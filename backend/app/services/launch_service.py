"""Background multi-account creative launch executor.

Runs as a FastAPI BackgroundTask (sync, threadpool). State lives in the
launch_jobs table so the frontend can poll progress and the job survives the
HTTP response. A Railway redeploy kills in-flight jobs; a startup reaper in
main.py marks them failed.
# ponytail: single worker thread per job, no queue — move to a poll loop over
# launch_jobs if redeploy-kills or concurrency ever become a real problem.
"""
import logging
import time

from app.database import SessionLocal
from app.models import FacebookAd, FacebookAdSet, FacebookCampaign, LaunchJob

logger = logging.getLogger(__name__)

# Seconds between ad creations to stay under FB rate limits.
AD_CREATE_PACING_SECONDS = 1


def _valid_texts(items):
    return [t for t in (items or []) if t and t.strip()]


def count_total_steps(payload: dict) -> int:
    """One step per ad permutation per account."""
    creatives = payload.get("creatives") or []
    headlines = _valid_texts(payload.get("headlines"))
    bodies = _valid_texts(payload.get("bodies"))
    accounts = payload.get("ad_account_ids") or []
    return len(accounts) * len(creatives) * len(headlines) * len(bodies)


def _update_job(db, job, **fields):
    for key, value in fields.items():
        setattr(job, key, value)
    db.commit()


def _upload_media(service, creative, ad_account_id, media_cache):
    """Upload a creative's media to FB once per (account, url). Returns (image_hash, video_data)."""
    is_video = creative.get("media_type") == "video" or (
        creative.get("video_url") and not creative.get("image_url")
    )
    if is_video:
        cache_key = (ad_account_id, "video", creative["video_url"])
        if cache_key not in media_cache:
            result = service.upload_video(
                creative["video_url"], ad_account_id, wait_for_ready=True
            )
            thumbnails = result.get("thumbnails") or []
            media_cache[cache_key] = {
                "video_id": result["video_id"],
                "thumbnail_url": creative.get("thumbnail_url") or (thumbnails[0] if thumbnails else None),
            }
        return None, media_cache[cache_key]

    cache_key = (ad_account_id, "image", creative["image_url"])
    if cache_key not in media_cache:
        media_cache[cache_key] = service.upload_image(creative["image_url"], ad_account_id)
    return media_cache[cache_key], None


def _create_campaign_and_adset(service, db, payload, ad_account_id, launch_status):
    """Create (or reuse) the campaign and adset for one account. Returns (fb_campaign_id, local_adset_id, fb_adset_id)."""
    campaign = payload["campaign"]
    adset = payload["adset"]
    source_account = payload.get("source_account_id")

    # An existing campaign/adset can only be reused on the account it belongs to;
    # every other account gets a fresh copy.
    reuse = bool(campaign.get("isExisting")) and ad_account_id == source_account

    if reuse and campaign.get("fbCampaignId"):
        fb_campaign_id = campaign["fbCampaignId"]
    else:
        result = service.create_campaign(
            {**campaign, "status": launch_status}, ad_account_id
        )
        fb_campaign_id = result["id"]

    local_campaign = FacebookCampaign(
        name=campaign.get("name") or "Untitled campaign",
        objective=campaign.get("objective") or "OUTCOME_TRAFFIC",
        budget_type=campaign.get("budgetType") or "ABO",
        daily_budget=int(float(campaign["dailyBudget"])) if campaign.get("dailyBudget") else None,
        bid_strategy=campaign.get("bidStrategy"),
        status=launch_status,
        fb_campaign_id=fb_campaign_id,
        ad_account_id=ad_account_id,
    )
    db.add(local_campaign)
    db.commit()
    db.refresh(local_campaign)

    if reuse and adset.get("fbAdsetId"):
        fb_adset_id = adset["fbAdsetId"]
    else:
        adset_payload = {
            **adset,
            "campaign_id": fb_campaign_id,
            "budget_type": payload["campaign"].get("budgetType"),
            "status": launch_status,
        }
        if campaign.get("budgetType") == "CBO":
            adset_payload["bidStrategy"] = campaign.get("bidStrategy")
            adset_payload["bidAmount"] = campaign.get("bidAmount")
        result = service.create_adset(adset_payload, ad_account_id)
        fb_adset_id = result["id"]

    local_adset = FacebookAdSet(
        campaign_id=local_campaign.id,
        name=adset.get("name") or "Untitled ad set",
        optimization_goal=adset.get("optimizationGoal") or "LINK_CLICKS",
        daily_budget=int(float(adset["dailyBudget"])) if adset.get("dailyBudget") else None,
        bid_strategy=adset.get("bidStrategy"),
        bid_amount=int(float(adset["bidAmount"])) if adset.get("bidAmount") else None,
        targeting=adset.get("targeting"),
        pixel_id=adset.get("pixelId"),
        conversion_event=adset.get("conversionEvent"),
        status=launch_status,
        fb_adset_id=fb_adset_id,
        ad_account_id=ad_account_id,
    )
    db.add(local_adset)
    db.commit()
    db.refresh(local_adset)

    return fb_campaign_id, local_adset.id, fb_adset_id


def run_launch_job(job_id: str):
    """Execute a launch job: replicate campaign+adset+ads into every selected account."""
    # Import here so tests can monkeypatch the api module's singleton factory.
    from app.api.v1.facebook import get_facebook_service

    db = SessionLocal()
    try:
        job = db.query(LaunchJob).filter(LaunchJob.id == job_id).first()
        if not job:
            logger.error("Launch job %s not found", job_id)
            return

        payload = job.payload
        launch_status = payload.get("launch_status") or "PAUSED"
        headlines = _valid_texts(payload.get("headlines"))
        bodies = _valid_texts(payload.get("bodies"))
        creatives = payload.get("creatives") or []
        results = []

        _update_job(db, job, status="running", total_steps=count_total_steps(payload), results=[])

        try:
            service = get_facebook_service()
        except Exception as e:
            logger.exception("Launch job %s: Facebook service init failed", job_id)
            _update_job(db, job, status="failed", error=f"Facebook service init failed: {e}")
            return

        media_cache = {}
        completed = 0
        failed = 0

        for ad_account_id in payload["ad_account_ids"]:
            steps_per_account = len(creatives) * len(headlines) * len(bodies)
            try:
                fb_campaign_id, local_adset_id, fb_adset_id = _create_campaign_and_adset(
                    service, db, payload, ad_account_id, launch_status
                )
            except Exception as e:
                db.rollback()
                logger.exception("Launch job %s: account %s setup failed", job_id, ad_account_id)
                failed += steps_per_account
                results.append({
                    "ad_account_id": ad_account_id,
                    "entity": "campaign",
                    "error": str(e),
                })
                _update_job(db, job, failed_steps=failed, results=list(results))
                continue

            results.append({
                "ad_account_id": ad_account_id,
                "entity": "campaign",
                "fb_id": fb_campaign_id,
                "name": payload["campaign"].get("name"),
            })

            for c_idx, creative in enumerate(creatives):
                for h_idx, headline in enumerate(headlines):
                    for b_idx, body in enumerate(bodies):
                        ad_name = f"{creative.get('name') or f'Creative {c_idx + 1}'} - H{h_idx + 1}B{b_idx + 1}"
                        try:
                            image_hash, video_data = _upload_media(
                                service, creative, ad_account_id, media_cache
                            )
                            creative_payload = {
                                "name": payload.get("creative_name") or ad_name,
                                "page_id": payload["page_id"],
                                "primary_text": body,
                                "headline": headline,
                                "description": payload.get("description"),
                                "cta": payload.get("cta") or "LEARN_MORE",
                                "website_url": payload.get("website_url"),
                            }
                            if payload.get("instagram_id"):
                                creative_payload["instagram_actor_id"] = payload["instagram_id"]
                            if video_data:
                                creative_payload["video_id"] = video_data["video_id"]
                                if video_data.get("thumbnail_url"):
                                    creative_payload["thumbnail_url"] = video_data["thumbnail_url"]
                            else:
                                creative_payload["image_hash"] = image_hash

                            fb_creative = service.create_creative(creative_payload, ad_account_id)
                            fb_ad = service.create_ad(
                                {
                                    "name": ad_name,
                                    "adset_id": fb_adset_id,
                                    "creative_id": fb_creative["id"],
                                    "status": launch_status,
                                },
                                ad_account_id,
                            )

                            db.add(FacebookAd(
                                adset_id=local_adset_id,
                                name=ad_name,
                                creative_name=payload.get("creative_name"),
                                image_url=creative.get("image_url"),
                                media_type=creative.get("media_type") or "image",
                                video_url=creative.get("video_url"),
                                video_id=video_data["video_id"] if video_data else None,
                                thumbnail_url=video_data.get("thumbnail_url") if video_data else None,
                                bodies=[body],
                                headlines=[headline],
                                description=payload.get("description"),
                                cta=payload.get("cta"),
                                website_url=payload.get("website_url"),
                                status=launch_status,
                                fb_ad_id=fb_ad["id"],
                                fb_creative_id=fb_creative["id"],
                                ad_account_id=ad_account_id,
                            ))
                            completed += 1
                            results.append({
                                "ad_account_id": ad_account_id,
                                "entity": "ad",
                                "name": ad_name,
                                "fb_id": fb_ad["id"],
                            })
                        except Exception as e:
                            db.rollback()
                            logger.exception(
                                "Launch job %s: ad '%s' failed on %s", job_id, ad_name, ad_account_id
                            )
                            failed += 1
                            results.append({
                                "ad_account_id": ad_account_id,
                                "entity": "ad",
                                "name": ad_name,
                                "error": str(e),
                            })
                        _update_job(
                            db, job,
                            completed_steps=completed,
                            failed_steps=failed,
                            results=list(results),
                        )
                        time.sleep(AD_CREATE_PACING_SECONDS)

        if failed == 0:
            final_status = "completed"
        elif completed > 0:
            final_status = "completed_with_errors"
        else:
            final_status = "failed"
        _update_job(db, job, status=final_status)
        logger.info("Launch job %s finished: %s (%d ok, %d failed)", job_id, final_status, completed, failed)
    except Exception as e:
        logger.exception("Launch job %s crashed", job_id)
        try:
            db.rollback()
            job = db.query(LaunchJob).filter(LaunchJob.id == job_id).first()
            if job:
                _update_job(db, job, status="failed", error=str(e))
        except Exception:
            logger.exception("Launch job %s: could not record crash", job_id)
    finally:
        db.close()
