from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from pydantic import (
    BaseModel,
    Field,
)

from app.db.database import (
    get_connection,
)

from app.db.lead_operations import (
    get_lead_events,
    get_lead_record,
    reassign_lead,
    update_lead_status,
)

from app.security.admin_auth import (
    require_admin,
)

from app.db.admin_dashboard import (
    get_analytics_metrics,
    get_delivery_jobs,
    get_overview_metrics,
)

from app.db.lead_conversations import (
    get_session_id_for_lead,
)

from app.graph.session_store import (
    get_session,
)


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[
        Depends(
            require_admin
        )
    ],
)


# =========================================================
# Request schemas
# =========================================================


class StatusUpdateRequest(
    BaseModel
):
    status: str = Field(
        min_length=1,
        max_length=50,
    )

    notes: str | None = Field(
        default=None,
        max_length=1000,
    )


class AssignmentUpdateRequest(
    BaseModel
):
    assigned_to: str = Field(
        min_length=1,
        max_length=200,
    )

    notes: str | None = Field(
        default=None,
        max_length=1000,
    )


# =========================================================
# Lead list
# =========================================================


@router.get(
    "/leads"
)
def list_leads(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),

    status: str | None = None,
    service: str | None = None,
    priority: str | None = None,
    location: str | None = None,
    assigned_to: str | None = None,
    source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:

    where: list[str] = []

    values: list[Any] = []


    if status:
        where.append(
            "lower(status) = ?"
        )

        values.append(
            status.strip().lower()
        )


    if service:
        where.append(
            "lower(service) = ?"
        )

        values.append(
            service.strip().lower()
        )


    if priority:
        where.append(
            "lower(priority) = ?"
        )

        values.append(
            priority.strip().lower()
        )


    if location:
        where.append(
            "lower(location) LIKE ?"
        )

        values.append(
            "%"
            + location.strip().lower()
            + "%"
        )


    if assigned_to:
        where.append(
            "lower(assigned_to) LIKE ?"
        )

        values.append(
            "%"
            + assigned_to.strip().lower()
            + "%"
        )


    if source:
        where.append(
            "lower(source) LIKE ?"
        )

        values.append(
            "%"
            + source.strip().lower()
            + "%"
        )


    if date_from:
        where.append(
            "date(created_at) >= date(?)"
        )

        values.append(
            date_from
        )


    if date_to:
        where.append(
            "date(created_at) <= date(?)"
        )

        values.append(
            date_to
        )


    sql = """
        SELECT
            lead_id,
            name,
            service,
            sub_service,
            requirement,
            budget,
            timeline,
            location,
            priority,
            status,
            assigned_to,
            contact_preference,
            source,
            created_at
        FROM leads
    """


    if where:
        sql += (
            " WHERE "
            + " AND ".join(
                where
            )
        )


    sql += """
        ORDER BY created_at DESC
        LIMIT ?
    """


    values.append(
        limit
    )


    connection = get_connection()

    try:
        rows = connection.execute(
            sql,
            tuple(values),
        ).fetchall()

    finally:
        connection.close()


    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# Lead detail
# =========================================================


@router.get(
    "/leads/{lead_id}"
)
def get_lead(
    lead_id: str,
) -> dict[str, Any]:

    lead = get_lead_record(
        lead_id
    )


    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found.",
        )


    return lead


# =========================================================
# Lead audit history
# =========================================================


@router.get(
    "/leads/{lead_id}/events"
)
def get_events(
    lead_id: str,
) -> list[dict[str, Any]]:

    lead = get_lead_record(
        lead_id
    )


    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found.",
        )


    return get_lead_events(
        lead_id
    )


# =========================================================
# Status update
# =========================================================


@router.patch(
    "/leads/{lead_id}/status"
)
def change_status(
    lead_id: str,
    payload: StatusUpdateRequest,
) -> dict[str, Any]:

    try:
        return update_lead_status(
            lead_id=lead_id,
            new_status=(
                payload.status
            ),
            actor="admin_api",
            notes=payload.notes,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# =========================================================
# Assignment update
# =========================================================


@router.patch(
    "/leads/{lead_id}/assignment"
)
def change_assignment(
    lead_id: str,
    payload: AssignmentUpdateRequest,
) -> dict[str, Any]:

    try:
        return reassign_lead(
            lead_id=lead_id,
            assigned_to=(
                payload.assigned_to
            ),
            actor="admin_api",
            notes=payload.notes,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@router.get(
    "/overview"
)
def dashboard_overview():
    return get_overview_metrics()


@router.get(
    "/analytics"
)
def dashboard_analytics():
    return get_analytics_metrics()


@router.get(
    "/delivery-jobs"
)
def delivery_jobs(
    status: str | None = None,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
):
    return get_delivery_jobs(
        status=status,
        limit=limit,
    )


@router.get(
    "/leads/{lead_id}/conversation"
)
def get_lead_conversation(
    lead_id: str,
) -> dict[str, Any]:
    """
    Return the stored chatbot transcript for a lead.

    This endpoint is protected by the existing admin
    router authentication.
    """

    session_id = (
        get_session_id_for_lead(
            lead_id
        )
    )


    if not session_id:
        return {
            "lead_id": lead_id,
            "session_id": None,
            "channel": None,
            "message_count": 0,
            "messages": [],
        }


    state = get_session(
        session_id
    )


    if state is None:
        return {
            "lead_id": lead_id,
            "session_id": session_id,
            "channel": None,
            "message_count": 0,
            "messages": [],
        }


    messages: list[
        dict[str, Any]
    ] = []


    for index, item in enumerate(
        state.history,
        start=1,
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue


        role = str(
            item.get(
                "role",
                "",
            )
        ).strip().lower()


        content = str(
            item.get(
                "content",
                "",
            )
        ).strip()


        if (
            role
            not in {
                "user",
                "assistant",
            }
        ):
            continue


        if not content:
            continue


        messages.append(
            {
                "index": index,
                "role": role,
                "content": content,
            }
        )


    return {
        "lead_id": lead_id,
        "session_id": session_id,
        "channel": getattr(
            state,
            "channel",
            "web",
        ),
        "message_count": len(
            messages
        ),
        "messages": messages,
    }