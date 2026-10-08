from app.db.lead_operations import (
    claim_delivery_job,
    get_due_delivery_jobs,
    get_lead_record,
    mark_delivery_failure,
    mark_delivery_success,
    record_lead_event,
)

from app.domain.models import Lead

from app.services.notifications import (
    notify_lead,
)


def process_jobs() -> None:

    jobs = get_due_delivery_jobs(
        limit=20
    )


    if not jobs:
        print(
            "No delivery jobs are due."
        )

        return


    print(
        f"Found {len(jobs)} delivery job(s)."
    )


    for job in jobs:

        job_id = int(
            job["id"]
        )

        lead_id = str(
            job["lead_id"]
        )


        if not claim_delivery_job(
            job_id
        ):
            continue


        try:
            lead_data = (
                get_lead_record(
                    lead_id
                )
            )


            if lead_data is None:
                raise RuntimeError(
                    f"Lead not found: {lead_id}"
                )


            lead = Lead.model_validate(
                lead_data
            )


            result = notify_lead(
                lead
            )


            # Your existing notification service returns
            # a structured result.
            #
            # Treat an explicit unsuccessful result as a
            # delivery failure.

            if hasattr(
                result,
                "success",
            ):
                if not result.success:
                    raise RuntimeError(
                        getattr(
                            result,
                            "error",
                            None,
                        )
                        or "Notification failed."
                    )


            mark_delivery_success(
                job_id
            )


            record_lead_event(
                lead_id=lead_id,
                event_type="delivery_success",
                new_value=str(
                    job["channel"]
                ),
                actor="delivery-worker",
            )


            print(
                f"SUCCESS: {lead_id}"
            )


        except Exception as exc:

            mark_delivery_failure(
                job_id,
                str(exc),
            )


            record_lead_event(
                lead_id=lead_id,
                event_type="delivery_failure",
                new_value=str(
                    job["channel"]
                ),
                actor="delivery-worker",
                notes=(
                    type(exc).__name__
                    + ": "
                    + str(exc)
                )[:2000],
            )


            print(
                f"FAILED: {lead_id}: {exc}"
            )


if __name__ == "__main__":
    process_jobs()