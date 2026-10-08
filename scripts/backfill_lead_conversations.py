from app.db.database import (
    get_connection,
)

from app.db.lead_conversations import (
    link_lead_to_session,
)

from app.domain.state import (
    ConversationState,
)


def main() -> None:

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                session_id,
                state_json
            FROM conversation_sessions
            """
        ).fetchall()

    finally:
        connection.close()


    linked = 0
    skipped = 0


    for row in rows:

        try:
            state = (
                ConversationState
                .model_validate_json(
                    row["state_json"]
                )
            )

        except Exception:
            skipped += 1
            continue


        if state.lead is None:
            continue


        lead_id = (
            state.lead.lead_id
        )


        if not lead_id:
            continue


        link_lead_to_session(
            lead_id=lead_id,
            session_id=row[
                "session_id"
            ],
        )

        linked += 1


    print(
        f"Linked conversations: {linked}"
    )

    print(
        f"Skipped unreadable sessions: "
        f"{skipped}"
    )


if __name__ == "__main__":
    main()