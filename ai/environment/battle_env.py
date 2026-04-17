from shooter.components.ai_controller import AIAction
from ai.environment.battle_factory import createBattleBundle
from engine.managers.scene_manager import SceneManager
from shooter.scenes.game_scene import GameScene


class BattleEnv:
    def __init__(
        self,
        policyA=None,
        policyB=None,
        deltaTime: float = 1.0 / 60.0,
        autoLearn: bool = False,
        checkpointPathA=None,
        checkpointPathB=None,
        saveOnEpisodeEnd: bool = True,
    ) -> None:
        self._deltaTime = float(deltaTime)
        self._policyA = policyA
        self._policyB = policyB
        self._autoLearn = bool(autoLearn)
        self._checkpointPathA = checkpointPathA
        self._checkpointPathB = checkpointPathB
        self._saveOnEpisodeEnd = bool(saveOnEpisodeEnd)
        self._scene = None
        self._session = None

    def reset(self) -> dict:
        bundle = createBattleBundle(
            externalControl=self._policyA is None and self._policyB is None,
            policyA=self._policyA,
            policyB=self._policyB,
            autoLearn=self._autoLearn,
            checkpointPathA=self._checkpointPathA,
            checkpointPathB=self._checkpointPathB,
            saveOnEpisodeEnd=self._saveOnEpisodeEnd,
        )
        self._scene = bundle.scene
        self._session = bundle.session
        SceneManager.getInstance().setScene(self._scene)
        self._session.initializeEpisode()
        return self._session.getObservations()

    def step(self, actionA: AIAction = None, actionB: AIAction = None):
        if self._scene is None:
            raise RuntimeError("BattleEnv.reset() must be called before step().")

        actionPlan = {}
        if actionA is not None:
            actionPlan[GameScene.TAG_A] = actionA
        if actionB is not None:
            actionPlan[GameScene.TAG_B] = actionB

        frameResult = self._session.stepFrame(self._deltaTime, actionPlan=actionPlan)
        info = {
            "winner": frameResult.winner,
            "episode_summary": frameResult.episodeSummary,
            "call_stack": frameResult.callStack,
        }
        return frameResult.nextObservations, frameResult.rewards, frameResult.done, info

    def closeEpisode(self) -> str:
        if self._session is None:
            return ""
        return self._session.forceCloseEpisode()

    def saveCheckpoints(self) -> None:
        if self._session is not None:
            self._session.saveCheckpoints()
