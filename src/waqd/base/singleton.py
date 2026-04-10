from typing import Any, ClassVar, Generic, TypeVar, cast


T = TypeVar("T")


class BorgSingleton(Generic[T]):
    """Lazy singleton factory keyed by subclass."""

    _instances: ClassVar[dict[object, Any]] = {}
    _instance_types: ClassVar[dict[object, type[Any] | None]] = {}
    _init_args: ClassVar[dict[object, tuple[Any, ...]]] = {}
    _init_kwargs: ClassVar[dict[object, dict[str, Any]]] = {}
    _key: object

    @classmethod
    def _singleton_key(cls, instance_type: type[T] | None) -> object:
        if cls is BorgSingleton:
            if instance_type is None:
                raise RuntimeError("BorgSingleton requires an instance type")
            return instance_type
        return cls

    def __new__(
        cls,
        instance_type: type[T] | None = None,
        *init_args: Any,
        **init_kwargs: Any,
    ) -> "BorgSingleton[T]":
        key = cls._singleton_key(instance_type)
        if key not in cls._instance_types:
            cls._instance_types[key] = instance_type
            cls._init_args[key] = init_args
            cls._init_kwargs[key] = dict(init_kwargs)

        self = cast("BorgSingleton[T]", super().__new__(cls))
        self._key = key
        return self

    def __call__(self) -> T:
        if self._key not in self._instances:
            self._instances[self._key] = self._create_instance(self._key)
        return cast(T, self._instances[self._key])

    def __init__(
        self,
        instance_type: type[T] | None = None,
        *init_args: Any,
        **init_kwargs: Any,
    ):
        pass

    @classmethod
    def _create_instance(cls, key: object) -> T:
        instance_type = cast(type[T] | None, cls._instance_types.get(key))
        if instance_type is None:
            raise RuntimeError(f"{cls.__name__} has no instance type configured")
        return instance_type(*cls._init_args.get(key, ()), **cls._init_kwargs.get(key, {}))

    def replace(self, instance: T) -> T:
        self._instances[self._key] = instance
        return instance

    def clear(self) -> None:
        self._instances.pop(self._key, None)

    def is_initialized(self) -> bool:
        return self._key in self._instances
