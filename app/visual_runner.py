from ai.policy_setup import TrainingSetup, loadTrainingSetup
from app.game_application import GameApplication
from ai.environment.battle_factory import BattleBundle, createBattleBundle
from app.debug_overlay import DebugOverlay
from engine.game_logger import get_logger
from engine.managers.scene_manager import SceneManager
from shooter.scenes.start_scene import StartScene


class VisualBattleController:
    """시각 모드의 장면 전환과 전투 세션 실행을 관리합니다."""

    def __init__(self, setup: TrainingSetup, logger) -> None:
        self._setup = setup
        self._logger = logger
        self._currentBattle: BattleBundle | None = None

    def createStartScene(self) -> StartScene:
        """시각 모드 시작 화면을 생성합니다."""
        if self._setup.loadedA and self._setup.loadedB:
            self._logger.info(
                "Visual mode using trained policies A/B from %s / %s",
                self._setup.specA.checkpointPath,
                self._setup.specB.checkpointPath,
            )
            message = "AI A: trained policy / AI B: trained policy"
        else:
            self._logger.info(
                "Visual mode bootstrapping training checkpoints A=%s B=%s",
                self._setup.loadedA,
                self._setup.loadedB,
            )
            message = "Self-play training mode"

        return StartScene(message=message, onStart=self.startBattle)

    def startBattle(self) -> None:
        """현재 설정으로 새 전투 장면과 세션을 시작합니다."""
        self._currentBattle = createBattleBundle(
            policyA=self._setup.policyA,
            policyB=self._setup.policyB,
            autoLearn=False,
            checkpointPathA=self._setup.specA.checkpointPath,
            checkpointPathB=self._setup.specB.checkpointPath,
            explore=False,
            saveOnEpisodeEnd=False,
        )
        SceneManager.getInstance().setScene(self._currentBattle.scene)
        self._currentBattle.session.initializeEpisode()

    def updateFrame(self, deltaTime: float):
        """시각 모드 전투 프레임을 갱신하고 결과를 반환합니다."""
        if self._currentBattle is None:
            return None

        activeScene = SceneManager.getInstance().getScene()
        if activeScene is not self._currentBattle.scene:
            self._currentBattle = None
            return None

        frameResult = self._currentBattle.session.stepFrame(deltaTime)
        if frameResult.done:
            self._logger.info(
                "visual episode end winner=%s summary=%s",
                frameResult.winner,
                frameResult.episodeSummary,
            )
            SceneManager.getInstance().setScene(
                StartScene(
                    message=frameResult.episodeSummary,
                    onStart=self.startBattle,
                )
            )
            self._currentBattle = None
        return frameResult

class VisualBattleApplication(GameApplication):
    """시각 모드 전투 실행을 게임 엔진 루프 위에서 구동합니다."""

    def __init__(self, setup: TrainingSetup, logger) -> None:
        super().__init__(title="Cover-Based Duel AI", logger=logger)
        self._visualController = VisualBattleController(setup, logger)
        self._debugOverlay = DebugOverlay()
        self._frameResult = None

    def onStart(self) -> None:
        SceneManager.getInstance().setScene(self._visualController.createStartScene())

    def handleEvent(self, event) -> None:
        self._debugOverlay.handleEvent(event)

    def update(self, deltaTime: float) -> None:
        self._frameResult = self._visualController.updateFrame(deltaTime)
        if self._frameResult is None:
            self.updateWorld(deltaTime)

    def renderOverlay(self, screen) -> None:
        self._debugOverlay.render(screen, self._frameResult)


def runVisualMode() -> None:
    """시각 모드 실행에 필요한 객체를 만들고 앱을 시작합니다."""
    logger = get_logger("game.main")
    logger.info("Game start (visual mode)")
    setup = loadTrainingSetup(epsilon=0.12, epsilonMin=0.03, epsilonDecay=0.998)
    app = VisualBattleApplication(setup, logger)
    try:
        app.run()
    finally:
        logger.info("Game shutdown")
