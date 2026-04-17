from engine.core.component import Component

class Collider(Component):
    def __init__(self) -> None:
        super().__init__()

    def onInitialize(self) -> None:
        from engine.managers.collision_manager import CollisionManager
        CollisionManager.getInstance().addCollider(self)
        pass

    def onStart(self) -> None:
        pass

    def onUpdate(self, deltaTime: float) -> None:
        pass

    def onRelease(self) -> None:
        from engine.managers.collision_manager import CollisionManager
        CollisionManager.getInstance().removeCollider(self)
        pass
