import pygame

import engine.platform.screen_info as screen_info
from engine.game_logger import get_logger
from engine.managers.collision_manager import CollisionManager
from engine.managers.object_manager import ObjectManager
from engine.managers.render_manager import RenderManager
from engine.managers.scene_manager import SceneManager
from engine.platform.pygame_input import PyGameInput


class GameApplication:
    """pygame 루프와 엔진 매니저 갱신을 실행합니다."""

    def __init__(
        self,
        title: str = "Cover-Based Duel AI",
        screenSize: tuple[int, int] | None = None,
        backgroundColor: tuple[int, int, int] = (30, 30, 30),
        targetFps: int = 60,
        logger=None,
    ) -> None:
        self._title = title
        self._screenSize = screenSize or (screen_info.SCREEN_WIDTH, screen_info.SCREEN_HEIGHT)
        self._backgroundColor = backgroundColor
        self._targetFps = int(targetFps)
        self._logger = logger or get_logger("game.app")
        self._screen = None
        self._clock = None
        self._running = False

    def run(self) -> None:
        """앱 실행을 시작하고 루프가 끝날 때까지 진행합니다."""
        pygame.init()
        self._screen = pygame.display.set_mode(self._screenSize)
        self._clock = pygame.time.Clock()
        pygame.display.set_caption(self._title)
        try:
            self.onStart()
            self._running = True

            while self._running:
                deltaTime = self._clock.tick(self._targetFps) / 1000.0
                self._processEvents()
                self._screen.fill(self._backgroundColor)

                self.update(deltaTime)
                RenderManager.getInstance().render(self._screen)
                self.renderOverlay(self._screen)

                pygame.display.set_caption(f"{self._title} - FPS: {self._clock.get_fps():.2f}")
                pygame.display.flip()
        finally:
            self.shutdown()

    def stop(self) -> None:
        """현재 실행 중인 루프를 중단합니다."""
        self._running = False

    def onStart(self) -> None:
        """실행 시작 시 한 번 호출됩니다."""

    def handleEvent(self, event) -> None:
        """입력 이벤트를 처리합니다."""

    def update(self, deltaTime: float) -> None:
        """프레임별 게임 로직을 갱신합니다."""
        self.updateWorld(deltaTime)

    def renderOverlay(self, screen) -> None:
        """기본 렌더 이후 추가 오버레이를 그립니다."""

    def onShutdown(self) -> None:
        """종료 직전에 필요한 정리 작업을 수행합니다."""

    def updateWorld(self, deltaTime: float) -> None:
        """충돌과 오브젝트 매니저를 갱신해 월드를 진행합니다."""
        CollisionManager.getInstance().update()
        ObjectManager.getInstance().update(deltaTime)

    def shutdown(self) -> None:
        """앱 종료 정리를 수행하고 제어를 호출자에게 반환합니다."""
        self.onShutdown()
        SceneManager.getInstance().release()
        pygame.quit()

    def _processEvents(self) -> None:
        PyGameInput.getInstance().updateEvents()
        eventList = PyGameInput.getInstance().getEventInfo()
        for event in eventList[:]:
            if event.type == pygame.QUIT:
                self.stop()
            self.handleEvent(event)
