from __future__ import annotations

import json

from datetime import (
    datetime,
    timezone,
)

from typing import Any

from app.db.database import (
    get_connection,
)


def _utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def record_analytics_event(
    event_type: str,
    *,
    session_id: str | None = None,
    service: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Store non-sensitive chatbot analytics.

    Never store message text, names, mobile numbers,
    email addresses or other customer PII here.
    """

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO analytics_events (
                event_type,
                session_id,
                service,
                metadata_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_type,
                session_id,
                service,
                (
                    json.dumps(
                        metadata
                    )
                    if metadata
                    else None
                ),
                _utc_now_iso(),
            ),
        )

        connection.commit()

    finally:
        connection.close()