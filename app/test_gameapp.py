from app.game_application import GameApplication
from engine.managers.scene_manager import SceneManager
from shooter.scenes.start_scene import StartScene


class SimpleGameApp(GameApplication):
    def onStart(self) -> None:
        SceneManager.getInstance().setScene(StartScene(message="Engine only"))


