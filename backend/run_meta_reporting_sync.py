#!/usr/bin/env python3
"""Railway Cron entrypoint for read-only Meta Insights reporting syncs."""

import logging
import sys

from app.database import SessionLocal
from app.services.meta_reporting_service import MetaReportingService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> int:
    db = SessionLocal()
    try:
        runs = MetaReportingService(db).sync_enabled_accounts()
        failed = [run for run in runs if run.status != "completed"]
        logger.info("Meta reporting sync completed: %s complete, %s incomplete", len(runs) - len(failed), len(failed))
        return 1 if failed else 0
    except Exception:
        logger.exception("Meta reporting sync failed")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
