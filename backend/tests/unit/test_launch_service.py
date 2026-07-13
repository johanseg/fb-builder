"""Unit tests for the multi-account background launch executor."""
from unittest.mock import MagicMock

import pytest

from app.database import SessionLocal
from app.models import FacebookAd, FacebookAdSet, FacebookCampaign, LaunchJob
from app.services.launch_service import count_total_steps, run_launch_job
import app.services.launch_service as launch_service_module


def make_payload(**overrides):
    payload = {
        "ad_account_ids": ["act_111", "act_222"],
        "launch_status": "PAUSED",
        "source_account_id": "act_111",
        "campaign": {"name": "Test Campaign", "objective": "OUTCOME_TRAFFIC", "budgetType": "ABO"},
        "adset": {"name": "Test AdSet", "optimizationGoal": "LINK_CLICKS", "dailyBudget": 10},
        "page_id": "page_1",
        "instagram_id": None,
        "creative_name": "Test Creative",
        "creatives": [{"image_url": "https://example.com/a.jpg", "media_type": "image", "name": "A"}],
        "headlines": ["H1", "H2"],
        "bodies": ["B1"],
        "description": "desc",
        "cta": "LEARN_MORE",
        "website_url": "https://example.com",
    }
    payload.update(overrides)
    return payload


def make_fake_service():
    service = MagicMock()
    service.create_campaign.side_effect = lambda data, acct: {"id": f"fbcamp_{acct}"}
    service.create_adset.side_effect = lambda data, acct: {"id": f"fbadset_{acct}"}
    service.upload_image.side_effect = lambda url, acct: f"hash_{acct}"
    service.create_creative.side_effect = lambda data, acct: {"id": f"fbcreative_{acct}"}
    service.create_ad.side_effect = lambda data, acct: {"id": f"fbad_{acct}_{data['name']}"}
    return service


@pytest.fixture()
def launch_env(monkeypatch):
    """Create a LaunchJob, patch out FB + pacing, and clean up commits afterwards."""
    monkeypatch.setattr(launch_service_module.time, "sleep", lambda s: None)
    created = {}

    def setup(payload, service):
        monkeypatch.setattr("app.api.v1.facebook.get_facebook_service", lambda: service)
        db = SessionLocal()
        job = LaunchJob(payload=payload)
        db.add(job)
        db.commit()
        db.refresh(job)
        created["job_id"] = job.id
        db.close()
        return job.id

    yield setup

    # run_launch_job commits its own transactions — remove them explicitly
    if created:
        db = SessionLocal()
        for campaign in db.query(FacebookCampaign).filter(FacebookCampaign.name == "Test Campaign").all():
            db.delete(campaign)  # cascades to adsets/ads
        job = db.query(LaunchJob).filter(LaunchJob.id == created["job_id"]).first()
        if job:
            db.delete(job)
        db.commit()
        db.close()


def get_job(job_id):
    db = SessionLocal()
    job = db.query(LaunchJob).filter(LaunchJob.id == job_id).first()
    db.expunge(job)
    db.close()
    return job


def test_count_total_steps():
    payload = make_payload()
    # 2 accounts x 1 creative x 2 headlines x 1 body
    assert count_total_steps(payload) == 4
    assert count_total_steps(make_payload(headlines=["", "  "])) == 0


def test_launch_creates_per_account_campaigns_and_ads(launch_env):
    service = make_fake_service()
    job_id = launch_env(make_payload(), service)

    run_launch_job(job_id)

    job = get_job(job_id)
    assert job.status == "completed"
    assert job.completed_steps == 4
    assert job.failed_steps == 0

    # One campaign per account, image uploaded once per account (cached across permutations)
    assert service.create_campaign.call_count == 2
    assert service.upload_image.call_count == 2
    assert service.create_ad.call_count == 4

    db = SessionLocal()
    campaigns = db.query(FacebookCampaign).filter(FacebookCampaign.name == "Test Campaign").all()
    assert {c.ad_account_id for c in campaigns} == {"act_111", "act_222"}
    ads = (
        db.query(FacebookAd)
        .join(FacebookAdSet, FacebookAd.adset_id == FacebookAdSet.id)
        .filter(FacebookAdSet.campaign_id.in_([c.id for c in campaigns]))
        .all()
    )
    assert len(ads) == 4
    assert all(ad.ad_account_id in ("act_111", "act_222") for ad in ads)
    assert all(ad.status == "PAUSED" for ad in ads)
    db.close()


def test_account_failure_does_not_abort_other_accounts(launch_env):
    service = make_fake_service()

    def failing_campaign(data, acct):
        if acct == "act_111":
            raise RuntimeError("no access to this account")
        return {"id": f"fbcamp_{acct}"}

    service.create_campaign.side_effect = failing_campaign
    job_id = launch_env(make_payload(), service)

    run_launch_job(job_id)

    job = get_job(job_id)
    assert job.status == "completed_with_errors"
    assert job.completed_steps == 2  # act_222 only
    assert job.failed_steps == 2  # act_111's two permutations
    errors = [r for r in job.results if r.get("error")]
    assert errors and errors[0]["ad_account_id"] == "act_111"


def test_all_failures_marks_job_failed(launch_env):
    service = make_fake_service()
    service.upload_image.side_effect = RuntimeError("upload broken")
    job_id = launch_env(make_payload(ad_account_ids=["act_111"]), service)

    run_launch_job(job_id)

    job = get_job(job_id)
    assert job.status == "failed"
    assert job.completed_steps == 0
    assert job.failed_steps == 2
