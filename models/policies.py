from dataclasses import dataclass, field
import gzip
import json
import math
import random
from pathlib import Path

from pygame.math import Vector2

from shooter.components.ai_controller import AIAction


@dataclass(slots=True)
class PolicyDecision:
    """정책이 선택한 액션과 학습용 보조 정보를 담습니다."""

    action: AIAction
    actionIndex: int | None = None
    stateKey: str | None = None


@dataclass(slots=True)
class PolicySpec:
    """정책 종류, 체크포인트 경로, 생성 옵션을 정의합니다."""

    kind: str
    checkpointPath: Path
    options: dict[str, object] = field(default_factory=dict)


class AIPolicy:
    """모든 AI 정책이 따르는 공통 인터페이스입니다."""

    def __call__(self, observation: dict) -> AIAction:
        raise NotImplementedError

    def selectDecision(self, observation: dict, explore: bool = True) -> PolicyDecision:
        return PolicyDecision(action=self(observation))

    def learnFromTransition(
        self,
        observation: dict,
        decision,
        reward: float,
        nextObservation: dict,
        done: bool,
    ) -> None:
        return None

    def onEpisodeStart(self) -> None:
        return None

    def onEpisodeEnd(self) -> None:
        return None


class HeuristicPolicy(AIPolicy):
    """간단한 거리 규칙 기반 휴리스틱 정책입니다."""

    def __init__(
        self,
        chaseDistance: float = 170.0,
        attackDistance: float = 340.0,
        dashMinDistance: float = 220.0,
        dashMaxDistance: float = 380.0,
    ) -> None:
        self._chaseDistance = float(chaseDistance)
        self._attackDistance = float(attackDistance)
        self._dashMinDistance = float(dashMinDistance)
        self._dashMaxDistance = float(dashMaxDistance)

    def __call__(self, observation: dict) -> AIAction:
        if not observation:
            return AIAction()

        selfPos = Vector2(observation.get("self_position", (0.0, 0.0)))
        enemyPos = Vector2(observation.get("enemy_position", (0.0, 0.0)))
        toEnemy = enemyPos - selfPos
        distance = toEnemy.length()

        moveDirection = Vector2(0.0, 0.0)
        if distance > self._chaseDistance and toEnemy.length_squared() > 0.0:
            moveDirection = toEnemy.normalize()

        attackPosition = None
        if observation.get("can_attack") and distance <= self._attackDistance:
            attackPosition = Vector2(enemyPos)

        dash = (
            observation.get("can_dash")
            and self._dashMinDistance < distance < self._dashMaxDistance
        )

        return AIAction(moveDirection, attackPosition, dash)


class ModelPolicy(AIPolicy):
    """외부 모델의 출력을 AIAction으로 변환하는 어댑터입니다."""

    def __init__(self, modelForward) -> None:
        self._modelForward = modelForward

    def __call__(self, observation: dict) -> AIAction:
        result = self._modelForward(observation)
        if isinstance(result, AIAction):
            return result

        if isinstance(result, (tuple, list)) and len(result) == 3:
            moveDirection, attackPosition, dash = result
            return AIAction(moveDirection, attackPosition, dash)

        return AIAction()


class ObservationEncoder:
    """관측 딕셔너리를 Q-table 상태 문자열로 압축합니다."""

    STATE_TO_BIN = {
        "idle": 0,
        "move": 1,
        "dash": 2,
        "attack": 3,
    }

    def __init__(
        self,
        distanceBins: int = 6,
        hpBins: int = 4,
        angleBins: int = 8,
        cooldownBins: int = 3,
        buffBins: int = 4,
    ) -> None:
        self._distanceBins = max(1, int(distanceBins))
        self._hpBins = max(1, int(hpBins))
        self._angleBins = max(1, int(angleBins))
        self._cooldownBins = max(1, int(cooldownBins))
        self._buffBins = max(1, int(buffBins))

    def encode(self, observation: dict) -> str:
        if not observation:
            return "empty"

        distanceBin = self._binDistance(float(observation.get("distance_to_enemy", 0.0)))
        enemyAngleBin = self._binAngle(observation.get("enemy_direction", (0.0, 0.0)))

        selfHpBin = self._binHp(
            observation.get("self_hp", 0),
            observation.get("self_hp_max", 1),
        )
        enemyHpBin = self._binHp(
            observation.get("enemy_hp", 0),
            observation.get("enemy_hp_max", 1),
        )

        selfStateBin = self._binState(observation.get("state", "idle"))
        enemyStateBin = self._binState(observation.get("enemy_state", "idle"))

        selfCombatReadinessBin = self._binCombatReadiness(
            float(observation.get("self_attack_cooldown_ratio", 0.0)),
            float(observation.get("self_dash_cooldown_ratio", 0.0)),
        )
        enemyCombatReadinessBin = self._binCombatReadiness(
            float(observation.get("enemy_attack_cooldown_ratio", 0.0)),
            float(observation.get("enemy_dash_cooldown_ratio", 0.0)),
        )

        coverDistanceBin = self._binDistance(float(observation.get("nearest_cover_distance", 9999.0)))
        coverAdvantageBin = self._binCoverAdvantage(
            observation.get("self_position", (0.0, 0.0)),
            observation.get("enemy_position", (0.0, 0.0)),
            observation.get("cover_positions", ()),
        )
        itemRaceBin = self._binItemRace(
            bool(observation.get("item_active", False)),
            float(observation.get("self_item_distance", 9999.0)),
            float(observation.get("enemy_item_distance", 9999.0)),
        )
        itemDistanceBin = self._binDistance(float(observation.get("self_item_distance", 9999.0)))
        bulletThreatBin = self._binBulletThreat(
            int(observation.get("enemy_bullet_count", 0)),
            float(observation.get("nearest_enemy_bullet_distance", 9999.0)),
            float(observation.get("second_enemy_bullet_distance", 9999.0)),
        )
        bulletAngleBin = self._binAngle(
            observation.get("nearest_enemy_bullet_direction", (0.0, 0.0))
        )

        buffStateBin = self._binBuffState(
            bool(observation.get("self_has_attack_buff", False)),
            bool(observation.get("enemy_has_attack_buff", False)),
            float(observation.get("self_attack_buff_ratio", 0.0)),
            float(observation.get("enemy_attack_buff_ratio", 0.0)),
        )

        return (
            f"{distanceBin}|{enemyAngleBin}|{selfHpBin}|{enemyHpBin}|"
            f"{selfStateBin}|{enemyStateBin}|"
            f"{selfCombatReadinessBin}|{enemyCombatReadinessBin}|"
            f"{coverDistanceBin}|{coverAdvantageBin}|"
            f"{itemRaceBin}|{itemDistanceBin}|"
            f"{bulletThreatBin}|{bulletAngleBin}|"
            f"{buffStateBin}"
        )

    def _binDistance(self, distance: float, maxDistance: float = 900.0) -> int:
        normalized = max(0.0, min(distance / maxDistance, 1.0))
        return min(self._distanceBins - 1, int(normalized * self._distanceBins))

    def _binHp(self, hp: float, hpMax: float) -> int:
        hpMax = max(1.0, float(hpMax))
        ratio = max(0.0, min(float(hp) / hpMax, 1.0))
        return min(self._hpBins - 1, int(ratio * self._hpBins))

    def _binRatio(self, ratio: float, binCount: int) -> int:
        normalized = max(0.0, min(float(ratio), 1.0))
        return min(binCount - 1, int(normalized * binCount))

    def _binCombatReadiness(self, attackRatio: float, dashRatio: float) -> int:
        score = max(0.0, min((float(attackRatio) + float(dashRatio)) * 0.5, 1.0))
        return self._binRatio(score, self._cooldownBins)

    def _binAngle(self, direction) -> int:
        x = float(direction[0]) if len(direction) >= 1 else 0.0
        y = float(direction[1]) if len(direction) >= 2 else 0.0
        if x == 0.0 and y == 0.0:
            return 0

        angle = math.atan2(y, x)
        normalized = (angle + math.pi) / (2.0 * math.pi)
        return min(self._angleBins - 1, int(normalized * self._angleBins))

    def _binState(self, stateName: str) -> int:
        return self.STATE_TO_BIN.get(str(stateName).strip().lower(), 0)

    def _binCoverAdvantage(self, selfPosition, enemyPosition, coverPositions) -> int:
        selfPos = Vector2(selfPosition)
        enemyPos = Vector2(enemyPosition)
        bestScore = 0.0

        for coverPosition in coverPositions:
            coverPos = Vector2(coverPosition)
            bestScore = max(bestScore, self._computeCoverScore(selfPos, enemyPos, coverPos))

        if bestScore >= 0.75:
            return 3
        if bestScore >= 0.5:
            return 2
        if bestScore >= 0.25:
            return 1
        return 0

    def _computeCoverScore(self, selfPos: Vector2, enemyPos: Vector2, coverPos: Vector2) -> float:
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

    def _binItemRace(self, itemActive: bool, selfDistance: float, enemyDistance: float) -> int:
        if not itemActive or selfDistance >= 9999.0:
            return 0

        distanceGap = float(enemyDistance) - float(selfDistance)
        if distanceGap >= 60.0:
            return 2
        if distanceGap >= -60.0:
            return 1
        return 0

    def _binBuffState(
        self,
        selfHasBuff: bool,
        enemyHasBuff: bool,
        selfBuffRatio: float,
        enemyBuffRatio: float,
    ) -> int:
        if self._buffBins <= 1:
            return 0

        if not selfHasBuff and not enemyHasBuff:
            return 0
        if selfHasBuff and not enemyHasBuff:
            return min(self._buffBins - 1, 2 + int(selfBuffRatio >= 0.5))
        if enemyHasBuff and not selfHasBuff:
            return 1
        if selfHasBuff and enemyHasBuff:
            return self._buffBins - 1 if selfBuffRatio >= enemyBuffRatio else max(1, self._buffBins - 2)
        return 0

    def _binBulletThreat(self, bulletCount: int, nearestDistance: float, secondDistance: float) -> int:
        if bulletCount <= 0 or nearestDistance >= 9999.0:
            return 0
        if nearestDistance <= 90.0:
            return 4 if bulletCount >= 2 and secondDistance <= 160.0 else 3
        if nearestDistance <= 180.0:
            return 2
        return 1


class TabularQPolicy(AIPolicy):
    """테이블 기반 상태-행동 값을 사용하는 Q-learning 정책입니다."""

    ACTION_IDLE = 0
    ACTION_MOVE_UP = 1
    ACTION_MOVE_UP_RIGHT = 2
    ACTION_MOVE_RIGHT = 3
    ACTION_MOVE_DOWN_RIGHT = 4
    ACTION_MOVE_DOWN = 5
    ACTION_MOVE_DOWN_LEFT = 6
    ACTION_MOVE_LEFT = 7
    ACTION_MOVE_UP_LEFT = 8
    ACTION_MOVE_TO_ENEMY = 9
    ACTION_MOVE_AWAY_FROM_ENEMY = 10
    ACTION_MOVE_TO_COVER = 11
    ACTION_MOVE_AWAY_FROM_COVER = 12
    ACTION_MOVE_TO_ITEM = 13
    ACTION_MOVE_AWAY_FROM_ITEM = 14
    ACTION_ATTACK = 15
    ACTION_ATTACK_UP = 16
    ACTION_ATTACK_UP_RIGHT = 17
    ACTION_ATTACK_RIGHT = 18
    ACTION_ATTACK_DOWN_RIGHT = 19
    ACTION_ATTACK_DOWN = 20
    ACTION_ATTACK_DOWN_LEFT = 21
    ACTION_ATTACK_LEFT = 22
    ACTION_ATTACK_UP_LEFT = 23
    ACTION_ATTACK_OFFSET_LEFT = 24
    ACTION_ATTACK_OFFSET_RIGHT = 25
    ACTION_ATTACK_OFFSET_FORWARD = 26
    ACTION_ATTACK_OFFSET_BACKWARD = 27
    ACTION_ATTACK_AND_CHASE = 28
    ACTION_ATTACK_AND_RETREAT = 29
    ACTION_DASH_UP = 30
    ACTION_DASH_UP_RIGHT = 31
    ACTION_DASH_RIGHT = 32
    ACTION_DASH_DOWN_RIGHT = 33
    ACTION_DASH_DOWN = 34
    ACTION_DASH_DOWN_LEFT = 35
    ACTION_DASH_LEFT = 36
    ACTION_DASH_UP_LEFT = 37
    ACTION_DASH_TO_ENEMY = 38
    ACTION_DASH_AWAY_FROM_ENEMY = 39
    ACTION_DASH_TO_COVER = 40
    ACTION_DASH_TO_ITEM = 41

    ATTACK_AIM_OFFSET_DISTANCE = 35.0
    CHECKPOINT_FORMAT_VERSION = 3
    CHECKPOINT_QVALUE_SAVE_EPSILON = 1e-3
    CHECKPOINT_QVALUE_DECIMALS = 4
    CHECKPOINT_MIN_VISIT_SAVE_COUNT = 2

    DIRECTION_UP = Vector2(0.0, -1.0)
    DIRECTION_UP_RIGHT = Vector2(1.0, -1.0).normalize()
    DIRECTION_RIGHT = Vector2(1.0, 0.0)
    DIRECTION_DOWN_RIGHT = Vector2(1.0, 1.0).normalize()
    DIRECTION_DOWN = Vector2(0.0, 1.0)
    DIRECTION_DOWN_LEFT = Vector2(-1.0, 1.0).normalize()
    DIRECTION_LEFT = Vector2(-1.0, 0.0)
    DIRECTION_UP_LEFT = Vector2(-1.0, -1.0).normalize()

    def __init__(
        self,
        alpha: float = 0.10,
        gamma: float = 0.96,
        epsilon: float = 0.25,
        epsilonMin: float = 0.05,
        epsilonDecay: float = 0.997,
        minAlpha: float = 0.02,
        tdErrorClip: float = 2.5,
        qValueClip: float = 12.0,
        rewardClip: float = 3.0,
        unexploredActionBias: float = 0.70,
        seed: int | None = None,
    ) -> None:
        self._alpha = float(alpha)
        self._gamma = float(gamma)
        self._epsilon = float(epsilon)
        self._epsilonMin = float(epsilonMin)
        self._epsilonDecay = float(epsilonDecay)
        self._minAlpha = float(minAlpha)
        self._tdErrorClip = float(tdErrorClip)
        self._qValueClip = float(qValueClip)
        self._rewardClip = float(rewardClip)
        self._unexploredActionBias = float(unexploredActionBias)

        self._encoder = ObservationEncoder()
        self._qTable: dict[str, list[float]] = {}
        self._visitCounts: dict[str, list[int]] = {}
        self._actionCount = 42
        self._rng = random.Random(seed)

    def __call__(self, observation: dict) -> AIAction:
        return self.selectDecision(observation, explore=True).action

    def selectDecision(self, observation: dict, explore: bool = True) -> PolicyDecision:
        stateKey = self._encoder.encode(observation)
        validActionIndices = self._getValidActionIndices(observation)
        actionIndex = self._selectActionIndex(stateKey, validActionIndices, explore=explore)
        return PolicyDecision(
            action=self._decodeAction(actionIndex, observation),
            actionIndex=actionIndex,
            stateKey=stateKey,
        )

    def selectAction(self, observation: dict, explore: bool = True) -> tuple[int, AIAction]:
        decision = self.selectDecision(observation, explore=explore)
        return int(decision.actionIndex or 0), decision.action

    def learn(
        self,
        observation: dict,
        actionIndex: int,
        reward: float,
        nextObservation: dict,
        done: bool,
    ) -> None:
        stateKey = self._encoder.encode(observation)
        self._learnEncodedState(stateKey, actionIndex, reward, nextObservation, done)

    def learnFromTransition(
        self,
        observation: dict,
        decision,
        reward: float,
        nextObservation: dict,
        done: bool,
    ) -> None:
        if decision.actionIndex is None:
            return

        stateKey = decision.stateKey
        if stateKey is None:
            stateKey = self._encoder.encode(observation)

        self._learnEncodedState(stateKey, decision.actionIndex, reward, nextObservation, done)

    def onEpisodeEnd(self) -> None:
        self.decayEpsilon()

    def onEpisodeStart(self) -> None:
        return None

    def _learnEncodedState(
        self,
        stateKey: str,
        actionIndex: int,
        reward: float,
        nextObservation: dict,
        done: bool,
    ) -> None:
        nextStateKey = self._encoder.encode(nextObservation)

        qValues = self._ensureState(stateKey)
        nextQValues = self._ensureState(nextStateKey)
        visitCounts = self._ensureVisitState(stateKey)

        oldQ = qValues[actionIndex]
        clippedReward = max(-self._rewardClip, min(self._rewardClip, float(reward)))
        nextBest = 0.0 if done else max(nextQValues)
        target = clippedReward + (self._gamma * nextBest)
        tdError = target - oldQ
        tdError = max(-self._tdErrorClip, min(self._tdErrorClip, tdError))
        adaptiveAlpha = max(self._minAlpha, self._alpha / math.sqrt(1.0 + visitCounts[actionIndex]))
        updatedQ = oldQ + (adaptiveAlpha * tdError)
        qValues[actionIndex] = max(-self._qValueClip, min(self._qValueClip, updatedQ))
        visitCounts[actionIndex] += 1

    def decayEpsilon(self) -> None:
        self._epsilon = max(self._epsilonMin, self._epsilon * self._epsilonDecay)

    def getEpsilon(self) -> float:
        return self._epsilon

    def save(self, path: str) -> None:
        savePath = Path(path)
        savePath.parent.mkdir(parents=True, exist_ok=True)
        serializedTable, serializedVisits = self._buildSparseCheckpointPayload()
        payload = {
            "format_version": self.CHECKPOINT_FORMAT_VERSION,
            "alpha": self._alpha,
            "gamma": self._gamma,
            "epsilon": self._epsilon,
            "epsilon_min": self._epsilonMin,
            "epsilon_decay": self._epsilonDecay,
            "min_alpha": self._minAlpha,
            "td_error_clip": self._tdErrorClip,
            "q_value_clip": self._qValueClip,
            "reward_clip": self._rewardClip,
            "unexplored_action_bias": self._unexploredActionBias,
            "action_count": self._actionCount,
            "q_table": serializedTable,
            "visit_counts": serializedVisits,
        }
        with self._openCheckpoint(savePath, "wt") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    def load(self, path: str) -> bool:
        loadPath = Path(path)
        if not loadPath.exists():
            return False

        with self._openCheckpoint(loadPath, "rt") as f:
            payload = json.load(f)

        self._alpha = float(payload.get("alpha", self._alpha))
        self._gamma = float(payload.get("gamma", self._gamma))
        self._epsilon = float(payload.get("epsilon", self._epsilon))
        self._epsilonMin = float(payload.get("epsilon_min", self._epsilonMin))
        self._epsilonDecay = float(payload.get("epsilon_decay", self._epsilonDecay))
        self._minAlpha = float(payload.get("min_alpha", self._minAlpha))
        self._tdErrorClip = float(payload.get("td_error_clip", self._tdErrorClip))
        self._qValueClip = float(payload.get("q_value_clip", self._qValueClip))
        self._rewardClip = float(payload.get("reward_clip", self._rewardClip))
        self._unexploredActionBias = float(payload.get("unexplored_action_bias", self._unexploredActionBias))
        savedActionCount = int(payload.get("action_count", self._actionCount))
        formatVersion = int(payload.get("format_version", 1))

        rawTable = payload.get("q_table", {})
        self._qTable = {}
        rawVisitCounts = payload.get("visit_counts", {})
        self._visitCounts = {}

        if formatVersion >= 2:
            self._loadSparseCheckpoint(rawTable, rawVisitCounts)
        else:
            self._loadDenseCheckpoint(rawTable, rawVisitCounts, savedActionCount)

        return True

    def _buildSparseCheckpointPayload(self) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, int]]]:
        serializedTable: dict[str, dict[str, float]] = {}
        serializedVisits: dict[str, dict[str, int]] = {}

        allStateKeys = set(self._qTable.keys()) | set(self._visitCounts.keys())
        for stateKey in allStateKeys:
            qValues = self._qTable.get(stateKey, [0.0] * self._actionCount)
            visitCounts = self._visitCounts.get(stateKey, [0] * self._actionCount)

            sparseQ = {
                str(index): round(float(qValue), self.CHECKPOINT_QVALUE_DECIMALS)
                for index, qValue in enumerate(qValues)
                if abs(float(qValue)) >= self.CHECKPOINT_QVALUE_SAVE_EPSILON
            }
            sparseVisits = {
                str(index): int(visitCount)
                for index, visitCount in enumerate(visitCounts)
                if int(visitCount) >= self.CHECKPOINT_MIN_VISIT_SAVE_COUNT
            }

            if sparseQ:
                serializedTable[stateKey] = sparseQ
            if sparseVisits:
                serializedVisits[stateKey] = sparseVisits

        return serializedTable, serializedVisits

    def _loadDenseCheckpoint(self, rawTable: dict, rawVisitCounts: dict, savedActionCount: int) -> None:
        for key, values in rawTable.items():
            if not isinstance(values, list):
                continue
            limitedValues = values[: max(0, savedActionCount)]
            q = [float(v) for v in limitedValues[: self._actionCount]]
            if len(q) < self._actionCount:
                q.extend([0.0] * (self._actionCount - len(q)))
            if any(abs(value) >= self.CHECKPOINT_QVALUE_SAVE_EPSILON for value in q):
                self._qTable[key] = q

        for key, values in rawVisitCounts.items():
            if not isinstance(values, list):
                continue
            visitValues = values[: max(0, savedActionCount)]
            counts = [max(0, int(v)) for v in visitValues[: self._actionCount]]
            if len(counts) < self._actionCount:
                counts.extend([0] * (self._actionCount - len(counts)))
            if any(value >= self.CHECKPOINT_MIN_VISIT_SAVE_COUNT for value in counts):
                self._visitCounts[key] = counts

    def _loadSparseCheckpoint(self, rawTable: dict, rawVisitCounts: dict) -> None:
        for key, values in rawTable.items():
            if not isinstance(values, dict):
                continue
            qValues = [0.0] * self._actionCount
            for rawIndex, rawValue in values.items():
                index = self._parseActionIndex(rawIndex)
                if index is None:
                    continue
                qValues[index] = float(rawValue)
            if any(abs(value) >= self.CHECKPOINT_QVALUE_SAVE_EPSILON for value in qValues):
                self._qTable[key] = qValues

        for key, values in rawVisitCounts.items():
            if not isinstance(values, dict):
                continue
            counts = [0] * self._actionCount
            for rawIndex, rawValue in values.items():
                index = self._parseActionIndex(rawIndex)
                if index is None:
                    continue
                counts[index] = max(0, int(rawValue))
            if any(value >= self.CHECKPOINT_MIN_VISIT_SAVE_COUNT for value in counts):
                self._visitCounts[key] = counts

    def _parseActionIndex(self, value) -> int | None:
        try:
            index = int(value)
        except (TypeError, ValueError):
            return None
        if 0 <= index < self._actionCount:
            return index
        return None

    def _openCheckpoint(self, path: Path, mode: str):
        if path.suffix == ".gz":
            return gzip.open(path, mode, encoding="utf-8")
        return path.open(mode, encoding="utf-8")

    def _selectActionIndex(self, stateKey: str, validActionIndices: list[int], explore: bool = True) -> int:
        qValues = self._ensureState(stateKey)
        visitCounts = self._ensureVisitState(stateKey)
        candidateIndices = validActionIndices[:] if validActionIndices else list(range(self._actionCount))

        if explore and self._rng.random() < self._epsilon:
            unexploredIndices = [index for index in candidateIndices if visitCounts[index] == 0]
            if unexploredIndices and self._rng.random() < self._unexploredActionBias:
                return self._rng.choice(unexploredIndices)
            minVisits = min(visitCounts[index] for index in candidateIndices)
            leastVisitedIndices = [index for index in candidateIndices if visitCounts[index] == minVisits]
            return self._rng.choice(leastVisitedIndices)

        maxQ = max(qValues[index] for index in candidateIndices)
        bestIndices = [index for index in candidateIndices if qValues[index] == maxQ]
        return self._rng.choice(bestIndices)

    def _ensureState(self, stateKey: str) -> list[float]:
        if stateKey not in self._qTable:
            self._qTable[stateKey] = [0.0 for _ in range(self._actionCount)]
        return self._qTable[stateKey]

    def _ensureVisitState(self, stateKey: str) -> list[int]:
        if stateKey not in self._visitCounts:
            self._visitCounts[stateKey] = [0 for _ in range(self._actionCount)]
        return self._visitCounts[stateKey]

    def _getValidActionIndices(self, observation: dict) -> list[int]:
        canAttack = bool(observation.get("can_attack", False))
        canDash = bool(observation.get("can_dash", False))
        itemActive = bool(observation.get("item_active", False))
        validIndices = [
            self.ACTION_IDLE,
            self.ACTION_MOVE_UP,
            self.ACTION_MOVE_UP_RIGHT,
            self.ACTION_MOVE_RIGHT,
            self.ACTION_MOVE_DOWN_RIGHT,
            self.ACTION_MOVE_DOWN,
            self.ACTION_MOVE_DOWN_LEFT,
            self.ACTION_MOVE_LEFT,
            self.ACTION_MOVE_UP_LEFT,
            self.ACTION_MOVE_TO_ENEMY,
            self.ACTION_MOVE_AWAY_FROM_ENEMY,
            self.ACTION_MOVE_TO_COVER,
            self.ACTION_MOVE_AWAY_FROM_COVER,
        ]

        if itemActive:
            validIndices.extend([self.ACTION_MOVE_TO_ITEM, self.ACTION_MOVE_AWAY_FROM_ITEM])

        if canAttack:
            validIndices.extend(
                [
                    self.ACTION_ATTACK,
                    self.ACTION_ATTACK_UP,
                    self.ACTION_ATTACK_UP_RIGHT,
                    self.ACTION_ATTACK_RIGHT,
                    self.ACTION_ATTACK_DOWN_RIGHT,
                    self.ACTION_ATTACK_DOWN,
                    self.ACTION_ATTACK_DOWN_LEFT,
                    self.ACTION_ATTACK_LEFT,
                    self.ACTION_ATTACK_UP_LEFT,
                    self.ACTION_ATTACK_OFFSET_LEFT,
                    self.ACTION_ATTACK_OFFSET_RIGHT,
                    self.ACTION_ATTACK_OFFSET_FORWARD,
                    self.ACTION_ATTACK_OFFSET_BACKWARD,
                    self.ACTION_ATTACK_AND_CHASE,
                    self.ACTION_ATTACK_AND_RETREAT,
                ]
            )
        else:
            validIndices.extend([self.ACTION_ATTACK_AND_CHASE, self.ACTION_ATTACK_AND_RETREAT])

        if canDash:
            validIndices.extend(
                [
                    self.ACTION_DASH_UP,
                    self.ACTION_DASH_UP_RIGHT,
                    self.ACTION_DASH_RIGHT,
                    self.ACTION_DASH_DOWN_RIGHT,
                    self.ACTION_DASH_DOWN,
                    self.ACTION_DASH_DOWN_LEFT,
                    self.ACTION_DASH_LEFT,
                    self.ACTION_DASH_UP_LEFT,
                    self.ACTION_DASH_TO_ENEMY,
                    self.ACTION_DASH_AWAY_FROM_ENEMY,
                    self.ACTION_DASH_TO_COVER,
                ]
            )
            if itemActive:
                validIndices.append(self.ACTION_DASH_TO_ITEM)

        return validIndices

    def _decodeAction(self, actionIndex: int, observation: dict) -> AIAction:
        selfPos = Vector2(observation.get("self_position", (0.0, 0.0)))
        enemyPos = Vector2(observation.get("enemy_position", (0.0, 0.0)))
        toEnemy = enemyPos - selfPos

        moveToEnemy = self._normalizedDirection(toEnemy)
        moveAwayFromEnemy = -moveToEnemy if moveToEnemy.length_squared() > 0.0 else Vector2(0.0, 0.0)
        enemyLateralLeft = self._perpendicularLeft(moveToEnemy)
        enemyLateralRight = -enemyLateralLeft if enemyLateralLeft.length_squared() > 0.0 else Vector2(0.0, 0.0)
        moveToCover = self._directionFromObservation(
            observation.get("nearest_cover_direction", (0.0, 0.0))
        )
        moveAwayFromCover = -moveToCover if moveToCover.length_squared() > 0.0 else Vector2(0.0, 0.0)
        moveToItem = self._directionFromObservation(
            observation.get("self_item_direction", (0.0, 0.0))
        )
        moveAwayFromItem = -moveToItem if moveToItem.length_squared() > 0.0 else Vector2(0.0, 0.0)

        canAttack = bool(observation.get("can_attack", False))
        canDash = bool(observation.get("can_dash", False))
        itemActive = bool(observation.get("item_active", False))

        directionActions = {
            self.ACTION_MOVE_UP: self.DIRECTION_UP,
            self.ACTION_MOVE_UP_RIGHT: self.DIRECTION_UP_RIGHT,
            self.ACTION_MOVE_RIGHT: self.DIRECTION_RIGHT,
            self.ACTION_MOVE_DOWN_RIGHT: self.DIRECTION_DOWN_RIGHT,
            self.ACTION_MOVE_DOWN: self.DIRECTION_DOWN,
            self.ACTION_MOVE_DOWN_LEFT: self.DIRECTION_DOWN_LEFT,
            self.ACTION_MOVE_LEFT: self.DIRECTION_LEFT,
            self.ACTION_MOVE_UP_LEFT: self.DIRECTION_UP_LEFT,
        }
        if actionIndex in directionActions:
            return AIAction(directionActions[actionIndex], None, False)

        dashDirectionActions = {
            self.ACTION_DASH_UP: self.DIRECTION_UP,
            self.ACTION_DASH_UP_RIGHT: self.DIRECTION_UP_RIGHT,
            self.ACTION_DASH_RIGHT: self.DIRECTION_RIGHT,
            self.ACTION_DASH_DOWN_RIGHT: self.DIRECTION_DOWN_RIGHT,
            self.ACTION_DASH_DOWN: self.DIRECTION_DOWN,
            self.ACTION_DASH_DOWN_LEFT: self.DIRECTION_DOWN_LEFT,
            self.ACTION_DASH_LEFT: self.DIRECTION_LEFT,
            self.ACTION_DASH_UP_LEFT: self.DIRECTION_UP_LEFT,
        }
        if actionIndex in dashDirectionActions and canDash:
            return AIAction(dashDirectionActions[actionIndex], None, True)

        attackDirectionActions = {
            self.ACTION_ATTACK_UP: self.DIRECTION_UP,
            self.ACTION_ATTACK_UP_RIGHT: self.DIRECTION_UP_RIGHT,
            self.ACTION_ATTACK_RIGHT: self.DIRECTION_RIGHT,
            self.ACTION_ATTACK_DOWN_RIGHT: self.DIRECTION_DOWN_RIGHT,
            self.ACTION_ATTACK_DOWN: self.DIRECTION_DOWN,
            self.ACTION_ATTACK_DOWN_LEFT: self.DIRECTION_DOWN_LEFT,
            self.ACTION_ATTACK_LEFT: self.DIRECTION_LEFT,
            self.ACTION_ATTACK_UP_LEFT: self.DIRECTION_UP_LEFT,
        }
        if actionIndex in attackDirectionActions and canAttack:
            return AIAction(
                Vector2(0.0, 0.0),
                selfPos + (attackDirectionActions[actionIndex] * self.ATTACK_AIM_OFFSET_DISTANCE),
                False,
            )

        if actionIndex == self.ACTION_MOVE_TO_ENEMY:
            return AIAction(moveToEnemy, None, False)

        if actionIndex == self.ACTION_MOVE_AWAY_FROM_ENEMY:
            return AIAction(moveAwayFromEnemy, None, False)

        if actionIndex == self.ACTION_MOVE_TO_COVER:
            return AIAction(moveToCover, None, False)

        if actionIndex == self.ACTION_MOVE_AWAY_FROM_COVER:
            return AIAction(moveAwayFromCover, None, False)

        if actionIndex == self.ACTION_MOVE_TO_ITEM:
            return AIAction(moveToItem if itemActive else Vector2(0.0, 0.0), None, False)

        if actionIndex == self.ACTION_MOVE_AWAY_FROM_ITEM:
            return AIAction(moveAwayFromItem if itemActive else Vector2(0.0, 0.0), None, False)

        if actionIndex == self.ACTION_ATTACK and canAttack:
            return AIAction(Vector2(0.0, 0.0), enemyPos, False)

        if actionIndex == self.ACTION_ATTACK_OFFSET_LEFT and canAttack:
            return AIAction(
                Vector2(0.0, 0.0),
                self._buildAttackPosition(enemyPos, moveToEnemy, enemyLateralLeft, 0.0, 1.0),
                False,
            )

        if actionIndex == self.ACTION_ATTACK_OFFSET_RIGHT and canAttack:
            return AIAction(
                Vector2(0.0, 0.0),
                self._buildAttackPosition(enemyPos, moveToEnemy, enemyLateralRight, 0.0, 1.0),
                False,
            )

        if actionIndex == self.ACTION_ATTACK_OFFSET_FORWARD and canAttack:
            return AIAction(
                Vector2(0.0, 0.0),
                self._buildAttackPosition(enemyPos, moveToEnemy, Vector2(0.0, 0.0), 1.0, 0.0),
                False,
            )

        if actionIndex == self.ACTION_ATTACK_OFFSET_BACKWARD and canAttack:
            return AIAction(
                Vector2(0.0, 0.0),
                self._buildAttackPosition(enemyPos, moveToEnemy, Vector2(0.0, 0.0), -1.0, 0.0),
                False,
            )

        if actionIndex == self.ACTION_ATTACK_AND_CHASE:
            attackPosition = enemyPos if canAttack else None
            return AIAction(moveToEnemy, attackPosition, False)

        if actionIndex == self.ACTION_ATTACK_AND_RETREAT:
            attackPosition = enemyPos if canAttack else None
            return AIAction(moveAwayFromEnemy, attackPosition, False)

        if actionIndex == self.ACTION_DASH_TO_ENEMY and canDash:
            return AIAction(moveToEnemy, None, True)

        if actionIndex == self.ACTION_DASH_AWAY_FROM_ENEMY and canDash:
            return AIAction(moveAwayFromEnemy, None, True)

        if actionIndex == self.ACTION_DASH_TO_COVER and canDash:
            return AIAction(moveToCover, None, True)

        if actionIndex == self.ACTION_DASH_TO_ITEM and canDash and itemActive:
            return AIAction(moveToItem, None, True)

        return AIAction()

    def _directionFromObservation(self, value) -> Vector2:
        return self._normalizedDirection(Vector2(value))

    def _normalizedDirection(self, direction: Vector2) -> Vector2:
        direction = Vector2(direction)
        if direction.length_squared() == 0.0:
            return Vector2(0.0, 0.0)
        return direction.normalize()

    def _perpendicularLeft(self, direction: Vector2) -> Vector2:
        if direction.length_squared() == 0.0:
            return Vector2(0.0, 0.0)
        return Vector2(-direction.y, direction.x).normalize()

    def _buildAttackPosition(
        self,
        enemyPos: Vector2,
        forwardDirection: Vector2,
        lateralDirection: Vector2,
        forwardScale: float,
        lateralScale: float,
    ) -> Vector2:
        return Vector2(enemyPos) + (
            (forwardDirection * self.ATTACK_AIM_OFFSET_DISTANCE * float(forwardScale))
            + (lateralDirection * self.ATTACK_AIM_OFFSET_DISTANCE * float(lateralScale))
        )


class PolicyFactory:
    """정책 종류 이름으로 정책 객체를 생성합니다."""

    _builders: dict[str, object] = {}

    @classmethod
    def register(cls, kind: str, builder) -> None:
        cls._builders[str(kind).strip().lower()] = builder

    @classmethod
    def create(cls, spec: PolicySpec) -> AIPolicy:
        kind = str(spec.kind).strip().lower()
        if kind not in cls._builders:
            available = ", ".join(sorted(cls._builders.keys()))
            raise ValueError(f"Unknown policy kind: {spec.kind}. Available: {available}")

        builder = cls._builders[kind]
        return builder(dict(spec.options))

    @classmethod
    def loadCheckpoint(cls, policy: AIPolicy, checkpointPath: Path) -> bool:
        if not hasattr(policy, "load"):
            return False
        return bool(policy.load(str(checkpointPath)))


PolicyFactory.register("heuristic", lambda options: HeuristicPolicy(**options))
PolicyFactory.register("qtable", lambda options: TabularQPolicy(**options))
