"""Runtime core errors."""


class RuntimeErrorBase(RuntimeError):
    """Base error for SDK/runtime failures."""


class BackendUnavailableError(RuntimeErrorBase):
    """Raised when no backend can execute or observe a request."""
