import time
import pytest
from backend.app.services.background_jobs import (
    background_job_service,
    run_batch_evaluation_task,
    run_analytics_aggregation_task,
    run_document_indexing_task
)


def test_submit_and_execute_background_job():
    """Verify background job queuing, async execution, status tracking, and result retrieval."""
    job_id = background_job_service.submit_job(
        job_type="batch_evaluations",
        target_fn=run_batch_evaluation_task,
        params={"sample_size": 25}
    )
    assert job_id.startswith("job-")

    # Initial status should be QUEUED or RUNNING
    job = background_job_service.get_job(job_id)
    assert job is not None
    assert job["status"] in ["QUEUED", "RUNNING", "COMPLETED"]

    # Wait briefly for completion
    for _ in range(20):
        time.sleep(0.1)
        job = background_job_service.get_job(job_id)
        if job["status"] == "COMPLETED":
            break

    assert job["status"] == "COMPLETED"
    assert job["progress"] == 1.0
    assert job["result"]["samples_evaluated"] == 25
    assert job["result"]["pass_rate"] > 0.90


def test_list_background_jobs():
    """Verify listing of background jobs."""
    jobs = background_job_service.list_jobs(limit=10)
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
