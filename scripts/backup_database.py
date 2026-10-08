from __future__ import annotations

import sqlite3

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path

from app.core.config import (
    settings,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


def resolve_database_path() -> Path:

    path = Path(
        settings.database_path
    )

    if not path.is_absolute():
        path = (
            PROJECT_ROOT
            / path
        )

    return path.resolve()


def backup_database() -> Path:

    source_path = (
        resolve_database_path()
    )


    if not source_path.exists():
        raise FileNotFoundError(
            "SQLite database was not found: "
            f"{source_path}"
        )


    backup_directory = (
        PROJECT_ROOT
        / "data"
        / "backups"
    )

    backup_directory.mkdir(
        parents=True,
        exist_ok=True,
    )


    timestamp = (
        datetime.now(
            timezone.utc
        )
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )


    destination_path = (
        backup_directory
        / (
            "sawai_"
            f"{timestamp}.db"
        )
    )


    source = sqlite3.connect(
        source_path
    )

    destination = (
        sqlite3.connect(
            destination_path
        )
    )


    try:
        source.backup(
            destination
        )

    finally:
        destination.close()
        source.close()


    return destination_path


if __name__ == "__main__":

    result = backup_database()

    print(
        "Database backup created:"
    )

    print(
        result
    )