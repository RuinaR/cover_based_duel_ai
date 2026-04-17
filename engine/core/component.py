
class Component:
    def __init__(self) -> None:
        self._gameObject = None
        self._isDestroyed = False
        self._isStarted = False
        self._isReleased = False

    def isDestroyed(self) -> bool:
        return self._isDestroyed

    def destroy(self) -> None:
        self._isDestroyed = True
    
    def initialize(self, gameObject) -> None:
        if self._gameObject is not None and self._gameObject is not gameObject:
            raise Exception("이미 다른 GameObject에 등록된 Component입니다.")
        self._gameObject = gameObject
        self.onInitialize()

    def isStarted(self) -> bool:
        return self._isStarted

    def start(self) -> None:
        if self._isStarted:
            return

        self._isStarted = True
        self.onStart()
        
    def update(self, deltaTime: float) -> None:
        if self._isDestroyed:
            return

        self.onUpdate(deltaTime)
    
    def release(self) -> None:
        if self._isReleased:
            return
        
        self._isReleased = True
        self.onRelease()

    def getGameObject(self):
        return self._gameObject



    #Override------------------------------------------

    def onInitialize(self) -> None:
        pass

    def onStart(self) -> None:
        pass

    def onUpdate(self, deltaTime: float) -> None:
        pass

    def onRelease(self) -> None:
        pass

    def onCollisionEnter(self, other) -> None:
        pass

    def onCollisionStay(self, other) -> None:
        pass

    def onCollisionExit(self, other) -> None:
        pass