from runtime.observations import WindowLocator
from runtime.ui import (
    Locator,
    UIControlType,
    UIElementBounds,
    UIElementIdentity,
    UIElementObservation,
    UIElementState,
    UITreeSnapshot,
)


def test_locator_is_platform_independent_and_composable() -> None:
    parent = Locator(automation_id="main", control_type=UIControlType.WINDOW)
    child = Locator(name="Run", parent=parent, visible=True, enabled=True)
    locator = Locator(
        regex="Run|Start",
        process="Code.exe",
        window=WindowLocator(title="Visual Studio Code"),
        children=(child,),
        index=0,
    )

    assert locator.window == WindowLocator(title="Visual Studio Code")
    assert locator.children[0].parent == parent
    assert locator.visible is None


def test_ui_element_observation_has_runtime_identity_not_platform_object() -> None:
    identity = UIElementIdentity(
        stable_id="process:1/window:Main/automation:Run",
        automation_id="Run",
        name="Run",
        control_type=UIControlType.BUTTON,
        process_id=1,
        window_title="Main",
    )
    observation = UIElementObservation(
        identity=identity,
        bounds=UIElementBounds(left=1, top=2, width=3, height=4),
        state=UIElementState(visible=True, enabled=True),
        child_ids=("child",),
    )
    snapshot = UITreeSnapshot(root_id=identity.stable_id, elements={identity.stable_id: observation})

    assert observation.identity.stable_id in snapshot.elements
    assert observation.bounds is not None
    assert observation.state.enabled is True
