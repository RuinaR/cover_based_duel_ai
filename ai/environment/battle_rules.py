from dataclasses import dataclass

from ai.environment.battle_event_bus import BattleEventBus


@dataclass(slots=True)
class BattleOutcome:
    """한 프레임의 보상과 종료 상태를 보관합니다."""

    rewards: dict
    done: bool
    winner: str | None


class BattleRules:
    HIT_REWARD = 1.0
    DEATH_PENALTY = 5.0
    KILL_REWARD = 5.0
    ITEM_PICKUP_REWARD = 1.3
    ITEM_PICKUP_BUFF_ONLY_REWARD = 1.0
    DODGE_REWARD = 0.25
    COVER_BLOCK_REWARD = 0.35
    """전투 이벤트를 바탕으로 보상과 승패를 계산합니다."""

    def __init__(self, tagA: str, tagB: str) -> None:
        self._tagA = tagA
        self._tagB = tagB
        self._done = False
        self._winner = None
        self._rewards = {
            self._tagA: 0.0,
            self._tagB: 0.0,
        }

    def resetEpisode(self) -> None:
        """에피소드 상태와 이벤트 큐를 초기화합니다."""
        BattleEventBus.getInstance().clear()
        self._done = False
        self._winner = None
        self._rewards[self._tagA] = 0.0
        self._rewards[self._tagB] = 0.0

    def resolveFrame(self) -> BattleOutcome:
        """현재까지 쌓인 전투 이벤트를 소비해 프레임 결과를 만듭니다."""
        self._consumeBattleEvents()
        rewards = {
            self._tagA: self._rewards[self._tagA],
            self._tagB: self._rewards[self._tagB],
        }
        self._rewards[self._tagA] = 0.0
        self._rewards[self._tagB] = 0.0
        return BattleOutcome(rewards=rewards, done=self._done, winner=self._winner)

    def forceFinish(self, winner: str | None = None) -> None:
        """현재 에피소드를 강제로 종료 상태로 전환합니다."""
        self._done = True
        if winner is not None:
            self._winner = winner

    def _consumeBattleEvents(self) -> None:
        if self._done:
            return

        events = BattleEventBus.getInstance().consumeAll()
        for event in events:
            eventType = event.get("type")
            if eventType == "hit":
                self._applyHitReward(event.get("source"), event.get("target"))
                continue

            if eventType == "dodge":
                self._applyDefenseReward(event.get("source"), event.get("target"), self.DODGE_REWARD)
                continue

            if eventType == "cover_block":
                self._applyDefenseReward(event.get("source"), event.get("target"), self.COVER_BLOCK_REWARD)
                continue

            if eventType == "item_pickup":
                self._applyItemPickupReward(
                    event.get("target"),
                    bool(event.get("healed_hp", False)),
                )
                continue

            if eventType == "death":
                self._applyDeathReward(event.get("target"))

    def _applyHitReward(self, source: str | None, target: str | None) -> None:
        if source in self._rewards:
            self._rewards[source] += self.HIT_REWARD
        if target in self._rewards:
            self._rewards[target] -= self.HIT_REWARD

    def _applyDeathReward(self, target: str | None) -> None:
        if target not in self._rewards:
            return

        self._rewards[target] -= self.DEATH_PENALTY
        winner = self._opponentTag(target)
        if winner in self._rewards:
            self._rewards[winner] += self.KILL_REWARD
            self._winner = winner
        self._done = True

    def _applyDefenseReward(self, source: str | None, target: str | None, rewardValue: float) -> None:
        if target in self._rewards:
            self._rewards[target] += rewardValue
        if source in self._rewards:
            self._rewards[source] -= rewardValue

    def _applyItemPickupReward(self, target: str | None, healedHp: bool) -> None:
        if target in self._rewards:
            rewardValue = self.ITEM_PICKUP_REWARD if healedHp else self.ITEM_PICKUP_BUFF_ONLY_REWARD
            self._rewards[target] += rewardValue

    def _opponentTag(self, tag: str):
        if tag == self._tagA:
            return self._tagB
        if tag == self._tagB:
            return self._tagA
        return None
