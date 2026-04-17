from pygame.math import Vector2

from engine.core.component import Component
from engine.managers.object_manager import ObjectManager

class GameObject:
    def __init__(self, tag : str) -> None:
        self._position = Vector2(0.0, 0.0)
        self._componentList = []
        self._isActive = True
        self._isDestroyed = False
        self._isStarted = False
        self._tag = tag

    def getTag(self) -> str:
        return self._tag
    
    def setTag(self, value : str) -> None:
        if value is not None:
            self._tag = value

    def registerObjectManager(self) -> None:
        ObjectManager.getInstance().addObject(self)

    def setPosition(self, position: Vector2) -> None:
        self._position = Vector2(position)

    def getPosition(self) -> Vector2:
        return Vector2(self._position)

    def setActive(self, active: bool) -> None:
        self._isActive = active

    def getActive(self) -> bool:
        return self._isActive
    
    def isStarted(self) -> bool:
        return self._isStarted
    
    def destroy(self) -> None:
        self._isDestroyed = True

    def isDestroyed(self) -> bool:
        return self._isDestroyed

    def addComponent(self, component: Component) -> Component:
        for exist_component in self._componentList:
            if type(exist_component) is type(component):
                raise ValueError(f"{type(component).__name__} component already exists.")

        self._componentList.append(component)
        component.initialize(self)
        return component

    def getComponent(self, componentType: type) -> Component | None:
        for component in self._componentList:
            if isinstance(component, componentType):
                return component
        return None

    def removeComponent(self, component: Component) -> None:
        if component in self._componentList:
            component.destroy()

    def removeComponentByType(self, componentType: type) -> None:
        component = self.getComponent(componentType)
        if component is not None:
            component.destroy()

    def start(self) -> None:
        if self._isStarted:
            return

        for component in self._componentList[:]:
            if not component.isDestroyed():
                component.start()

        self._isStarted = True
        self._cleanupDestroyedComponents()

    def update(self, deltaTime: float) -> None:
        if self._isDestroyed:
            return

        for component in self._componentList[:]:
            if component.isDestroyed():
                continue

            if not component.isStarted():
                component.start()

            component.update(deltaTime)

        self._cleanupDestroyedComponents()

    def release(self) -> None:
        for component in self._componentList[:]:
            component.release()

        self._componentList.clear()

    def _cleanupDestroyedComponents(self) -> None:
        for component in self._componentList[:]:
            if component.isDestroyed():
                component.release()
                self._componentList.remove(component)

    def onCollisionEnter(self, other) -> None:
        if self._isDestroyed:
            return

        for component in self._componentList[:]:
            if component.isDestroyed():
                continue
            component.onCollisionEnter(other)

    def onCollisionStay(self, other) -> None:
        if self._isDestroyed:
            return

        for component in self._componentList[:]:
            if component.isDestroyed():
                continue
            component.onCollisionStay(other)

    def onCollisionExit(self, other) -> None:
        if self._isDestroyed:
            return

        for component in self._componentList[:]:
            if component.isDestroyed():
                continue
            component.onCollisionExit(other)
