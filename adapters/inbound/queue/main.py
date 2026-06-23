import asyncio
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from infrastructure.container import Container
from infrastructure.logging import setup_logging


async def _serve() -> None:
    load_dotenv()
    setup_logging()

    container = Container()
    worker = container.bullmq_exercise_worker()
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    await worker.start()

    try:
        await stop_event.wait()
    finally:
        await worker.close()


def main() -> None:
    asyncio.run(_serve())


if __name__ == "__main__":
    main()