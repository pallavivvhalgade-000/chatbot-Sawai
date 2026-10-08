import csv
from datetime import datetime
from pathlib import Path

from app.db.database import (
    get_connection,
)


def main() -> None:

    export_dir = Path(
        "data/exports"
    )

    export_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )


    output_path = (
        export_dir
        / f"leads_{timestamp}.csv"
    )


    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                lead_id,
                name,
                mobile,
                email,
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
                notes,
                created_at
            FROM leads
            ORDER BY created_at DESC
            """
        ).fetchall()

    finally:
        connection.close()


    fieldnames = [
        "lead_id",
        "name",
        "mobile",
        "email",
        "service",
        "sub_service",
        "requirement",
        "budget",
        "timeline",
        "location",
        "priority",
        "status",
        "assigned_to",
        "contact_preference",
        "source",
        "notes",
        "created_at",
    ]


    with output_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:

            writer.writerow(
                {
                    field:
                        row[field]
                    for field
                    in fieldnames
                }
            )


    print(
        f"Exported {len(rows)} lead(s)"
    )

    print(
        output_path.resolve()
    )


if __name__ == "__main__":
    main()