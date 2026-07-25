"""Focused tests for the durable, PAUSED-only launch worker."""
from unittest.mock import MagicMock

import pytest
import requests

from app.database import SessionLocal
from app.models import LaunchJob, LaunchOperation, User
from app.services.launch_service import MAX_ADS_PER_LAUNCH, MAX_OPERATION_ATTEMPTS, _result, create_job, reconcile_job, request_activation, run_worker_once, validate_launch_payload


def payload(**overrides):
    value = {
        "ad_account_ids": ["act_111", "act_222"], "launch_status": "PAUSED", "source_account_id": "act_111",
        "campaign": {"name": "Test Campaign", "objective": "OUTCOME_TRAFFIC", "budgetType": "ABO"},
        "adset": {"name": "Test AdSet", "optimizationGoal": "LINK_CLICKS", "dailyBudget": 10},
        "page_id": "page_1", "creatives": [{"image_url": "https://example.com/a.jpg", "media_type": "image", "name": "A"}],
        "headlines": ["H1", "H2"], "bodies": ["B1"], "cta": "LEARN_MORE", "website_url": "https://example.com",
    }
    value.update(overrides)
    return value


def fake_service():
    service = MagicMock()
    service.create_campaign.side_effect = lambda data, account: {"id": f"campaign_{account}"}
    service.create_adset.side_effect = lambda data, account: {"id": f"adset_{account}"}
    service.upload_image.side_effect = lambda url, account: f"hash_{account}"
    service.create_creative.side_effect = lambda data, account: {"id": f"creative_{account}_{data['name']}"}
    service.create_ad.side_effect = lambda data, account: {"id": f"ad_{account}_{data['name']}"}
    service.get_object.return_value = {"id": "known", "status": "PAUSED"}
    return service


@pytest.fixture
def owner_id():
    db = SessionLocal()
    user = User(id="test-worker-user", email="launch-worker@example.test", hashed_password="not-used")
    db.add(user); db.commit()
    yield user.id
    db.query(User).filter_by(id=user.id).delete(); db.commit(); db.close()


@pytest.fixture
def job_id(owner_id):
    db = SessionLocal()
    job, _ = create_job(db, payload(), owner_id, "test-worker-key")
    yield job.id
    db = SessionLocal()
    job = db.query(LaunchJob).filter_by(id=job.id).first()
    if job:
        db.delete(job); db.commit()
    db.close()


def drain(service):
    while run_worker_once(lambda: service):
        pass


def test_worker_creates_paused_launch_then_requires_explicit_activation(job_id):
    service = fake_service()
    drain(service)
    db = SessionLocal(); job = db.query(LaunchJob).filter_by(id=job_id).one()
    assert job.status == "ready"
    assert job.completed_steps == 4
    request_activation(db, job, service)
    db.close()
    drain(service)
    db = SessionLocal(); job = db.query(LaunchJob).filter_by(id=job_id).one()
    assert job.status == "active"
    assert service.set_status.call_count == 8  # 4 ads + 2 adsets + 2 campaigns
    db.close()


def test_idempotency_replays_only_the_matching_payload(owner_id):
    db = SessionLocal()
    job, replayed = create_job(db, payload(ad_account_ids=["act_333"]), owner_id, "same-key")
    same, replayed_same = create_job(db, payload(ad_account_ids=["act_333"]), owner_id, "same-key")
    with pytest.raises(RuntimeError):
        create_job(db, payload(ad_account_ids=["act_444"]), owner_id, "same-key")
    assert not replayed and replayed_same and same.id == job.id
    db = SessionLocal(); db.delete(db.query(LaunchJob).filter_by(id=job.id).one()); db.commit(); db.close()


def test_launch_is_paused_only_and_capped():
    with pytest.raises(ValueError, match="PAUSED only"):
        validate_launch_payload(payload(launch_status="ACTIVE"))
    too_many = payload(ad_account_ids=[f"act_{number}" for number in range(MAX_ADS_PER_LAUNCH + 1)])
    with pytest.raises(ValueError, match="limited"):
        validate_launch_payload(too_many)


def test_retries_are_bounded(job_id):
    db = SessionLocal()
    op = db.query(LaunchOperation).join(LaunchOperation.target).filter_by(job_id=job_id).first()
    op.attempt_count = MAX_OPERATION_ATTEMPTS
    op.status = "leased"
    db.commit()
    _result(db, op.id, retryable=True)
    db.refresh(op)
    assert op.status == "failed"
    assert "exceeded" in op.last_error
    db.close()


def test_uncertain_activation_is_reconciled_without_replay(job_id):
    service = fake_service()
    drain(service)
    db = SessionLocal()
    job = db.query(LaunchJob).filter_by(id=job_id).one()
    request_activation(db, job, service)
    db.close()
    service.set_status.side_effect = requests.Timeout("provider timeout")
    assert run_worker_once(lambda: service)
    db = SessionLocal(); job = db.query(LaunchJob).filter_by(id=job_id).one()
    op = next(op for target in job.targets for op in target.operations if op.kind == "activate_ad" and op.status == "needs_reconciliation")
    assert op.fb_object_id == op.request_payload["fb_object_id"]
    service.get_object.return_value = {"id": op.fb_object_id, "status": "ACTIVE"}
    assert reconcile_job(db, job, service) == []
    db.refresh(op)
    assert op.status == "succeeded"
    assert service.set_status.call_count == 1
    db.close()


def test_reused_parent_is_not_activated(owner_id):
    db = SessionLocal()
    reused = payload(ad_account_ids=["act_111"], campaign={"name": "Existing", "isExisting": True, "fbCampaignId": "existing_campaign"}, adset={"name": "Existing set", "fbAdsetId": "existing_adset"})
    job, _ = create_job(db, reused, owner_id, "reused-parent-key")
    launch_id = job.id
    db.close()
    service = fake_service(); drain(service)
    db = SessionLocal(); job = db.query(LaunchJob).filter_by(id=launch_id).one()
    request_activation(db, job, service); db.close()
    drain(service)
    activated_ids = [call.args[0] for call in service.set_status.call_args_list]
    assert "existing_campaign" not in activated_ids
    assert "existing_adset" not in activated_ids
    db = SessionLocal(); db.delete(db.query(LaunchJob).filter_by(id=launch_id).one()); db.commit(); db.close()
