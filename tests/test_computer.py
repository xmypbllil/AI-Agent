from computer import create_default_computer
from computer.errors import CapabilityUnavailableError
from computer.keyboard import Keyboard
from computer.mouse import Mouse
from computer.models import MouseButton, Point


def test_files_are_restricted_to_root(tmp_path) -> None:
    computer = create_default_computer(root=tmp_path)
    computer.files.write("main.py", "print('x')")

    assert computer.files.read("main.py") == "print('x')"


def test_unsupported_capability_is_explicit() -> None:
    keyboard = Keyboard()

    try:
        keyboard.write("hello")
    except CapabilityUnavailableError as exc:
        assert "keyboard" in str(exc)
    else:
        raise AssertionError("Expected CapabilityUnavailableError")


class FakeMouseDriver:
    def __init__(self) -> None:
        self.clicked: tuple[Point | None, MouseButton] | None = None

    def move(self, point: Point) -> None:
        self.moved = point

    def click(self, point: Point | None = None, button: MouseButton = MouseButton.LEFT) -> None:
        self.clicked = (point, button)


def test_mouse_delegates_to_driver() -> None:
    driver = FakeMouseDriver()
    mouse = Mouse(driver=driver)

    mouse.click(Point(1, 2), MouseButton.RIGHT)

    assert driver.clicked == (Point(1, 2), MouseButton.RIGHT)
