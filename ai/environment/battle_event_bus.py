class BattleEventBus:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if BattleEventBus._initialized:
            return

        self._events = []
        BattleEventBus._initialized = True

    @classmethod
    def getInstance(cls):
        return cls()

    def clear(self) -> None:
        self._events.clear()

    def emit(self, eventType: str, **payload) -> None:
        self._events.append({
            "type": eventType,
            **payload,
        })

    def consumeAll(self) -> list:
        events = self._events[:]
        self._events.clear()
        return events
