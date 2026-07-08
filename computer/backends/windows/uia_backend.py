"""Microsoft UI Automation observation backend."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from runtime.backends.models import BackendCapabilities, BackendCandidate, BackendRole
from runtime.ui import (
    Locator,
    UIControlType,
    UIElementBounds,
    UIElementIdentity,
    UIElementObservation,
    UIElementState,
    UITreeSnapshot,
)

try:
    import comtypes.client
    comtypes.client.GetModule("UIAutomationCore.dll")
    from comtypes.gen import UIAutomationClient
except ImportError as exc:  # pragma: no cover - exercised in environments without comtypes.
    raise ImportError("UIAObservationBackend requires the optional 'comtypes' dependency") from exc


TreeScope_Element = 0x1
TreeScope_Children = 0x2
TreeScope_Descendants = 0x4
TreeScope_Subtree = 0x7
UIA_NamePropertyId = 30005
UIA_AutomationIdPropertyId = 30011
UIA_ClassNamePropertyId = 30012
UIA_ControlTypePropertyId = 30003
UIA_ProcessIdPropertyId = 30002
UIA_IsEnabledPropertyId = 30010
UIA_BoundingRectanglePropertyId = 30001
UIA_ButtonControlTypeId = 50000
UIA_EditControlTypeId = 50004
UIA_WindowControlTypeId = 50032
UIA_TextControlTypeId = 50020
UIA_MenuControlTypeId = 50009
UIA_MenuItemControlTypeId = 50011
UIA_ListControlTypeId = 50008
UIA_ListItemControlTypeId = 50007
UIA_TreeControlTypeId = 50023
UIA_TreeItemControlTypeId = 50024
UIA_ComboBoxControlTypeId = 50003
UIA_CheckBoxControlTypeId = 50002
UIA_RadioButtonControlTypeId = 50013
UIA_TabControlTypeId = 50018
UIA_TabItemControlTypeId = 50019
UIA_PaneControlTypeId = 50033
UIA_DocumentControlTypeId = 50030
UIA_ValuePatternId = 10002
CONTROL_TO_UIA = {
    UIControlType.BUTTON: UIA_ButtonControlTypeId,
    UIControlType.EDIT: UIA_EditControlTypeId,
    UIControlType.WINDOW: UIA_WindowControlTypeId,
    UIControlType.TEXT: UIA_TextControlTypeId,
    UIControlType.MENU: UIA_MenuControlTypeId,
    UIControlType.MENU_ITEM: UIA_MenuItemControlTypeId,
    UIControlType.LIST: UIA_ListControlTypeId,
    UIControlType.LIST_ITEM: UIA_ListItemControlTypeId,
    UIControlType.TREE: UIA_TreeControlTypeId,
    UIControlType.TREE_ITEM: UIA_TreeItemControlTypeId,
    UIControlType.COMBO_BOX: UIA_ComboBoxControlTypeId,
    UIControlType.CHECK_BOX: UIA_CheckBoxControlTypeId,
    UIControlType.RADIO_BUTTON: UIA_RadioButtonControlTypeId,
    UIControlType.TAB: UIA_TabControlTypeId,
    UIControlType.TAB_ITEM: UIA_TabItemControlTypeId,
    UIControlType.PANE: UIA_PaneControlTypeId,
    UIControlType.DOCUMENT: UIA_DocumentControlTypeId,
}
UIA_TO_CONTROL = {value: key for key, value in CONTROL_TO_UIA.items()}


@dataclass(slots=True)
class UIAObservationBackend:
    _automation: Any | None = field(default=None, init=False, repr=False)

    @property
    def name(self) -> str:
        return "uia"

    @property
    def role(self) -> BackendRole:
        return BackendRole.UI_AUTOMATION

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            supports_text=True,
            supports_tree=True,
            supports_pattern=True,
            supports_window_search=True,
        )

    def score_locator(
        self,
        locator: Locator,
        context: Mapping[str, Any] | None = None,
    ) -> BackendCandidate | None:
        return BackendCandidate(
            backend_name=self.name,
            score=0.95,
            reason="supports UI tree observation through Microsoft UI Automation",
        )

    def find(self, locator: Locator) -> UIElementObservation | None:
        matches = self.find_all(locator)
        if locator.index is not None:
            return matches[locator.index] if 0 <= locator.index < len(matches) else None
        return matches[0] if matches else None

    def find_all(self, locator: Locator) -> tuple[UIElementObservation, ...]:
        root = self._root_for(locator)
        condition = self._condition(locator)
        elements = root.FindAll(TreeScope_Subtree, condition)
        observations = [self._observation(elements.GetElement(index)) for index in range(elements.Length)]
        return tuple(item for item in observations if self._matches_post_filter(item, locator))

    def _element_for(self, locator: Locator):
        root = self._root_for(locator)
        condition = self._condition(locator)
        elements = root.FindAll(TreeScope_Subtree, condition)
        matches = [
            elements.GetElement(index)
            for index in range(elements.Length)
            if self._matches_post_filter(self._observation(elements.GetElement(index)), locator)
        ]
        if locator.index is not None:
            if 0 <= locator.index < len(matches):
                return matches[locator.index]
            raise LookupError(f"UI element not found at index {locator.index}: {locator}")
        if not matches:
            raise LookupError(f"UI element not found: {locator}")
        return matches[0]

    def snapshot_tree(self, locator: Locator | None = None) -> UITreeSnapshot:
        root_element = self._root_for(locator or Locator())
        root = self._observation(root_element)
        elements: dict[str, UIElementObservation] = {root.identity.stable_id: root}
        children = root_element.FindAll(TreeScope_Descendants, self._automation_client().CreateTrueCondition())
        child_ids: list[str] = []
        for index in range(children.Length):
            child = self._observation(children.GetElement(index), parent_id=root.identity.stable_id)
            elements[child.identity.stable_id] = child
            child_ids.append(child.identity.stable_id)
        root = UIElementObservation(
            identity=root.identity,
            bounds=root.bounds,
            state=root.state,
            text=root.text,
            parent_id=root.parent_id,
            child_ids=tuple(child_ids),
            observed_at=root.observed_at,
            metadata=root.metadata,
        )
        elements[root.identity.stable_id] = root
        return UITreeSnapshot(root_id=root.identity.stable_id, elements=elements)

    def _automation_client(self):
        if self._automation is None:
            self._automation = comtypes.client.CreateObject(
                UIAutomationClient.CUIAutomation,
                interface=UIAutomationClient.IUIAutomation,
            )
        return self._automation

    def _root_for(self, locator: Locator):
        automation = self._automation_client()
        if locator.window is None:
            return automation.GetRootElement()
        window_locator = Locator(name=locator.window) if isinstance(locator.window, str) else Locator(
            name=locator.window.title,
            class_name=locator.window.class_name,
            process=locator.window.process_id,
            control_type=UIControlType.WINDOW,
        )
        window = self.find(window_locator)
        if window is None:
            return automation.GetRootElement()
        handle = window.metadata.get("native_window_handle")
        if isinstance(handle, int) and handle:
            return automation.ElementFromHandle(handle)
        return automation.GetRootElement()

    def _condition(self, locator: Locator):
        automation = self._automation_client()
        conditions = []
        if locator.automation_id:
            conditions.append(automation.CreatePropertyCondition(UIA_AutomationIdPropertyId, locator.automation_id))
        if locator.name:
            conditions.append(automation.CreatePropertyCondition(UIA_NamePropertyId, locator.name))
        if locator.class_name:
            conditions.append(automation.CreatePropertyCondition(UIA_ClassNamePropertyId, locator.class_name))
        if locator.control_type and locator.control_type in CONTROL_TO_UIA:
            conditions.append(
                automation.CreatePropertyCondition(
                    UIA_ControlTypePropertyId,
                    CONTROL_TO_UIA[locator.control_type],
                )
            )
        if isinstance(locator.process, int):
            conditions.append(automation.CreatePropertyCondition(UIA_ProcessIdPropertyId, locator.process))
        if not conditions:
            return automation.CreateTrueCondition()
        condition = conditions[0]
        for next_condition in conditions[1:]:
            condition = automation.CreateAndCondition(condition, next_condition)
        return condition

    def _matches_post_filter(self, observation: UIElementObservation, locator: Locator) -> bool:
        if isinstance(locator.process, str) and observation.identity.process_id is None:
            return False
        if locator.regex is not None:
            pattern = locator.regex if isinstance(locator.regex, str) else locator.regex.pattern
            text = observation.identity.name or observation.text or ""
            if re.search(pattern, text) is None:
                return False
        if locator.visible is not None and observation.state.visible != locator.visible:
            return False
        if locator.enabled is not None and observation.state.enabled != locator.enabled:
            return False
        return True

    def _observation(self, element, parent_id: str | None = None) -> UIElementObservation:
        name = self._property(element, "CurrentName")
        automation_id = self._property(element, "CurrentAutomationId")
        class_name = self._property(element, "CurrentClassName")
        control_type_id = self._property(element, "CurrentControlType")
        process_id = self._property(element, "CurrentProcessId")
        native_handle = self._property(element, "CurrentNativeWindowHandle")
        bounds = self._bounds(element)
        control_type = UIA_TO_CONTROL.get(control_type_id, UIControlType.UNKNOWN)
        stable_id = "|".join(
            str(part)
            for part in (
                process_id,
                native_handle,
                control_type.value,
                automation_id,
                name,
                class_name,
            )
        )
        return UIElementObservation(
            identity=UIElementIdentity(
                stable_id=stable_id,
                automation_id=automation_id or None,
                name=name or None,
                class_name=class_name or None,
                control_type=control_type,
                process_id=process_id or None,
            ),
            bounds=bounds,
            state=UIElementState(
                visible=bounds is not None and bounds.width > 0 and bounds.height > 0,
                enabled=bool(self._property(element, "CurrentIsEnabled")),
            ),
            text=self._text(element, name),
            parent_id=parent_id,
            metadata={"native_window_handle": native_handle},
        )

    def _bounds(self, element) -> UIElementBounds | None:
        rect = self._property(element, "CurrentBoundingRectangle")
        if rect is None:
            return None
        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        return UIElementBounds(left=int(rect.left), top=int(rect.top), width=width, height=height)

    def _property(self, element, name: str):
        try:
            return getattr(element, name)
        except Exception:  # noqa: BLE001 - COM property access can fail per element.
            return None

    def _text(self, element, fallback: str | None) -> str | None:
        try:
            pattern = element.GetCurrentPattern(UIA_ValuePatternId)
            if pattern:
                value = pattern.QueryInterface(UIAutomationClient.IUIAutomationValuePattern).CurrentValue
                return value if value != "" else fallback or ""
        except Exception:  # noqa: BLE001 - not every element supports ValuePattern.
            pass
        return fallback or None
