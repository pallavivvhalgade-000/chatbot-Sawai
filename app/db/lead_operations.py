from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Any

from app.db.database import (
    get_connection,
)


# =========================================================
# Time
# =========================================================


def _utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


# =========================================================
# Lead status rules
# =========================================================


VALID_STATUS_TRANSITIONS: dict[
    str,
    set[str],
] = {
    "new": {
        "contacted",
        "qualified",
        "closed",
        "closed_lost",
    },

    "contacted": {
        "qualified",
        "follow_up",
        "closed",
        "closed_lost",
    },

    "qualified": {
        "in_progress",
        "proposal_shared",
        "follow_up",
        "converted",
        "closed",
        "closed_lost",
    },

    "in_progress": {
        "proposal_shared",
        "follow_up",
        "converted",
        "closed",
        "closed_lost",
    },

    "proposal_shared": {
        "follow_up",
        "converted",
        "closed",
        "closed_lost",
    },

    "follow_up": {
        "contacted",
        "qualified",
        "proposal_shared",
        "converted",
        "closed",
        "closed_lost",
    },

    "converted": set(),

    "closed": set(),

    "closed_lost": set(),
}


# =========================================================
# Helpers
# =========================================================


def get_lead_record(
    lead_id: str,
) -> dict[str, Any] | None:

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT *
            FROM leads
            WHERE lead_id = ?
            """,
            (
                lead_id,
            ),
        ).fetchone()

    finally:
        connection.close()


    if row is None:
        return None


    return dict(row)


# =========================================================
# Audit events
# =========================================================


def record_lead_event(
    lead_id: str,
    event_type: str,
    *,
    old_value: str | None = None,
    new_value: str | None = None,
    actor: str = "system",
    notes: str | None = None,
) -> int:

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO lead_events (
                lead_id,
                event_type,
                old_value,
                new_value,
                actor,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lead_id,
                event_type,
                old_value,
                new_value,
                actor,
                notes,
                _utc_now_iso(),
            ),
        )

        connection.commit()

        return int(
            cursor.lastrowid
        )

    finally:
        connection.close()


def get_lead_events(
    lead_id: str,
) -> list[dict[str, Any]]:

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM lead_events
            WHERE lead_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (
                lead_id,
            ),
        ).fetchall()

    finally:
        connection.close()


    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# Status management
# =========================================================


def update_lead_status(
    lead_id: str,
    new_status: str,
    *,
    actor: str = "system",
    notes: str | None = None,
) -> dict[str, Any]:

    new_status = (
        new_status
        .strip()
        .lower()
    )


    lead = get_lead_record(
        lead_id
    )


    if lead is None:
        raise ValueError(
            f"Lead not found: {lead_id}"
        )


    old_status = str(
        lead["status"]
    ).lower()


    if old_status == new_status:
        return lead


    allowed = (
        VALID_STATUS_TRANSITIONS
        .get(
            old_status,
            set(),
        )
    )


    if new_status not in allowed:
        raise ValueError(
            f"Invalid lead status transition: "
            f"{old_status} -> {new_status}"
        )


    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE leads
            SET status = ?
            WHERE lead_id = ?
            """,
            (
                new_status,
                lead_id,
            ),
        )

        connection.commit()

    finally:
        connection.close()


    record_lead_event(
        lead_id=lead_id,
        event_type="status_changed",
        old_value=old_status,
        new_value=new_status,
        actor=actor,
        notes=notes,
    )


    updated = get_lead_record(
        lead_id
    )


    if updated is None:
        raise RuntimeError(
            "Lead disappeared after status update."
        )


    return updated


# =========================================================
# Assignment
# =========================================================


def reassign_lead(
    lead_id: str,
    assigned_to: str,
    *,
    actor: str = "system",
    notes: str | None = None,
) -> dict[str, Any]:

    clean_assignment = (
        assigned_to.strip()
    )


    if not clean_assignment:
        raise ValueError(
            "assigned_to cannot be empty."
        )


    lead = get_lead_record(
        lead_id
    )


    if lead is None:
        raise ValueError(
            f"Lead not found: {lead_id}"
        )


    old_assignment = (
        lead.get("assigned_to")
    )


    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE leads
            SET assigned_to = ?
            WHERE lead_id = ?
            """,
            (
                clean_assignment,
                lead_id,
            ),
        )

        connection.commit()

    finally:
        connection.close()


    record_lead_event(
        lead_id=lead_id,
        event_type="assignment_changed",
        old_value=(
            str(old_assignment)
            if old_assignment
            else None
        ),
        new_value=clean_assignment,
        actor=actor,
        notes=notes,
    )


    updated = get_lead_record(
        lead_id
    )


    if updated is None:
        raise RuntimeError(
            "Lead disappeared after reassignment."
        )


    return updated


# =========================================================
# Delivery jobs
# =========================================================


def enqueue_lead_delivery(
    lead_id: str,
    channel: str,
    *,
    event_type: str = "lead_created",
    max_attempts: int = 3,
) -> int | None:
    """
    Create one delivery job.

    UNIQUE(lead_id, channel, event_type) prevents the same
    lead-created notification from being queued repeatedly.
    """

    clean_channel = (
        channel.strip().lower()
    )


    if not clean_channel:
        return None


    if clean_channel == "none":
        return None


    now = _utc_now_iso()

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO lead_delivery_jobs (
                lead_id,
                channel,
                event_type,
                status,
                attempt_count,
                max_attempts,
                next_attempt_at,
                last_error,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lead_id,
                clean_channel,
                event_type,
                "pending",
                0,
                max_attempts,
                now,
                None,
                now,
                now,
            ),
        )

        connection.commit()


        if cursor.rowcount == 0:
            return None


        return int(
            cursor.lastrowid
        )

    finally:
        connection.close()


def get_due_delivery_jobs(
    limit: int = 20,
) -> list[dict[str, Any]]:

    now = _utc_now_iso()

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM lead_delivery_jobs
            WHERE status IN (
                'pending',
                'retry'
            )
            AND (
                next_attempt_at IS NULL
                OR next_attempt_at <= ?
            )
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (
                now,
                limit,
            ),
        ).fetchall()

    finally:
        connection.close()


    return [
        dict(row)
        for row in rows
    ]


def claim_delivery_job(
    job_id: int,
) -> bool:
    """
    Atomically claim a pending/retry job.
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE lead_delivery_jobs
            SET
                status = 'processing',
                updated_at = ?
            WHERE id = ?
            AND status IN (
                'pending',
                'retry'
            )
            """,
            (
                _utc_now_iso(),
                job_id,
            ),
        )

        connection.commit()

        return cursor.rowcount == 1

    finally:
        connection.close()


def mark_delivery_success(
    job_id: int,
) -> None:

    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE lead_delivery_jobs
            SET
                status = 'sent',
                attempt_count =
                    attempt_count + 1,
                last_error = NULL,
                next_attempt_at = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (
                _utc_now_iso(),
                job_id,
            ),
        )

        connection.commit()

    finally:
        connection.close()


def mark_delivery_failure(
    job_id: int,
    error: str,
) -> None:
    """
    Retry temporary failures using a simple exponential
    backoff:

        attempt 1 -> 1 minute
        attempt 2 -> 5 minutes
        attempt 3 -> failed permanently
    """

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                attempt_count,
                max_attempts
            FROM lead_delivery_jobs
            WHERE id = ?
            """,
            (
                job_id,
            ),
        ).fetchone()


        if row is None:
            return


        new_attempt_count = (
            int(
                row["attempt_count"]
            )
            + 1
        )

        max_attempts = int(
            row["max_attempts"]
        )


        if new_attempt_count >= max_attempts:

            status = "failed"

            next_attempt_at = None

        else:

            status = "retry"

            delay_seconds = (
                60
                if new_attempt_count == 1
                else 300
            )

            next_attempt_at = (
                _utc_now()
                + timedelta(
                    seconds=delay_seconds
                )
            ).isoformat()


        connection.execute(
            """
            UPDATE lead_delivery_jobs
            SET
                status = ?,
                attempt_count = ?,
                next_attempt_at = ?,
                last_error = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                new_attempt_count,
                next_attempt_at,
                error[:2000],
                _utc_now_iso(),
                job_id,
            ),
        )

        connection.commit()

    finally:
        connection.close()