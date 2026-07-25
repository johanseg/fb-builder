"""PostgreSQL-backed, at-least-once Meta launch worker."""
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import or_

from app.database import SessionLocal
from app.models import AdModule, FacebookAd, FacebookAdModule, FacebookAdSet, FacebookCampaign, LaunchJob, LaunchOperation, LaunchTarget

logger = logging.getLogger(__name__)
LEASE_SECONDS = 120
MAX_ADS_PER_LAUNCH = 100
MAX_OPERATION_ATTEMPTS = 20


def _now():
    return datetime.now(timezone.utc)


def _valid_texts(items):
    return [item.strip() for item in (items or []) if isinstance(item, str) and item.strip()]


def count_total_steps(payload):
    return len(payload.get("ad_account_ids") or []) * len(payload.get("creatives") or []) * len(_valid_texts(payload.get("headlines"))) * len(_valid_texts(payload.get("bodies")))


def payload_digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def normalize_accounts(accounts):
    normalized = [account if account.startswith("act_") else f"act_{account}" for account in accounts]
    if len(normalized) != len(set(normalized)):
        raise ValueError("Duplicate ad accounts are not allowed")
    return normalized


def validate_launch_payload(payload):
    payload["ad_account_ids"] = normalize_accounts(payload.get("ad_account_ids") or [])
    if payload.get("source_account_id"):
        payload["source_account_id"] = normalize_accounts([payload["source_account_id"]])[0]
    if not payload["ad_account_ids"] or not payload.get("creatives"):
        raise ValueError("Select at least one ad account and creative")
    if payload.get("launch_status", "PAUSED") != "PAUSED":
        raise ValueError("Launch creation is PAUSED only; use activation after verification")
    total = count_total_steps(payload)
    if not total:
        raise ValueError("Nothing to launch: need creatives, headlines and bodies")
    if total > MAX_ADS_PER_LAUNCH:
        raise ValueError(f"A launch is limited to {MAX_ADS_PER_LAUNCH} ads")
    for creative in payload["creatives"]:
        is_video = creative.get("media_type") == "video"
        if not (creative.get("video_url") if is_video else creative.get("image_url")):
            raise ValueError("Every creative needs a matching media URL")
    campaign = payload.get("campaign") or {}
    adset = payload.get("adset") or {}
    if campaign.get("isExisting"):
        source = payload.get("source_account_id")
        if source not in payload["ad_account_ids"] or not campaign.get("fbCampaignId") or not adset.get("fbAdsetId"):
            raise ValueError("Existing campaign reuse requires its source account and Meta IDs")
    return total


def _operation(target, key, kind, ordinal, request, fb_object_id=None):
    return LaunchOperation(target_id=target.id, operation_key=key, kind=kind, ordinal=ordinal, request_payload=request, fb_object_id=fb_object_id)


def create_job(db, payload, created_by, idempotency_key):
    total = validate_launch_payload(payload)
    digest = payload_digest(payload)
    existing = db.query(LaunchJob).filter(LaunchJob.created_by == created_by, LaunchJob.idempotency_key == idempotency_key).first()
    if existing:
        if existing.payload_sha256 != digest:
            raise RuntimeError("idempotency key was already used with a different launch")
        return existing, True
    job = LaunchJob(payload=payload, created_by=created_by, idempotency_key=idempotency_key, payload_sha256=digest, status="queued", total_steps=total)
    db.add(job)
    db.flush()
    ordinal = 0
    for account in payload["ad_account_ids"]:
        reuse = bool(payload["campaign"].get("isExisting")) and account == payload.get("source_account_id")
        target = LaunchTarget(job_id=job.id, ad_account_id=account, campaign_owned_by_launch=not reuse, adset_owned_by_launch=not reuse)
        db.add(target)
        db.flush()
        token = job.id.replace("-", "")[:10]
        campaign = {**payload["campaign"], "status": "PAUSED", "name": f"{payload['campaign'].get('name') or 'Campaign'} [L{token}]", "reuse": reuse}
        adset = {**payload["adset"], "status": "PAUSED", "reuse": reuse}
        db.add(_operation(target, "campaign", "campaign", ordinal, campaign)); ordinal += 1
        db.add(_operation(target, "adset", "adset", ordinal, adset)); ordinal += 1
        media_keys = []
        for index, creative in enumerate(payload["creatives"]):
            key = f"media:{index}"
            media_keys.append(key)
            db.add(_operation(target, key, "media", ordinal, creative)); ordinal += 1
        for c_index, creative in enumerate(payload["creatives"]):
            for h_index, headline in enumerate(_valid_texts(payload.get("headlines"))):
                for b_index, body in enumerate(_valid_texts(payload.get("bodies"))):
                    name = f"{creative.get('name') or f'Creative {c_index + 1}'} - H{h_index + 1}B{b_index + 1} [L{token}]"
                    request = {"media_key": media_keys[c_index], "name": name, "headline": headline, "body": body, "creative": creative}
                    creative_key = f"creative:{c_index}:{h_index}:{b_index}"
                    db.add(_operation(target, creative_key, "creative", ordinal, request)); ordinal += 1
                    db.add(_operation(target, f"ad:{c_index}:{h_index}:{b_index}", "ad", ordinal, {**request, "creative_key": creative_key})); ordinal += 1
    db.commit()
    return job, False


def _claim_next(db):
    now = _now()
    db.query(LaunchOperation).filter(LaunchOperation.status == "leased", LaunchOperation.lease_expires_at < now).update({"status": "needs_reconciliation", "lease_expires_at": None}, synchronize_session=False)
    candidates = (db.query(LaunchOperation).join(LaunchTarget).join(LaunchJob)
          .filter(LaunchOperation.status.in_(("pending", "retryable")), LaunchOperation.available_at <= now,
                  LaunchJob.status.in_(("queued", "building", "activation_queued", "activating")))
          .order_by(LaunchOperation.ordinal, LaunchOperation.created_at).with_for_update(skip_locked=True).limit(50).all())
    if not candidates:
        db.commit()
        return None
    op = None
    for candidate in candidates:
        earlier = db.query(LaunchOperation).filter(LaunchOperation.target_id == candidate.target_id, LaunchOperation.ordinal < candidate.ordinal, LaunchOperation.status != "succeeded").first()
        if not earlier:
            op = candidate
            break
        if earlier.status in ("failed", "cancelled"):
            candidate.status = "cancelled"
    if not op:
        db.commit()
        return None
    op.status = "leased"; op.attempt_count += 1; op.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    op.target.status = "activating" if op.kind.startswith("activate_") else "building"
    op.target.job.status = "activating" if op.kind.startswith("activate_") else "building"
    db.commit(); db.refresh(op)
    return op.id


def _result(db, op_id, result=None, fb_object_id=None, retryable=False, needs_reconciliation=False, error=None):
    op = db.query(LaunchOperation).filter_by(id=op_id).first()
    if not op:
        return
    op.result = result or op.result
    op.fb_object_id = fb_object_id or op.fb_object_id
    if retryable and op.attempt_count >= MAX_OPERATION_ATTEMPTS:
        retryable = False
        error = f"operation exceeded {MAX_OPERATION_ATTEMPTS} attempts"
    op.lease_expires_at = None
    op.last_error = error
    op.status = (
        "needs_reconciliation"
        if needs_reconciliation
        else ("retryable" if retryable else ("failed" if error else "succeeded"))
    )
    if retryable:
        op.available_at = _now() + timedelta(seconds=15)
    db.commit()
    _refresh_job(db, op.target.job_id)


def _dependency(db, target_id, key):
    return db.query(LaunchOperation).filter_by(target_id=target_id, operation_key=key).one()


def _execute(db, op_id, service):
    op = db.query(LaunchOperation).filter_by(id=op_id).first()
    target, payload = op.target, op.target.job.payload
    try:
        if op.kind == "campaign":
            if op.request_payload.get("reuse"):
                target.campaign_fb_id = payload["campaign"]["fbCampaignId"]; db.commit()
                return _result(db, op.id, {"id": target.campaign_fb_id}, target.campaign_fb_id)
            remote = service.create_campaign(op.request_payload, target.ad_account_id)
            target.campaign_fb_id = remote["id"]
            db.add(FacebookCampaign(name=op.request_payload["name"], objective=payload["campaign"].get("objective") or "OUTCOME_TRAFFIC", budget_type=payload["campaign"].get("budgetType") or "ABO", status="PAUSED", fb_campaign_id=remote["id"], ad_account_id=target.ad_account_id)); db.commit()
            return _result(db, op.id, dict(remote), remote["id"])
        if op.kind == "adset":
            campaign = _dependency(db, target.id, "campaign")
            if op.request_payload.get("reuse"):
                target.adset_fb_id = payload["adset"]["fbAdsetId"]; db.commit()
                return _result(db, op.id, {"id": target.adset_fb_id}, target.adset_fb_id)
            remote = service.create_adset({**op.request_payload, "campaign_id": campaign.fb_object_id, "status": "PAUSED", "budget_type": payload["campaign"].get("budgetType")}, target.ad_account_id)
            target.adset_fb_id = remote["id"]
            local_campaign = db.query(FacebookCampaign).filter_by(fb_campaign_id=campaign.fb_object_id, ad_account_id=target.ad_account_id).first()
            if local_campaign: db.add(FacebookAdSet(campaign_id=local_campaign.id, name=op.request_payload.get("name") or "Ad set", optimization_goal=op.request_payload.get("optimizationGoal") or "LINK_CLICKS", status="PAUSED", fb_adset_id=remote["id"], ad_account_id=target.ad_account_id))
            db.commit(); return _result(db, op.id, dict(remote), remote["id"])
        if op.kind == "media":
            creative = op.request_payload; is_video = creative.get("media_type") == "video"
            if is_video and op.result and op.result.get("video_id"):
                status = service.get_video_status(op.result["video_id"])
                if status.get("status") != "ready": return _result(db, op.id, op.result, op.result["video_id"], retryable=True)
                return _result(db, op.id, {**op.result, "thumbnails": service.get_video_thumbnails(op.result["video_id"])}, op.result["video_id"])
            if is_video:
                remote = service.upload_video(creative["video_url"], target.ad_account_id, wait_for_ready=False)
                return _result(db, op.id, remote, remote["video_id"], retryable=remote.get("status") != "ready")
            image_hash = service.upload_image(creative["image_url"], target.ad_account_id)
            return _result(db, op.id, {"image_hash": image_hash}, image_hash)
        if op.kind == "creative":
            media = _dependency(db, target.id, op.request_payload["media_key"])
            data = {"name": op.request_payload["name"], "page_id": payload["page_id"], "primary_text": op.request_payload["body"], "headline": op.request_payload["headline"], "description": payload.get("description"), "cta": payload.get("cta") or "LEARN_MORE", "website_url": payload.get("website_url")}
            if media.result.get("video_id"): data["video_id"] = media.result["video_id"]
            else: data["image_hash"] = media.result["image_hash"]
            remote = service.create_creative(data, target.ad_account_id); return _result(db, op.id, dict(remote), remote["id"])
        if op.kind == "ad":
            creative = _dependency(db, target.id, op.request_payload["creative_key"])
            remote = service.create_ad({"name": op.request_payload["name"], "adset_id": target.adset_fb_id, "creative_id": creative.fb_object_id, "status": "PAUSED"}, target.ad_account_id)
            local_adset = db.query(FacebookAdSet).filter_by(fb_adset_id=target.adset_fb_id, ad_account_id=target.ad_account_id).first()
            if local_adset:
                local_ad = FacebookAd(
                    adset_id=local_adset.id,
                    name=op.request_payload["name"],
                    bodies=[op.request_payload["body"]],
                    headlines=[op.request_payload["headline"]],
                    status="PAUSED",
                    fb_ad_id=remote["id"],
                    fb_creative_id=creative.fb_object_id,
                    ad_account_id=target.ad_account_id,
                )
                db.add(local_ad)
                db.flush()
                module_ids = op.request_payload.get("creative", {}).get("module_ids") or []
                existing_ids = {
                    row[0]
                    for row in db.query(AdModule.id).filter(AdModule.id.in_(module_ids)).all()
                }
                for module_id in module_ids:
                    if module_id in existing_ids:
                        db.add(FacebookAdModule(facebook_ad_id=local_ad.id, ad_module_id=module_id))
            db.commit(); return _result(db, op.id, dict(remote), remote["id"])
        if op.kind.startswith("activate_"):
            service.set_status(op.request_payload["fb_object_id"], "ACTIVE")
            return _result(db, op.id, {"id": op.request_payload["fb_object_id"], "status": "ACTIVE"}, op.request_payload["fb_object_id"])
        raise ValueError(f"Unknown launch operation {op.kind}")
    except requests.Timeout as exc:
        logger.warning("launch operation %s has an uncertain provider outcome", op.id)
        _result(db, op.id, error=str(exc), needs_reconciliation=True)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 0
        retryable = op.kind == "media" and (status == 429 or status >= 500)
        _result(
            db,
            op.id,
            error=str(exc),
            retryable=retryable,
            needs_reconciliation=not retryable and (status == 429 or status >= 500),
        )
    except Exception as exc:
        logger.exception("launch operation %s failed", op.id)
        _result(db, op.id, error=str(exc))


def _refresh_job(db, job_id):
    job = db.query(LaunchJob).filter_by(id=job_id).first()
    operations = db.query(LaunchOperation).join(LaunchTarget).filter(LaunchTarget.job_id == job_id).all()
    job.completed_steps = sum(1 for op in operations if op.kind == "ad" and op.status == "succeeded")
    job.failed_steps = sum(1 for op in operations if op.kind == "ad" and op.status == "failed")
    for target in job.targets:
        target_ops = [op for op in operations if op.target_id == target.id]
        if any(op.status == "needs_reconciliation" for op in target_ops):
            target.status = "reconciliation_required"
        if any(op.status == "failed" for op in target_ops):
            target.status = "failed"
    activation_ops = [op for op in operations if op.kind.startswith("activate_")]
    if job.activation_requested_at and activation_ops and not all(op.status == "succeeded" for op in activation_ops):
        job.status = "activation_queued" if any(op.status in ("pending", "retryable", "needs_reconciliation") for op in activation_ops) else "activating"
    elif any(op.status == "needs_reconciliation" for op in operations):
        job.status = "reconciliation_required"
    elif operations and all(op.status == "succeeded" for op in operations):
        job.status = "active" if job.activation_requested_at else "ready"; job.activated_at = _now() if job.activation_requested_at else None
        for target in job.targets: target.status = "active" if job.activation_requested_at else "ready"
    elif all(target.status == "failed" for target in job.targets):
        job.status = "failed"
    elif all(op.status in ("succeeded", "failed") for op in operations):
        job.status = "reconciliation_required"
    db.commit()


def run_worker_once(service_factory=None):
    from app.api.v1.facebook import get_facebook_service
    db = SessionLocal()
    try:
        op_id = _claim_next(db)
        if not op_id: return False
        _execute(db, op_id, (service_factory or get_facebook_service)())
        return True
    finally:
        db.close()


def verify_activation_ready(db, job, service):
    if job.status != "ready" or any(target.status != "ready" for target in job.targets):
        raise ValueError("Launch is not fully reconciled and ready for activation")
    for target in job.targets:
        ads = db.query(LaunchOperation).filter_by(target_id=target.id, kind="ad", status="succeeded").order_by(LaunchOperation.ordinal).all()
        required_ids = [ad.fb_object_id for ad in ads]
        if target.adset_owned_by_launch:
            required_ids.append(target.adset_fb_id)
        if target.campaign_owned_by_launch:
            required_ids.append(target.campaign_fb_id)
        for object_id in required_ids:
            remote = service.get_object(object_id)
            if remote.get("status") != "PAUSED":
                raise ValueError("Activation preflight requires every launch-owned object to be PAUSED")


def request_activation(db, job, service):
    verify_activation_ready(db, job, service)
    for target in job.targets:
        ads = db.query(LaunchOperation).filter_by(
            target_id=target.id, kind="ad", status="succeeded"
        ).order_by(LaunchOperation.ordinal).all()
        ordinal = max(op.ordinal for op in target.operations) + 1
        for ad in ads:
            db.add(_operation(target, f"activate:{ad.operation_key}", "activate_ad", ordinal, {"fb_object_id": ad.fb_object_id}, ad.fb_object_id)); ordinal += 1
        if target.adset_owned_by_launch: db.add(_operation(target, "activate:adset", "activate_adset", ordinal, {"fb_object_id": target.adset_fb_id}, target.adset_fb_id)); ordinal += 1
        if target.campaign_owned_by_launch: db.add(_operation(target, "activate:campaign", "activate_campaign", ordinal, {"fb_object_id": target.campaign_fb_id}, target.campaign_fb_id))
    job.activation_requested_at = _now(); job.status = "activation_queued"; db.commit()


def reconcile_job(db, job, service):
    """Resolve only operations that already have a provider ID; never replay an uncertain create."""
    blocked = []
    operations = (
        db.query(LaunchOperation)
        .join(LaunchTarget)
        .filter(
            LaunchTarget.job_id == job.id,
            LaunchOperation.status == "needs_reconciliation",
        )
        .all()
    )
    for op in operations:
        if not op.fb_object_id:
            blocked.append(op.operation_key)
            continue
        try:
            remote = service.get_object(op.fb_object_id)
            expected = "ACTIVE" if op.kind.startswith("activate_") else None
            if expected and remote.get("status") != expected:
                blocked.append(op.operation_key)
                continue
            op.result = {**(op.result or {}), **remote}
            op.status = "succeeded"
            op.last_error = None
        except Exception:
            blocked.append(op.operation_key)
    db.commit()
    _refresh_job(db, job.id)
    return blocked
