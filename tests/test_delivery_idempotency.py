import sqlite3

from app.db import (
    lead_operations,
)


def _connection_factory(
    database_path,
):
    def factory():

        connection = (
            sqlite3.connect(
                database_path
            )
        )

        connection.row_factory = (
            sqlite3.Row
        )

        return connection

    return factory


def test_delivery_job_is_not_duplicated(
    tmp_path,
    monkeypatch,
):

    database_path = (
        tmp_path
        / "delivery_test.db"
    )


    connection = sqlite3.connect(
        database_path
    )

    try:
        connection.execute(
            """
            CREATE TABLE
            lead_delivery_jobs (
                id INTEGER
                    PRIMARY KEY AUTOINCREMENT,

                lead_id TEXT NOT NULL,

                channel TEXT NOT NULL,

                event_type TEXT NOT NULL,

                status TEXT NOT NULL,

                attempt_count INTEGER
                    NOT NULL DEFAULT 0,

                max_attempts INTEGER
                    NOT NULL DEFAULT 3,

                next_attempt_at TEXT,

                last_error TEXT,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL,

                UNIQUE(
                    lead_id,
                    channel,
                    event_type
                )
            )
            """
        )

        connection.commit()

    finally:
        connection.close()


    monkeypatch.setattr(
        lead_operations,
        "get_connection",
        _connection_factory(
            database_path
        ),
    )


    first_job = (
        lead_operations
        .enqueue_lead_delivery(
            lead_id="SA-TEST-001",
            channel="test",
            event_type=(
                "lead_created"
            ),
        )
    )


    second_job = (
        lead_operations
        .enqueue_lead_delivery(
            lead_id="SA-TEST-001",
            channel="test",
            event_type=(
                "lead_created"
            ),
        )
    )


    assert first_job is not None

    assert second_job is None


    connection = sqlite3.connect(
        database_path
    )

    try:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM lead_delivery_jobs
            """
        ).fetchone()[0]

    finally:
        connection.close()


    assert count == 1