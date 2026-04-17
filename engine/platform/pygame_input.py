import pygame

class PyGameInput:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if PyGameInput._initialized:
            return

        self._eventList = []

        PyGameInput._initialized = True

    @classmethod
    def getInstance(cls):
        return cls()
    
    def updateEvents(self) -> None:
        self._eventList = pygame.event.get()

    def getEventInfo(self) -> list:
        return self._eventList[:]