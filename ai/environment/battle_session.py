from pygame.math import Vector2

from shooter.components.ai_controller import AIAction
from ai.environment.battle_observation import BattleObservationBuilder
from ai.environment.battle_rules import BattleRules
from ai.environment.battle_runtime import (
    BattleFrameDecision,
    BattleFrameResult,
    BattleFrameTrace,
    PolicyRuntime,
)
from models.policies import HeuristicPolicy
from engine.managers.collision_manager import CollisionManager
from engine.managers.object_manager import ObjectManager
from shooter.scenes.game_scene import GameScene


class BattleSession:
    """전투 프레임 진행과 학습 연결을 관리합니다."""

    DEFAULT_THINK_INTERVAL = 5

    PREFERRED_DISTANCE_CENTER = 260.0
    PREFERRED_DISTANCE_REWARD_MIN = 0.02
    PREFERRED_DISTANCE_REWARD_MAX = 0.05
    PREFERRED_DISTANCE_IMPROVEMENT_SCALE = 100.0
    COVER_ADVANTAGE_REWARD = 0.05
    COVER_SCORE_IMPROVEMENT_THRESHOLD = 0.18
    COVER_SCORE_REWARD_THRESHOLD = 0.55
    BLOCKED_MOVE_PENALTY_MIN = -0.02
    BLOCKED_MOVE_PENALTY_MAX = -0.05
    BLOCKED_MOVE_DISTANCE_EPSILON = 2.0
    BLOCKED_MOVE_MIN_CONSECUTIVE_STEPS = 2
    IDLE_PENALTY = -0.01
    IDLE_PENALTY_START_STEPS = 10
    MEANINGLESS_ATTACK_PENALTY_MIN = -0.02
    MEANINGLESS_ATTACK_PENALTY_MAX = -0.05
    MEANINGLESS_ATTACK_ANGLE_THRESHOLD_DEGREES = 75.0
    MEANINGLESS_ATTACK_SEVERE_THRESHOLD_DEGREES = 120.0

    def __init__(
        self,
        scene: GameScene,
        externalControl: bool = False,
        policyA=None,
        policyB=None,
        autoLearn: bool = False,
        checkpointPathA=None,
        checkpointPathB=None,
        thinkInterval: int = DEFAULT_THINK_INTERVAL,
        explore: bool = True,
        saveOnEpisodeEnd: bool = True,
    ) -> None:
        self._scene = scene
        self._externalControl = externalControl
        self._autoLearn = bool(autoLearn)
        self._policyA = policyA if policyA is not None else HeuristicPolicy()
        self._policyB = policyB if policyB is not None else HeuristicPolicy()
        self._observationBuilder = BattleObservationBuilder(scene)
        self._rules = BattleRules(GameScene.TAG_A, GameScene.TAG_B)
        self._policyRuntimes = {
            GameScene.TAG_A: PolicyRuntime(
                GameScene.TAG_A,
                None if self._externalControl else self._policyA,
                checkpointPathA,
                trainingEnabled=self._autoLearn,
                explore=explore,
                thinkInterval=thinkInterval,
                saveOnEpisodeEnd=saveOnEpisodeEnd,
            ),
            GameScene.TAG_B: PolicyRuntime(
                GameScene.TAG_B,
                None if self._externalControl else self._policyB,
                checkpointPathB,
                trainingEnabled=self._autoLearn,
                explore=explore,
                thinkInterval=thinkInterval,
                saveOnEpisodeEnd=saveOnEpisodeEnd,
            ),
        }
        self._frameIndex = 0
        self._episodeStepCount = 0
        self._episodeRewardTotals = {
            GameScene.TAG_A: 0.0,
            GameScene.TAG_B: 0.0,
        }
        self._episodeClosed = False
        self._lastFrameResult = None
        self._lastWinner = None
        self._idleStepCounts = {
            GameScene.TAG_A: 0,
            GameScene.TAG_B: 0,
        }
        self._blockedMoveCounts = {
            GameScene.TAG_A: 0,
            GameScene.TAG_B: 0,
        }

    def initializeEpisode(self) -> None:
        """에피소드 시작에 필요한 상태를 초기화합니다."""
        self._frameIndex = 0
        self._episodeStepCount = 0
        self._episodeClosed = False
        self._lastWinner = None
        self._episodeRewardTotals[GameScene.TAG_A] = 0.0
        self._episodeRewardTotals[GameScene.TAG_B] = 0.0
        self._idleStepCounts[GameScene.TAG_A] = 0
        self._idleStepCounts[GameScene.TAG_B] = 0
        self._blockedMoveCounts[GameScene.TAG_A] = 0
        self._blockedMoveCounts[GameScene.TAG_B] = 0
        self._rules.resetEpisode()
        self._policyRuntimes[GameScene.TAG_A].resetEpisode()
        self._policyRuntimes[GameScene.TAG_B].resetEpisode()

    def stepFrame(self, deltaTime: float, actionPlan: dict | None = None) -> BattleFrameResult:
        """전투 한 프레임을 진행하고 결과를 반환합니다."""
        trace = BattleFrameTrace()
        trace.add("BattleSession.stepFrame(deltaTime)")

        trace.add("1. BattleSession.getObservations()")
        observations = self.getObservations()

        trace.add("2. BattleSession._resolveFrameDecisions(observations, actionPlan)")
        decisions = self._resolveFrameDecisions(observations, actionPlan, trace)

        trace.add("3. BattleSession.applyActions(actionA, actionB)")
        self.applyActions(
            decisions[GameScene.TAG_A].action,
            decisions[GameScene.TAG_B].action,
        )

        trace.add("4. CollisionManager.update()")
        CollisionManager.getInstance().update()
        trace.add("5. ObjectManager.update(deltaTime)")
        ObjectManager.getInstance().update(deltaTime)

        trace.add("6. BattleRules.resolveFrame()")
        outcome = self._rules.resolveFrame()
        self._lastWinner = outcome.winner
        self._frameIndex += 1
        self._episodeStepCount += 1

        trace.add("7. BattleSession.getObservations()")
        nextObservations = self.getObservations()

        trace.add("8. BattleSession._applyRewardShaping(...)")
        shapedRewards = self._applyRewardShaping(observations, nextObservations, decisions, trace)
        finalRewards = self._mergeRewards(outcome.rewards, shapedRewards)
        self._episodeRewardTotals[GameScene.TAG_A] += finalRewards.get(GameScene.TAG_A, 0.0)
        self._episodeRewardTotals[GameScene.TAG_B] += finalRewards.get(GameScene.TAG_B, 0.0)

        trace.add("9. BattleSession._advancePolicyIntervals(...)")
        self._advancePolicyIntervals(finalRewards, nextObservations, outcome.done, trace)

        episodeSummary = None
        if outcome.done:
            trace.add("10. BattleSession._closeEpisode()")
            episodeSummary = self._closeEpisode(trace)

        result = BattleFrameResult(
            frameIndex=self._frameIndex,
            observations=observations,
            nextObservations=nextObservations,
            rewards=finalRewards,
            done=outcome.done,
            winner=outcome.winner,
            callStack=trace.asTuple(),
            episodeSummary=episodeSummary,
        )
        self._lastFrameResult = result
        return result

    def getLastFrameResult(self):
        """가장 최근 프레임 결과를 반환합니다."""
        return self._lastFrameResult

    def getObservations(self) -> dict:
        """현재 전투 상태를 정책 공통 관측 형식으로 반환합니다."""
        return self._observationBuilder.buildForBattle()

    def applyActions(self, actionA: AIAction, actionB: AIAction) -> None:
        """각 컨트롤러에 이번 프레임 액션을 전달합니다."""
        controllerA = self._scene.getController(GameScene.TAG_A)
        controllerB = self._scene.getController(GameScene.TAG_B)

        if controllerA is not None and actionA is not None:
            controllerA.setAction(actionA)
        if controllerB is not None and actionB is not None:
            controllerB.setAction(actionB)

    def forceCloseEpisode(self) -> str:
        """현재 에피소드를 강제로 종료하고 요약 문자열을 반환합니다."""
        self._rules.forceFinish()
        return self._closeEpisode(BattleFrameTrace())

    def saveCheckpoints(self) -> None:
        for tag in (GameScene.TAG_A, GameScene.TAG_B):
            self._policyRuntimes[tag].saveCheckpoint()

    def discardEpisodeProgress(self) -> None:
        self._episodeClosed = True
        for tag in (GameScene.TAG_A, GameScene.TAG_B):
            self._policyRuntimes[tag].discardEpisodeProgress()

    def _resolveFrameDecisions(
        self,
        observations: dict,
        actionPlan: dict | None,
        trace: BattleFrameTrace,
    ) -> dict[str, BattleFrameDecision]:
        decisions = {}
        actionPlan = {} if actionPlan is None else dict(actionPlan)

        for tag in (GameScene.TAG_A, GameScene.TAG_B):
            observation = observations.get(tag, {})
            if tag in actionPlan and actionPlan[tag] is not None:
                trace.add(f"  {tag}: external action override")
                decisions[tag] = BattleFrameDecision(
                    tag=tag,
                    observation=observation,
                    action=actionPlan[tag],
                    source="external",
                )
                continue

            decisions[tag] = self._policyRuntimes[tag].decide(observation, trace)

        return decisions

    def _advancePolicyIntervals(
        self,
        rewards: dict,
        nextObservations: dict,
        done: bool,
        trace: BattleFrameTrace,
    ) -> None:
        for tag in (GameScene.TAG_A, GameScene.TAG_B):
            self._policyRuntimes[tag].advanceInterval(
                rewards.get(tag, 0.0),
                nextObservations.get(tag, {}),
                done,
                trace,
            )

    def _applyRewardShaping(
        self,
        observations: dict,
        nextObservations: dict,
        decisions: dict[str, BattleFrameDecision],
        trace: BattleFrameTrace,
    ) -> dict[str, float]:
        shapedRewards = {
            GameScene.TAG_A: 0.0,
            GameScene.TAG_B: 0.0,
        }

        for tag in (GameScene.TAG_A, GameScene.TAG_B):
            previous = observations.get(tag, {})
            current = nextObservations.get(tag, {})
            decision = decisions.get(tag)
            shapedRewards[tag] += self._computePreferredDistanceReward(previous, current)
            shapedRewards[tag] += self._computeCoverReward(previous, current)
            shapedRewards[tag] += self._computeBlockedMovementPenalty(tag, previous, current, decision)
            shapedRewards[tag] += self._computeIdlePenalty(tag, current)
            shapedRewards[tag] += self._computeMeaninglessAttackPenalty(previous, decision)

            if shapedRewards[tag] != 0.0:
                trace.add(f"  {tag}: shaping reward={shapedRewards[tag]:+.3f}")

        return shapedRewards

    def _computePreferredDistanceReward(self, previous: dict, current: dict) -> float:
        previousDistance = float(previous.get("distance_to_enemy", 0.0))
        currentDistance = float(current.get("distance_to_enemy", 0.0))
        previousGap = abs(previousDistance - self.PREFERRED_DISTANCE_CENTER)
        currentGap = abs(currentDistance - self.PREFERRED_DISTANCE_CENTER)
        improvement = previousGap - currentGap
        if improvement <= 2.0:
            return 0.0

        scaledReward = improvement / self.PREFERRED_DISTANCE_IMPROVEMENT_SCALE
        return min(
            self.PREFERRED_DISTANCE_REWARD_MAX,
            max(self.PREFERRED_DISTANCE_REWARD_MIN, scaledReward),
        )

    def _computeCoverReward(self, previous: dict, current: dict) -> float:
        previousScore = self._computeCoverScore(previous)
        currentScore = self._computeCoverScore(current)
        if (
            currentScore >= self.COVER_SCORE_REWARD_THRESHOLD
            and currentScore - previousScore >= self.COVER_SCORE_IMPROVEMENT_THRESHOLD
        ):
            return self.COVER_ADVANTAGE_REWARD
        return 0.0

    def _computeBlockedMovementPenalty(
        self,
        tag: str,
        previous: dict,
        current: dict,
        decision: BattleFrameDecision | None,
    ) -> float:
        if decision is None or decision.action is None:
            self._blockedMoveCounts[tag] = 0
            return 0.0

        attemptedMovement = (
            decision.action.moveDirection.length_squared() > 0.0
            or bool(decision.action.dash)
        )
        if not attemptedMovement:
            self._blockedMoveCounts[tag] = 0
            return 0.0

        if self._didCollectNearbyItem(previous, current):
            self._blockedMoveCounts[tag] = 0
            return 0.0

        previousPos = previous.get("self_position", (0.0, 0.0))
        currentPos = current.get("self_position", (0.0, 0.0))
        displacement = (Vector2(currentPos) - Vector2(previousPos)).length()
        if displacement > self.BLOCKED_MOVE_DISTANCE_EPSILON:
            self._blockedMoveCounts[tag] = 0
            return 0.0

        self._blockedMoveCounts[tag] += 1
        consecutive = self._blockedMoveCounts[tag]
        if consecutive < self.BLOCKED_MOVE_MIN_CONSECUTIVE_STEPS:
            return 0.0
        if consecutive == self.BLOCKED_MOVE_MIN_CONSECUTIVE_STEPS:
            return self.BLOCKED_MOVE_PENALTY_MIN
        if consecutive == self.BLOCKED_MOVE_MIN_CONSECUTIVE_STEPS + 1:
            return -0.03
        if consecutive == self.BLOCKED_MOVE_MIN_CONSECUTIVE_STEPS + 2:
            return -0.04
        return self.BLOCKED_MOVE_PENALTY_MAX

    def _computeIdlePenalty(self, tag: str, current: dict) -> float:
        stateName = str(current.get("state", "idle")).strip().lower()
        if stateName != "idle":
            self._idleStepCounts[tag] = 0
            return 0.0

        self._idleStepCounts[tag] += 1
        if self._idleStepCounts[tag] < self.IDLE_PENALTY_START_STEPS:
            return 0.0
        return self.IDLE_PENALTY

    def _computeMeaninglessAttackPenalty(
        self,
        observation: dict,
        decision: BattleFrameDecision | None,
    ) -> float:
        if decision is None or decision.action is None or decision.action.attackPosition is None:
            return 0.0

        selfPos = Vector2(observation.get("self_position", (0.0, 0.0)))
        enemyPos = Vector2(observation.get("enemy_position", (0.0, 0.0)))
        attackPos = Vector2(decision.action.attackPosition)

        toEnemy = enemyPos - selfPos
        toAttack = attackPos - selfPos
        if toEnemy.length_squared() == 0.0 or toAttack.length_squared() == 0.0:
            return 0.0

        angleDifference = toEnemy.angle_to(toAttack)
        absoluteAngleDifference = abs(float(angleDifference))
        if absoluteAngleDifference < self.MEANINGLESS_ATTACK_ANGLE_THRESHOLD_DEGREES:
            return 0.0
        if absoluteAngleDifference >= self.MEANINGLESS_ATTACK_SEVERE_THRESHOLD_DEGREES:
            return self.MEANINGLESS_ATTACK_PENALTY_MAX
        return self.MEANINGLESS_ATTACK_PENALTY_MIN

    def _mergeRewards(self, baseRewards: dict, extraRewards: dict) -> dict[str, float]:
        merged = {
            GameScene.TAG_A: float(baseRewards.get(GameScene.TAG_A, 0.0)),
            GameScene.TAG_B: float(baseRewards.get(GameScene.TAG_B, 0.0)),
        }
        for tag in (GameScene.TAG_A, GameScene.TAG_B):
            merged[tag] += float(extraRewards.get(tag, 0.0))
        return merged

    def _closeEpisode(self, trace: BattleFrameTrace) -> str:
        if self._episodeClosed:
            return self._buildEpisodeSummary()

        self._episodeClosed = True
        self._policyRuntimes[GameScene.TAG_A].finishEpisode(trace)
        self._policyRuntimes[GameScene.TAG_B].finishEpisode(trace)
        return self._buildEpisodeSummary()

    def _buildEpisodeSummary(self) -> str:
        epsilonA = self._policyRuntimes[GameScene.TAG_A].getEpsilon()
        epsilonB = self._policyRuntimes[GameScene.TAG_B].getEpsilon()
        epsilonText = ""
        if epsilonA is not None and epsilonB is not None:
            epsilonText = f" | epsA:{epsilonA:.3f}, epsB:{epsilonB:.3f}"

        return (
            f"Winner: {self._lastWinner} | "
            f"A:{self._episodeRewardTotals[GameScene.TAG_A]:.1f}, "
            f"B:{self._episodeRewardTotals[GameScene.TAG_B]:.1f}"
            f"{epsilonText}"
        )

    def _computeCoverScore(self, observation: dict) -> float:
        selfPos = Vector2(observation.get("self_position", (0.0, 0.0)))
        enemyPos = Vector2(observation.get("enemy_position", (0.0, 0.0)))
        coverPositions = observation.get("cover_positions", ())
        bestScore = 0.0

        for coverPosition in coverPositions:
            coverPos = Vector2(coverPosition)
            bestScore = max(bestScore, self._scoreCoverPosition(selfPos, enemyPos, coverPos))

        return bestScore

    def _scoreCoverPosition(self, selfPos: Vector2, enemyPos: Vector2, coverPos: Vector2) -> float:
        toEnemy = enemyPos - selfPos
        segmentLength = toEnemy.length()
        if segmentLength <= 1.0:
            return 0.0

        direction = toEnemy / segmentLength
        toCover = coverPos - selfPos
        projectedDistance = toCover.dot(direction)
        if projectedDistance <= 20.0 or projectedDistance >= segmentLength - 20.0:
            return 0.0

        perpendicularDistance = (toCover - (direction * projectedDistance)).length()
        if perpendicularDistance >= 110.0:
            return 0.0

        selfDistance = toCover.length()
        enemyDistance = (coverPos - enemyPos).length()
        lineScore = max(0.0, 1.0 - (perpendicularDistance / 110.0))
        selfDistanceScore = max(0.0, 1.0 - (selfDistance / 260.0))
        enemyDistanceScore = max(0.0, min((enemyDistance - selfDistance + 120.0) / 240.0, 1.0))
        return (lineScore * 0.5) + (selfDistanceScore * 0.3) + (enemyDistanceScore * 0.2)

    def _didCollectNearbyItem(self, previous: dict, current: dict) -> bool:
        if not bool(previous.get("item_active", False)) or bool(current.get("item_active", False)):
            return False

        return float(previous.get("self_item_distance", 9999.0)) <= 24.0
