"""Dedicated Railway launch worker. Run as `python -m app.worker`."""
import logging
import os
import time

from app.services.launch_service import run_worker_once

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)


def main():
    poll_seconds = max(1, int(os.getenv("LAUNCH_WORKER_POLL_SECONDS", "2")))
    while True:
        try:
            if not run_worker_once():
                time.sleep(poll_seconds)
        except Exception:
            logger.exception("launch worker iteration failed")
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
