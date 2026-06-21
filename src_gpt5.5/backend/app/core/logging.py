import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any


class DailyLogFileHandler(TimedRotatingFileHandler):
    """Rotate at midnight and keep rotated filenames ending in .log."""

    def rotation_filename(self, default_name: str) -> str:
        path = Path(default_name)
        marker = ".log."
        if marker not in path.name:
            return default_name
        stem, date_suffix = path.name.rsplit(marker, maxsplit=1)
        return str(path.with_name(f"{stem}.{date_suffix}.log"))

    def getFilesToDelete(self) -> list[str]:  # noqa: N802 - stdlib API name
        if self.backupCount <= 0:
            return []
        base = Path(self.baseFilename)
        stem = base.name.removesuffix(".log")
        rotated = sorted(base.parent.glob(f"{stem}.*.log"))
        return [str(path) for path in rotated[: max(0, len(rotated) - self.backupCount)]]


def build_log_config(log_dir: Path, level: str, retention_days: int) -> dict[str, Any]:
    log_dir.mkdir(parents=True, exist_ok=True)
    normalized_level = level.upper()
    handler_options = {
        "class": "app.core.logging.DailyLogFileHandler",
        "when": "midnight",
        "interval": 1,
        "backupCount": retention_days,
        "encoding": "utf-8",
        "delay": True,
    }
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
                "use_colors": False,
            },
        },
        "handlers": {
            "app_file": {
                **handler_options,
                "filename": str(log_dir / "app.log"),
                "formatter": "default",
            },
            "access_file": {
                **handler_options,
                "filename": str(log_dir / "access.log"),
                "formatter": "access",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["app_file"],
                "level": normalized_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["app_file"],
                "level": normalized_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access_file"],
                "level": normalized_level,
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["app_file"],
            "level": normalized_level,
        },
    }


def configure_logging(level: str = "INFO") -> None:
    logging.getLogger().setLevel(getattr(logging, level.upper(), logging.INFO))
