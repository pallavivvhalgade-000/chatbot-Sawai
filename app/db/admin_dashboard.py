from __future__ import annotations

from typing import Any

from app.db.database import (
    get_connection,
)


def _scalar(
    connection,
    sql: str,
    parameters: tuple = (),
) -> int:

    row = connection.execute(
        sql,
        parameters,
    ).fetchone()

    if row is None:
        return 0

    return int(
        row[0] or 0
    )


def get_overview_metrics() -> dict[str, int]:

    connection = get_connection()

    try:
        total = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            """,
        )

        today = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE date(created_at)
                = date('now')
            """,
        )

        real_estate = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE service = 'real_estate'
            """,
        )

        insurance = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE service = 'insurance'
            """,
        )

        it_services = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE service = 'it_services'
            """,
        )

        hot = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE lower(priority) = 'hot'
            """,
        )

        converted = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE status = 'converted'
            """,
        )

        follow_up = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE status = 'follow_up'
            """,
        )

        pending = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE status NOT IN (
                'converted',
                'closed',
                'closed_lost'
            )
            """,
        )

        failed_deliveries = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM lead_delivery_jobs
            WHERE status = 'failed'
            """,
        )

        unassigned = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE assigned_to IS NULL
               OR trim(assigned_to) = ''
            """,
        )

    finally:
        connection.close()


    return {
        "total_leads": total,
        "today_leads": today,
        "real_estate_leads": real_estate,
        "insurance_leads": insurance,
        "it_leads": it_services,
        "hot_leads": hot,
        "pending_leads": pending,
        "converted_leads": converted,
        "follow_up_leads": follow_up,
        "failed_deliveries": failed_deliveries,
        "unassigned_leads": unassigned,
    }


def get_analytics_metrics() -> dict[str, Any]:

    connection = get_connection()

    try:
        chatbot_opens = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM analytics_events
            WHERE event_type = 'chatbot_open'
            """,
        )

        expert_requests = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM analytics_events
            WHERE event_type = 'expert_request'
            """,
        )

        call_requests = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM analytics_events
            WHERE event_type = 'call_request'
            """,
        )

        whatsapp_requests = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM analytics_events
            WHERE event_type = 'whatsapp_request'
            """,
        )

        conversations_started = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM conversation_sessions
            """,
        )

        completed = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            """,
        )

        real_estate = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE service = 'real_estate'
            """,
        )

        insurance = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE service = 'insurance'
            """,
        )

        it_services = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM leads
            WHERE service = 'it_services'
            """,
        )

    finally:
        connection.close()


    if conversations_started > 0:
        incomplete = max(
            conversations_started
            - completed,
            0,
        )

        drop_off_rate = round(
            (
                incomplete
                / conversations_started
            )
            * 100,
            1,
        )

    else:
        drop_off_rate = 0.0


    return {
        "chatbot_opens":
            chatbot_opens,

        "conversations_started":
            conversations_started,

        "completed_leads":
            completed,

        "drop_off_rate":
            drop_off_rate,

        "expert_requests":
            expert_requests,

        "call_requests":
            call_requests,

        "whatsapp_requests":
            whatsapp_requests,

        "real_estate_enquiries":
            real_estate,

        "insurance_enquiries":
            insurance,

        "it_enquiries":
            it_services,
    }


def get_delivery_jobs(
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:

    connection = get_connection()

    try:

        if status:
            rows = connection.execute(
                """
                SELECT
                    id,
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
                FROM lead_delivery_jobs
                WHERE status = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (
                    status,
                    limit,
                ),
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT
                    id,
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
                FROM lead_delivery_jobs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (
                    limit,
                ),
            ).fetchall()

    finally:
        connection.close()


    return [
        dict(row)
        for row in rows
    ]