import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ScrapedAd, SavedSearch, FacebookPage
from app.schemas.research import AdSearchRequest, ScrapedAdCreate

logger = logging.getLogger(__name__)


class ResearchService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def compute_content_hash(ad_data) -> str:
        """Compute hash from ad content for deduplication."""
        content = "|".join([
            f"external_id:{getattr(ad_data, 'external_id', '') or ''}",
            f"brand_name:{getattr(ad_data, 'brand_name', '') or ''}",
            f"headline:{getattr(ad_data, 'headline', '') or ''}",
            f"ad_copy:{getattr(ad_data, 'ad_copy', '') or ''}",
            f"cta_text:{getattr(ad_data, 'cta_text', '') or ''}",
            f"media_type:{getattr(ad_data, 'media_type', '') or ''}",
            f"ad_link:{getattr(ad_data, 'ad_link', '') or ''}",
            f"start_date:{getattr(ad_data, 'start_date', '') or ''}",
        ])
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def search_and_save(self, request: AdSearchRequest):
        """Execute search and save as SavedSearch with all ads"""
        from app.services.scraper import FacebookAdsLibraryAPI

        # Create scraper with db session for logging
        scraper = FacebookAdsLibraryAPI(db=self.db)

        # Execute search
        ads = await scraper.search_ads(
            request.query,
            request.limit,
            request.country,
            request.offset,
            request.exclude_ids,
            request.negative_keywords
        )

        # Track statistics
        ads_requested = request.limit
        ads_returned = len(ads)
        ads_new = 0
        ads_duplicate = 0

        # Create SavedSearch
        saved_search = SavedSearch(
            query=request.query,
            country=request.country,
            negative_keywords=request.negative_keywords if request.negative_keywords else None,
            vertical_id=request.vertical_id,
            search_type=request.search_type,
            schedule_config=request.schedule_config,
            is_active=True if request.search_type != 'one_time' else None,
            ads_requested=ads_requested,
            ads_returned=ads_returned
        )
        self.db.add(saved_search)
        self.db.flush()  # Get ID

        # Save all ads linked to this search
        saved_ads = []
        seen_hashes = set()  # Track hashes in current batch to avoid duplicates

        # Pre-compute all hashes once (avoids double-calling compute_content_hash)
        ad_hashes = {}
        all_hashes = []
        for ad in ads:
            h = self.compute_content_hash(ad)
            ad_hashes[id(ad)] = h
            if h:
                all_hashes.append(h)

        # Batch-preload existing ads by content_hash
        existing_ads_by_hash = {}
        if all_hashes:
            existing_ads = self.db.query(ScrapedAd).filter(
                ScrapedAd.content_hash.in_(all_hashes)
            ).all()
            existing_ads_by_hash = {ad.content_hash: ad for ad in existing_ads}

        # Batch-preload existing ads by external_id to avoid N+1 queries
        all_ext_ids = [ad.external_id for ad in ads if ad.external_id]
        existing_ads_by_ext_id = {}
        if all_ext_ids:
            ext_ads = self.db.query(ScrapedAd).filter(
                ScrapedAd.external_id.in_(all_ext_ids)
            ).all()
            existing_ads_by_ext_id = {ad.external_id: ad for ad in ext_ads}

        for ad_data in ads:
            # Use pre-computed hash
            content_hash = ad_hashes[id(ad_data)]

            # Skip if we've already seen this hash in this batch
            if content_hash and content_hash in seen_hashes:
                ads_duplicate += 1
                continue

            # Mark this hash as seen in this batch (do this early to prevent duplicates)
            if content_hash:
                seen_hashes.add(content_hash)

            # Check if ad exists by content_hash (from pre-loaded dict)
            existing = existing_ads_by_hash.get(content_hash) if content_hash else None

            # Fallback: check by external_id from pre-loaded dict
            if not existing and ad_data.external_id:
                existing = existing_ads_by_ext_id.get(ad_data.external_id)

            if existing:
                # Update last_seen timestamp and increment seen_count
                existing.last_seen = datetime.now(timezone.utc)
                existing.seen_count = (existing.seen_count or 0) + 1
                saved_ads.append(existing)
                ads_duplicate += 1
            else:
                ads_new += 1
                # Get or create FacebookPage
                fb_page = None
                if ad_data.brand_name:
                    fb_page = self.db.query(FacebookPage).filter(
                        FacebookPage.page_name == ad_data.brand_name
                    ).first()

                    if not fb_page:
                        fb_page = FacebookPage(page_name=ad_data.brand_name, total_ads=0)
                        self.db.add(fb_page)
                        self.db.flush()

                # Create ad with FacebookPage link and content_hash
                ad_dict = ad_data.model_dump()
                ad_dict['content_hash'] = content_hash
                if fb_page:
                    ad_dict['facebook_page_id'] = fb_page.id

                db_ad = ScrapedAd(**ad_dict, search_id=saved_search.id)
                self.db.add(db_ad)
                saved_ads.append(db_ad)

                # Add to existing_ads_by_hash to prevent duplicates within this batch
                if content_hash:
                    existing_ads_by_hash[content_hash] = db_ad

        # Update total_ads count for all affected FacebookPages
        try:
            self.db.flush()
        except Exception as e:
            # Handle duplicate content_hash errors gracefully
            if 'duplicate key value violates unique constraint' in str(e) and 'content_hash' in str(e):
                logger.warning("Duplicate content_hash during flush, rolling back and retrying with existing ads")
                self.db.rollback()

                # Retry: for each ad in saved_ads that's new (not yet in DB),
                # check if it now exists and update instead
                saved_ads_clean = []
                for ad in saved_ads:
                    if ad.id and self.db.query(ScrapedAd).filter(ScrapedAd.id == ad.id).first():
                        # Ad already exists in session/DB
                        saved_ads_clean.append(ad)
                    else:
                        # Try to find existing by content_hash
                        existing = self.db.query(ScrapedAd).filter(
                            ScrapedAd.content_hash == ad.content_hash
                        ).first()
                        if existing:
                            existing.last_seen = datetime.now(timezone.utc)
                            existing.seen_count = (existing.seen_count or 0) + 1
                            saved_ads_clean.append(existing)

                saved_ads = saved_ads_clean
                self.db.flush()
            else:
                raise

        page_ids = {ad.facebook_page_id for ad in saved_ads if ad.facebook_page_id}
        if page_ids:
            # Single grouped COUNT query instead of N individual queries
            counts = self.db.query(
                ScrapedAd.facebook_page_id,
                func.count(ScrapedAd.id).label('total')
            ).filter(
                ScrapedAd.facebook_page_id.in_(page_ids)
            ).group_by(ScrapedAd.facebook_page_id).all()

            count_map = {row.facebook_page_id: row.total for row in counts}
            pages = self.db.query(FacebookPage).filter(FacebookPage.id.in_(page_ids)).all()
            for fb_page in pages:
                fb_page.total_ads = count_map.get(fb_page.id, 0)

        # Update saved_search with final statistics
        saved_search.ads_new = ads_new
        saved_search.ads_duplicate = ads_duplicate

        self.db.commit()
        self.db.refresh(saved_search)

        return saved_search, saved_ads

    async def search_ads_async(self, request: AdSearchRequest):
        """Search without saving"""
        from app.services.scraper import FacebookAdsLibraryAPI
        api = FacebookAdsLibraryAPI(db=self.db)
        return await api.search_ads(
            request.query,
            request.limit,
            request.country,
            request.offset,
            request.exclude_ids,
            request.negative_keywords
        )

    def get_saved_searches(self):
        """Get all saved searches"""
        return self.db.query(SavedSearch).order_by(SavedSearch.created_at.desc()).all()

    def get_saved_search_with_ads(self, search_id: str):
        """Get saved search with its ads"""
        return self.db.query(SavedSearch).filter(SavedSearch.id == search_id).first()

    def delete_saved_search(self, search_id: str):
        """Delete saved search (cascades to ads)"""
        search = self.db.query(SavedSearch).filter(SavedSearch.id == search_id).first()
        if search:
            self.db.delete(search)
            self.db.commit()
            return True
        return False

