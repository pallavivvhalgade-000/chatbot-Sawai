from fastapi import (
    APIRouter,
    HTTPException,
)

from app.db.database import (
    get_connection,
)


router = APIRouter(
    tags=["health"]
)


@router.get(
    "/health",
    include_in_schema=False,
)
def health_check():

    connection = None

    try:
        connection = (
            get_connection()
        )

        connection.execute(
            "SELECT 1"
        ).fetchone()

    except Exception as exc:

        raise HTTPException(
            status_code=503,
            detail=(
                "Service unavailable."
            ),
        ) from exc

    finally:
        if connection is not None:
            connection.close()


    return {
        "status": "ok"
    }