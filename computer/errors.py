"""Computer API errors."""


class ComputerError(RuntimeError):
    """Base error for desktop capability failures."""


class CapabilityUnavailableError(ComputerError):
    """Raised when a capability has no active platform adapter."""


class DesktopOperationError(ComputerError):
    """Raised when a native desktop operation fails."""


class ElementNotFoundError(ComputerError):
    """Raised when a UI, process, or window element is not found."""


class RuntimeDependencyError(ComputerError):
    """Raised when an optional native dependency is required but missing."""


class TimeoutExpiredError(ComputerError):
    """Raised when a desktop wait operation times out."""
