import logging
from pathlib import Path

from app.core.logging import DailyLogFileHandler


def test_rotated_log_filename_still_ends_with_log(tmp_path: Path) -> None:
    handler = DailyLogFileHandler(tmp_path / "app.log", when="midnight", backupCount=7)
    try:
        rotated = handler.rotation_filename(str(tmp_path / "app.log.2026-06-21"))
    finally:
        handler.close()

    assert rotated.endswith("app.2026-06-21.log")


def test_rollover_creates_log_suffixed_archive(tmp_path: Path) -> None:
    handler = DailyLogFileHandler(tmp_path / "app.log", when="midnight", backupCount=7)
    handler.setFormatter(logging.Formatter("%(message)s"))
    try:
        handler.emit(logging.LogRecord("test", logging.INFO, __file__, 1, "before", (), None))
        handler.doRollover()
        handler.emit(logging.LogRecord("test", logging.INFO, __file__, 1, "after", (), None))
    finally:
        handler.close()

    archives = [path for path in tmp_path.iterdir() if path.name != "app.log"]
    assert len(archives) == 1
    assert archives[0].suffix == ".log"
    assert archives[0].name.startswith("app.")
