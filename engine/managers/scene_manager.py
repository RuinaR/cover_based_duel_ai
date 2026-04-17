from engine.core.scene import Scene
from engine.managers.object_manager import ObjectManager
from engine.managers.render_manager import RenderManager
from engine.managers.collision_manager import CollisionManager


class SceneManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if SceneManager._initialized:
            return

        self._scene = None
        SceneManager._initialized = True

    @classmethod
    def getInstance(cls):
        return cls()

    def getScene(self):
        return self._scene

    def setScene(self, scene: Scene) -> None:
        if scene is None:
            raise Exception("scene is None")
        
        self.release()

        CollisionManager.getInstance().initialize()
        ObjectManager.getInstance().initialize()   
        self._scene = scene
        self._scene.initialize()

    def release(self) -> None:
        if self._scene is not None:
            self._scene.release()
            self._scene = None

        ObjectManager.getInstance().release()
        CollisionManager.getInstance().release()
        RenderManager.getInstance().reset()
