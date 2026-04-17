


class ObjectManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if ObjectManager._initialized:
            return

        self._gameObjectList = []
        self._pendingAddList = []
        self._pendingRemoveList = []

        ObjectManager._initialized = True

    @classmethod
    def getInstance(cls):
        return cls()

    def initialize(self) -> None:
        self._gameObjectList.clear()
        self._pendingAddList.clear()
        self._pendingRemoveList.clear()

    def release(self) -> None:
        for gameObject in self._gameObjectList[:]:
            gameObject.release()

        for gameObject in self._pendingAddList[:]:
            gameObject.release()

        self._gameObjectList.clear()
        self._pendingAddList.clear()
        self._pendingRemoveList.clear()

    def addObject(self, gameObject):
        if gameObject is None:
            raise ValueError("gameObject is None.")

        if gameObject in self._gameObjectList:
            return gameObject

        if gameObject in self._pendingAddList:
            return gameObject

        self._pendingAddList.append(gameObject)
        return gameObject

    def removeObject(self, gameObject) -> None:
        if gameObject is None:
            return

        gameObject.destroy()

        if gameObject in self._pendingAddList:
            self._pendingAddList.remove(gameObject)
            gameObject.release()
            return

        if gameObject in self._pendingRemoveList:
            return

        self._pendingRemoveList.append(gameObject)

    def getObjectList(self) -> list:
        return self._gameObjectList

    def update(self, deltaTime: float) -> None:
        self._processPendingAdd()

        for gameObject in self._gameObjectList[:]:
            if gameObject.isDestroyed():
                continue

            if not gameObject.isStarted():
                gameObject.start()

            if gameObject.getActive():
                gameObject.update(deltaTime)

        self._collectDestroyedObjects()
        self._processPendingRemove()

    def _processPendingAdd(self) -> None:
        if len(self._pendingAddList) == 0:
            return

        for gameObject in self._pendingAddList[:]:
            if gameObject.isDestroyed():
                gameObject.release()
                continue

            self._gameObjectList.append(gameObject)

        self._pendingAddList.clear()

    def _collectDestroyedObjects(self) -> None:
        for gameObject in self._gameObjectList:
            if gameObject.isDestroyed() and gameObject not in self._pendingRemoveList:
                self._pendingRemoveList.append(gameObject)

    def _processPendingRemove(self) -> None:
        if len(self._pendingRemoveList) == 0:
            return

        for gameObject in self._pendingRemoveList[:]:
            if gameObject in self._gameObjectList:
                gameObject.release()
                self._gameObjectList.remove(gameObject)

        self._pendingRemoveList.clear()
