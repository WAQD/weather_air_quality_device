from typing import Any


class BorgSingleton:
    """Shared-state wrapper for app-wide singletons."""

    _shared_state = {}

    def __init__(self, name: str):
        object.__setattr__(
            self,
            "__dict__",
            self._shared_state.setdefault(name, {"_name": name, "_instance": None}),
        )

    def initialize(self, factory, *args, **kwargs):
        self._instance = factory(*args, **kwargs)
        return self

    def replace(self, instance: Any):
        self._instance = instance
        return self

    def clear(self):
        self._instance = None

    def is_initialized(self) -> bool:
        return self._instance is not None

    def require_instance(self) -> Any:
        if self._instance is None:
            raise RuntimeError(f"{self._name} is not initialized yet")
        return self._instance

    def __getattr__(self, item: str) -> Any:
        return getattr(self.require_instance(), item)

    def __setattr__(self, key, value):
        if key in {"_name", "_instance"}:
            object.__setattr__(self, key, value)
            return
        setattr(self.require_instance(), key, value)

    def __bool__(self):
        return self.is_initialized()

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} name={self._name!r} "
            f"initialized={self.is_initialized()}>"
        )
