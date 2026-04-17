#.\visual
#.\train

from app.train_runner import runTrainMode
from app.visual_runner import runVisualMode
from engine.game_logger import get_logger, shutdown_logging


def main() -> None:
    import sys

    mode = "visual"
    if len(sys.argv) >= 2:
        mode = sys.argv[1].strip().lower()

    if mode == "train":
        runTrainMode()
        return

    runVisualMode()


if __name__ == "__main__":
    logger = get_logger("game.main")
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Game interrupted by keyboard")
        raise
    except Exception:
        logger.exception("Unhandled exception")
        raise
    finally:
        shutdown_logging()
