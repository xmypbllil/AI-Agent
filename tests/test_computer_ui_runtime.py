from computer.ui import UI
from runtime.backends import BackendCapabilities, BackendCandidate, BackendManager, BackendRole
from runtime.ui import (
    Locator,
    UIControlType,
    UIElementIdentity,
    UIElementObservation,
    UITreeSnapshot,
)
from runtime.ui.engine import UIObservationExecutor


class FakeUIObservationBackend:
    @property
    def name(self) -> str:
        return "fake-uia"

    @property
    def role(self) -> BackendRole:
        return BackendRole.UI_AUTOMATION

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_tree=True, supports_text=True)

    def score_locator(self, locator: Locator, context=None):
        return BackendCandidate(
            backend_name=self.name,
            score=0.95,
            reason="test UI observation backend",
        )

    def find(self, locator: Locator):
        if locator.name != "Editor":
            return None
        return UIElementObservation(
            identity=UIElementIdentity(
                stable_id="editor",
                name="Editor",
                control_type=UIControlType.EDIT,
            ),
            text="hello",
        )

    def find_all(self, locator: Locator):
        found = self.find(locator)
        return () if found is None else (found,)

    def snapshot_tree(self, locator: Locator | None = None):
        element = self.find(locator or Locator(name="Editor"))
        elements = {} if element is None else {element.identity.stable_id: element}
        return UITreeSnapshot(root_id=element.identity.stable_id if element else None, elements=elements)


def test_computer_ui_find_uses_backend_manager() -> None:
    manager = BackendManager(ui_observation_backends=[FakeUIObservationBackend()])
    ui = UI(observation_executor=UIObservationExecutor(backend_manager=manager))

    element = ui.find(Locator(name="Editor", control_type=UIControlType.EDIT))

    assert element is not None
    assert element.text == "hello"
    assert ui.exists(Locator(name="Editor"))
    assert ui.text(Locator(name="Editor")) == "hello"
