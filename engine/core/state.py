

class State:
    def __init__(self, owner, name: str) -> None:
        self._owner = owner
        self._name = name
        self._elapsed = 0.0

    def getName(self) -> str:
        return self._name

    def getElapsed(self) -> float:
        return self._elapsed

    def resetElapsed(self) -> None:
        self._elapsed = 0.0

    def addElapsed(self, deltaTime: float) -> None:
        self._elapsed += deltaTime

    def enter(self) -> None:
        pass

    def update(self, deltaTime: float) -> None:
        pass

    def exit(self) -> None:
        pass


class StateMachine:
    def __init__(self, owner) -> None:
        self._owner = owner
        self._currentState = None

    def getOwner(self):
        return self._owner

    def getCurrentState(self):
        return self._currentState

    def getCurrentStateName(self):
        if self._currentState is None:
            return None
        return self._currentState.getName()

    def changeState(self, nextState: State) -> None:
        if nextState is None:
            return

        if self._currentState is nextState:
            return

        if self._currentState is not None:
            self._currentState.exit()

        self._currentState = nextState
        self._currentState.resetElapsed()
        self._currentState.enter()

    def update(self, deltaTime: float) -> None:
        if self._currentState is None:
            return

        self._currentState.addElapsed(deltaTime)
        self._currentState.update(deltaTime)
