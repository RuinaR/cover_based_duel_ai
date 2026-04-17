from dataclasses import dataclass, field
from pathlib import Path

from shooter.components.ai_controller import AIAction


@dataclass(slots=True)
class BattleFrameTrace:
    """현재 프레임 처리 흐름을 문자열 목록으로 기록합니다."""

    entries: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.entries.append(message)

    def asTuple(self) -> tuple[str, ...]:
        return tuple(self.entries)


@dataclass(slots=True)
class BattleFrameDecision:
    """한 판단 구간에서 선택된 액션과 학습용 정보를 담습니다."""

    tag: str
    observation: dict
    action: AIAction
    actionIndex: int | None = None
    stateKey: str | None = None
    source: str = "idle"


@dataclass(slots=True)
class BattleFrameResult:
    """프레임 처리 결과를 담습니다."""

    frameIndex: int
    observations: dict
    nextObservations: dict
    rewards: dict
    done: bool
    winner: str | None
    callStack: tuple[str, ...]
    episodeSummary: str | None = None


class PolicyRuntime:
    """정책의 판단 주기, 학습, 저장 동작을 관리합니다."""

    def __init__(
        self,
        tag: str,
        policy=None,
        checkpointPath: str | Path | None = None,
        trainingEnabled: bool = False,
        explore: bool = True,
        thinkInterval: int = 5,
        saveOnEpisodeEnd: bool = True,
    ) -> None:
        self._tag = tag
        self._policy = policy
        self._checkpointPath = None if checkpointPath is None else Path(checkpointPath)
        self._trainingEnabled = bool(trainingEnabled)
        self._explore = bool(explore)
        self._thinkInterval = max(1, int(thinkInterval))
        self._saveOnEpisodeEnd = bool(saveOnEpisodeEnd)
        self._activeDecision: BattleFrameDecision | None = None
        self._accumulatedReward = 0.0
        self._stepsSinceDecision = 0

    def decide(self, observation: dict, trace: BattleFrameTrace) -> BattleFrameDecision:
        if self._policy is None:
            trace.add(f"  {self._tag}: no policy -> AIAction()")
            return BattleFrameDecision(self._tag, observation, AIAction(), source="idle")

        if self._activeDecision is None:
            trace.add(
                f"  {self._tag}: {type(self._policy).__name__}.selectDecision(observation) "
                f"[thinkInterval={self._thinkInterval}]"
            )
            decision = self._policy.selectDecision(observation, explore=self._explore)
            self._activeDecision = BattleFrameDecision(
                tag=self._tag,
                observation=observation,
                action=decision.action,
                actionIndex=decision.actionIndex,
                stateKey=decision.stateKey,
                source=type(self._policy).__name__,
            )
            self._accumulatedReward = 0.0
            self._stepsSinceDecision = 0
        else:
            trace.add(
                f"  {self._tag}: reuse cached action "
                f"(step {self._stepsSinceDecision + 1}/{self._thinkInterval})"
            )

        return self._activeDecision

    def advanceInterval(
        self,
        reward: float,
        nextObservation: dict,
        done: bool,
        trace: BattleFrameTrace,
    ) -> None:
        if self._activeDecision is None:
            return

        self._accumulatedReward += float(reward)
        self._stepsSinceDecision += 1

        if not done and self._stepsSinceDecision < self._thinkInterval:
            return

        if self._trainingEnabled and self._policy is not None:
            trace.add(
                f"  {self._tag}: {type(self._policy).__name__}.learnFromTransition(...) "
                f"[reward_sum={self._accumulatedReward:.3f}, steps={self._stepsSinceDecision}]"
            )
            self._policy.learnFromTransition(
                self._activeDecision.observation,
                self._activeDecision,
                self._accumulatedReward,
                nextObservation,
                done,
            )

        self._activeDecision = None
        self._accumulatedReward = 0.0
        self._stepsSinceDecision = 0

    def finishEpisode(self, trace: BattleFrameTrace) -> None:
        if self._policy is None:
            return

        trace.add(f"  {self._tag}: {type(self._policy).__name__}.onEpisodeEnd()")
        self._policy.onEpisodeEnd()

        if self._saveOnEpisodeEnd:
            self.saveCheckpoint(trace)

    def saveCheckpoint(self, trace: BattleFrameTrace | None = None) -> None:
        if self._policy is None or self._checkpointPath is None:
            return

        if trace is not None:
            trace.add(f"  {self._tag}: {type(self._policy).__name__}.save('{self._checkpointPath}')")
        self._policy.save(str(self._checkpointPath))

    def resetEpisode(self) -> None:
        self._activeDecision = None
        self._accumulatedReward = 0.0
        self._stepsSinceDecision = 0
        if self._policy is None:
            return
        self._policy.onEpisodeStart()

    def discardEpisodeProgress(self) -> None:
        self._activeDecision = None
        self._accumulatedReward = 0.0
        self._stepsSinceDecision = 0

    def getEpsilon(self) -> float | None:
        if self._policy is None or not hasattr(self._policy, "getEpsilon"):
            return None
        return self._policy.getEpsilon()
