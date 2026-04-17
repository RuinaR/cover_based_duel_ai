from collections import deque

import pygame

from ai.policy_setup import loadTrainingSetup
from ai.environment.battle_env import BattleEnv
from engine.game_logger import get_logger


def runTrainMode(episodes: int = 250, maxStepsPerEpisode: int = 2000) -> None:
    logger = get_logger("game.main")
    logger.info("Game start (train mode): episodes=%s max_steps=%s", episodes, maxStepsPerEpisode)

    pygame.init()
    setup = loadTrainingSetup()
    logger.info("%s checkpoint loaded A=%s path=%s", setup.specA.kind, setup.loadedA, setup.specA.checkpointPath)
    logger.info("%s checkpoint loaded B=%s path=%s", setup.specB.kind, setup.loadedB, setup.specB.checkpointPath)

    env = BattleEnv(
        policyA=setup.policyA,
        policyB=setup.policyB,
        autoLearn=True,
        checkpointPathA=setup.specA.checkpointPath,
        checkpointPathB=setup.specB.checkpointPath,
        saveOnEpisodeEnd=False,
    )
    recentRewardA = deque(maxlen=20)
    recentRewardB = deque(maxlen=20)
    recentWinners = deque(maxlen=20)
    try:
        for episode in range(episodes):
            env.reset()
            done = False
            totalRewardA = 0.0
            totalRewardB = 0.0
            stepCount = 0
            info = {"winner": None, "episode_summary": None, "call_stack": ()}

            while not done and stepCount < maxStepsPerEpisode:
                _, rewards, done, info = env.step()
                totalRewardA += rewards.get("ai_a", 0.0)
                totalRewardB += rewards.get("ai_b", 0.0)
                stepCount += 1

            if not done:
                info["episode_summary"] = env.closeEpisode()
                logger.info("[%s/%s] force-closed after max steps", episode + 1, episodes)

            recentRewardA.append(totalRewardA)
            recentRewardB.append(totalRewardB)
            recentWinners.append(info.get("winner"))
            avgRewardA = sum(recentRewardA) / len(recentRewardA)
            avgRewardB = sum(recentRewardB) / len(recentRewardB)
            winRateA = _computeRecentWinRate(recentWinners, "ai_a")
            winRateB = _computeRecentWinRate(recentWinners, "ai_b")
            drawRate = _computeRecentDrawRate(recentWinners)
            progressLine = (
                f"[{episode + 1}/{episodes}] steps={stepCount} "
                f"reward_a={totalRewardA:.3f} reward_b={totalRewardB:.3f} "
                f"avg20_reward_a={avgRewardA:.3f} avg20_reward_b={avgRewardB:.3f} "
                f"avg20_win_a={winRateA:.1f}% avg20_win_b={winRateB:.1f}% avg20_draw={drawRate:.1f}% "
                f"winner={info.get('winner')} summary={info.get('episode_summary')}"
            )

            logger.info(
                "[%s/%s] steps=%s reward_a=%.3f reward_b=%.3f "
                "avg20_reward_a=%.3f avg20_reward_b=%.3f "
                "avg20_win_a=%.1f%% avg20_win_b=%.1f%% avg20_draw=%.1f%% "
                "winner=%s summary=%s",
                episode + 1,
                episodes,
                stepCount,
                totalRewardA,
                totalRewardB,
                avgRewardA,
                avgRewardB,
                winRateA,
                winRateB,
                drawRate,
                info.get("winner"),
                info.get("episode_summary"),
            )
            print(progressLine, flush=True)
    finally:
        logger.info("Saving checkpoints at train shutdown")
        env.saveCheckpoints()
        pygame.quit()


def _computeRecentWinRate(winners: deque, tag: str) -> float:
    if not winners:
        return 0.0
    winCount = sum(1 for winner in winners if winner == tag)
    return (winCount / len(winners)) * 100.0


def _computeRecentDrawRate(winners: deque) -> float:
    if not winners:
        return 0.0
    drawCount = sum(1 for winner in winners if winner is None)
    return (drawCount / len(winners)) * 100.0
