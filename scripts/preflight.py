from __future__ import annotations

import sqlite3
import sys

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


errors: list[str] = []

warnings: list[str] = []


def check(
    condition: bool,
    message: str,
) -> None:

    if condition:
        print(
            f"[OK] {message}"
        )

    else:
        print(
            f"[ERROR] {message}"
        )

        errors.append(
            message
        )


def warn(
    condition: bool,
    message: str,
) -> None:

    if not condition:
        print(
            f"[WARNING] {message}"
        )

        warnings.append(
            message
        )


# =========================================================
# Core settings
# =========================================================


check(
    bool(
        settings.groq_api_key
    ),
    "Groq API key configured.",
)


check(
    bool(
        settings.llm_model
    ),
    "LLM model configured.",
)


if (
    settings.admin_api_enabled
):
    check(
        bool(
            settings.admin_api_token
        ),
        (
            "Admin API token "
            "configured."
        ),
    )


# =========================================================
# Production settings
# =========================================================


if (
    str(
        settings.app_env
    ).lower()
    == "production"
):
    check(
        settings.debug is False,
        (
            "DEBUG is disabled "
            "in production."
        ),
    )


# =========================================================
# Admin frontend
# =========================================================


admin_directory = (
    PROJECT_ROOT
    / "admin"
)


check(
    (
        admin_directory
        / "index.html"
    ).exists(),
    "Admin index.html exists.",
)


check(
    (
        admin_directory
        / "admin.js"
    ).exists(),
    "Admin JavaScript exists.",
)


check(
    (
        admin_directory
        / "admin.css"
    ).exists(),
    "Admin stylesheet exists.",
)


# =========================================================
# Database
# =========================================================


database_path = Path(
    settings.database_path
)


if not database_path.is_absolute():
    database_path = (
        PROJECT_ROOT
        / database_path
    )


check(
    database_path.exists(),
    "SQLite database exists.",
)


required_tables = {
    "conversation_sessions",
    "leads",
    "lead_events",
    "lead_delivery_jobs",
    "analytics_events",
}


if database_path.exists():

    connection = (
        sqlite3.connect(
            database_path
        )
    )

    try:

        integrity = (
            connection.execute(
                """
                PRAGMA integrity_check
                """
            )
            .fetchone()[0]
        )


        check(
            integrity == "ok",
            (
                "SQLite integrity "
                "check passed."
            ),
        )


        rows = (
            connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
            .fetchall()
        )


        existing_tables = {
            row[0]
            for row in rows
        }


        missing_tables = (
            required_tables
            - existing_tables
        )


        check(
            not missing_tables,
            (
                "Required database "
                "tables exist."
                if not missing_tables
                else (
                    "Missing tables: "
                    + ", ".join(
                        sorted(
                            missing_tables
                        )
                    )
                )
            ),
        )

    finally:
        connection.close()


# =========================================================
# Delivery configuration
# =========================================================


warn(
    (
        settings.notification_channel
        != "none"
    ),
    (
        "Notification channel is "
        "'none'; delivery jobs will "
        "not notify a real team."
    ),
)


# =========================================================
# Final result
# =========================================================


print()

print(
    "Preflight summary:"
)

print(
    f"Errors: {len(errors)}"
)

print(
    f"Warnings: {len(warnings)}"
)


if errors:

    print()

    print(
        "PRE-FLIGHT FAILED"
    )

    sys.exit(1)


print()

print(
    "PRE-FLIGHT PASSED"
)