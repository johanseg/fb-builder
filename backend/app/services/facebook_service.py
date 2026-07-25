import logging
import os
import time
from pathlib import Path

import requests
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adimage import AdImage
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.advideo import AdVideo
from facebook_business.adobjects.user import User

from app.core.utils import (
    GRAPH_API_VERSION,
    IMAGE_CONTENT_TYPES,
    VIDEO_CONTENT_TYPES,
    allowed_media_domains,
    download_remote_media_to_tempfile,
    resolve_managed_upload_path,
)

logger = logging.getLogger(__name__)

UPLOAD_DIR = (Path(__file__).resolve().parents[2] / "uploads").resolve()
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm'}
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
IMAGE_MAX_BYTES = 10 * 1024 * 1024
VIDEO_MAX_BYTES = 500 * 1024 * 1024

class FacebookService:
    def __init__(self):
        self.access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.ad_account_id = os.getenv("FACEBOOK_AD_ACCOUNT_ID")
        self.app_id = os.getenv("FACEBOOK_APP_ID")
        self.app_secret = os.getenv("FACEBOOK_APP_SECRET")
        self.api = None
        self.account = None
        
        if self.access_token and self.ad_account_id:
            self.initialize()

    def initialize(self):
        """Initialize the Facebook API connection."""
        try:
            FacebookAdsApi.init(
                app_id=self.app_id,
                app_secret=self.app_secret,
                access_token=self.access_token
            )
            self.api = FacebookAdsApi.get_default_api()
            
            # Only set up the AdAccount object if we have an ID
            if self.ad_account_id:
                # Ensure ad account ID has 'act_' prefix
                account_id = self.ad_account_id
                if not account_id.startswith('act_'):
                    account_id = f'act_{account_id}'
                self.account = AdAccount(account_id)
            
            return True
        except Exception as e:
            # Re-raise the exception so the caller knows what went wrong
            raise Exception(f"Facebook API Init Error: {str(e)}")

    def _resolve_media_source(
        self,
        source: str,
        *,
        media_kind: str,
        default_suffix: str,
        timeout: int,
        allowed_extensions: set[str] | None = None,
    ) -> tuple[str, bool]:
        """Resolve a remote URL or managed `/uploads/...` reference into a local file path."""
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"A {media_kind} source is required")

        normalized_source = source.strip()
        if normalized_source.startswith(('http://', 'https://')):
            local_path = download_remote_media_to_tempfile(
                normalized_source,
                media_kind=media_kind,
                allowed_mime_types=VIDEO_CONTENT_TYPES if media_kind == "video" else IMAGE_CONTENT_TYPES,
                max_bytes=VIDEO_MAX_BYTES if media_kind == "video" else IMAGE_MAX_BYTES,
                timeout=timeout,
                default_suffix=default_suffix,
                allowed_extensions=allowed_extensions,
                allowed_domains=allowed_media_domains(),
            )
            return local_path, True

        managed_path = resolve_managed_upload_path(normalized_source, UPLOAD_DIR)
        if managed_path is None:
            raise ValueError(
                f"Only http(s) URLs or managed /uploads/ references are allowed for {media_kind} uploads"
            )

        return str(managed_path), False


    def get_ad_accounts(self):
        """Fetch all ad accounts for the current user."""
        allowed_ids = self._allowed_account_ids()
        if not allowed_ids:
            logger.warning("ALLOWED_FB_ACCOUNTS is empty; refusing Meta account discovery")
            return []
        if not self.api:
            # Try to initialize if not already done
            self.initialize()
        
        # Use the SDK's User object to fetch ad accounts
        logger.info("Fetching ad accounts for user 'me'...")
        try:
            me = User(fbid='me', api=self.api)
            my_accounts = me.get_ad_accounts(fields=['id', 'name', 'account_id', 'account_status', 'currency', 'balance', 'amount_spent'])
            
            my_accounts = [acc for acc in my_accounts if acc.get('id') in allowed_ids]
                
            logger.info(f"Found {len(my_accounts)} accounts.")
            return [dict(acc) for acc in my_accounts]
        except Exception as e:
            logger.error(f"Error fetching ad accounts: {e}")
            raise e

    @staticmethod
    def _allowed_account_ids():
        return {
            value if value.startswith("act_") else f"act_{value}"
            for value in (item.strip() for item in os.getenv("ALLOWED_FB_ACCOUNTS", "").split(","))
            if value
        }

    def _get_account(self, ad_account_id=None):
        """Helper to get AdAccount object."""
        resolved_id = ad_account_id
        if not resolved_id and self.account:
            resolved_id = self.account.get_id()
        if resolved_id:
            if not resolved_id.startswith('act_'):
                resolved_id = f'act_{resolved_id}'
            allowed_ids = self._allowed_account_ids()
            if not allowed_ids or resolved_id not in allowed_ids:
                raise PermissionError("Ad account is outside ALLOWED_FB_ACCOUNTS")
            return AdAccount(resolved_id, api=self.api)

        raise Exception("No Ad Account ID provided and no default account set.")

    def get_campaigns(self, ad_account_id=None):
        """Fetch all campaigns from the ad account."""
        account = self._get_account(ad_account_id)
            
        fields = [
            Campaign.Field.id,
            Campaign.Field.name,
            Campaign.Field.objective,
            Campaign.Field.status,
            Campaign.Field.daily_budget,
            Campaign.Field.lifetime_budget,
            Campaign.Field.budget_remaining,
            Campaign.Field.bid_strategy,
            'is_adset_budget_sharing_enabled',
        ]

        
        return account.get_campaigns(fields=fields)

    def create_campaign(self, campaign_data, ad_account_id=None):
        """Create a new campaign."""
        account = self._get_account(ad_account_id)

        params = {
            Campaign.Field.name: campaign_data.get('name'),
            Campaign.Field.objective: campaign_data.get('objective'),
            Campaign.Field.status: 'PAUSED',
            Campaign.Field.special_ad_categories: [],
        }

        # Handle budget based on budget type
        budget_type = campaign_data.get('budget_type') or campaign_data.get('budgetType')
        daily_budget = campaign_data.get('daily_budget') or campaign_data.get('dailyBudget')
        
        if budget_type == 'CBO' and daily_budget:
            # Campaign Budget Optimization
            # Set budget at campaign level, do NOT set is_adset_budget_sharing_enabled
            params[Campaign.Field.daily_budget] = int(float(daily_budget) * 100)
        else:
            # Ad Set Budget Optimization (ABO)
            # Budget is set at ad set level, not campaign level
            # Starting with API v24.0+, is_adset_budget_sharing_enabled is REQUIRED for ABO
            # Set to False to enforce strict ad set budgets
            params['is_adset_budget_sharing_enabled'] = False

            
        bid_strategy = campaign_data.get('bid_strategy') or campaign_data.get('bidStrategy')
        if bid_strategy:
            params[Campaign.Field.bid_strategy] = bid_strategy

        return account.create_campaign(params=params)


    def get_pixels(self, ad_account_id=None):
        """Fetch all pixels for the ad account."""
        from facebook_business.adobjects.adspixel import AdsPixel
        
        account = self._get_account(ad_account_id)
        
        fields = [
            AdsPixel.Field.id,
            AdsPixel.Field.name,
        ]
        
        pixels = account.get_ads_pixels(fields=fields)
        return [dict(pixel) for pixel in pixels]

    def get_pages(self, ad_account_id=None):
        """Fetch all Facebook Pages accessible to the user."""
        from facebook_business.adobjects.page import Page
        
        # Fetch pages for the current user (not ad account specific)
        me = User(fbid='me', api=self.api)
        
        fields = [
            Page.Field.id,
            Page.Field.name,
            Page.Field.access_token,
            Page.Field.category,
        ]
        
        pages = me.get_accounts(fields=fields)
        return [dict(page) for page in pages]

    def get_adsets(self, ad_account_id=None, campaign_id=None):
        """Fetch all ad sets."""
        fields = [
            AdSet.Field.id,
            AdSet.Field.name,
            AdSet.Field.status,
            AdSet.Field.daily_budget,
            AdSet.Field.targeting,
            AdSet.Field.optimization_goal,
            AdSet.Field.billing_event,
            AdSet.Field.bid_amount,
            AdSet.Field.promoted_object,
            AdSet.Field.campaign_id,
        ]

        if campaign_id:
            # Fetch from campaign
            campaign = Campaign(campaign_id, api=self.api)
            return campaign.get_ad_sets(fields=fields)
        
        account = self._get_account(ad_account_id)
        return account.get_ad_sets(fields=fields)

    def get_ads(self, adset_id):
        """Fetch all ads for a specific ad set."""
        adset = AdSet(adset_id, api=self.api)
        fields = [
            Ad.Field.id,
            Ad.Field.name,
            Ad.Field.status,
            Ad.Field.creative,
        ]
        return adset.get_ads(fields=fields)

    def create_adset(self, adset_data, ad_account_id=None):
        """Create a new ad set."""
        account = self._get_account(ad_account_id)

        # Transform targeting from camelCase to snake_case
        targeting = adset_data.get('targeting', {})
        transformed_targeting = {}
        
        # Handle age fields
        if 'ageMin' in targeting:
            transformed_targeting['age_min'] = targeting['ageMin']
        if 'ageMax' in targeting:
            transformed_targeting['age_max'] = targeting['ageMax']
        
        # Handle genders
        if 'genders' in targeting:
            transformed_targeting['genders'] = targeting['genders']
        
        # Handle geo_locations - clean up empty arrays
        if 'geo_locations' in targeting:
            geo_locs = targeting['geo_locations']
            cleaned_geo_locs = {}
            
            # Only include non-empty arrays
            for key, value in geo_locs.items():
                if isinstance(value, list) and len(value) > 0:
                    cleaned_geo_locs[key] = value
                elif not isinstance(value, list):
                    # Include non-list values as-is
                    cleaned_geo_locs[key] = value
            
            if cleaned_geo_locs:
                transformed_targeting['geo_locations'] = cleaned_geo_locs
        
        # Handle publisher_platforms
        if 'publisher_platforms' in targeting:
            transformed_targeting['publisher_platforms'] = targeting['publisher_platforms']

        # Fix for Advantage Audience Flag Required error
        # Facebook now requires explicit opt-in/out for Advantage+ Audience
        # Default to 0 (Off) if not provided, unless user explicitly sets it
        advantage_audience = adset_data.get('advantage_audience', 0)
        transformed_targeting['targeting_automation'] = {
            'advantage_audience': advantage_audience
        }

        params = {
            AdSet.Field.name: adset_data.get('name'),
            AdSet.Field.campaign_id: adset_data.get('campaign_id'),
            AdSet.Field.billing_event: 'IMPRESSIONS',
            AdSet.Field.optimization_goal: adset_data.get('optimization_goal') or adset_data.get('optimizationGoal'),
            AdSet.Field.is_dynamic_creative: False,
            AdSet.Field.status: 'PAUSED',
            AdSet.Field.targeting: transformed_targeting,
        }

        # Handle promoted_object for conversion optimization
        if adset_data.get('optimization_goal') == 'OFFSITE_CONVERSIONS' or adset_data.get('optimizationGoal') == 'OFFSITE_CONVERSIONS':
            pixel_id = adset_data.get('pixelId') or adset_data.get('pixel_id')
            conversion_event = adset_data.get('conversionEvent') or adset_data.get('conversion_event')
            
            if pixel_id and conversion_event:
                params[AdSet.Field.promoted_object] = {
                    'pixel_id': pixel_id,
                    'custom_event_type': conversion_event
                }


        # Handle budget - only set for ABO campaigns (not CBO)
        # CBO = Campaign Budget Optimization (budget at campaign level)
        # ABO = Ad Set Budget Optimization (budget at ad set level)
        budget_type = adset_data.get('budget_type') or adset_data.get('budgetType')

        if budget_type != 'CBO':
            # For ABO campaigns, budget is required at ad set level
            budget = adset_data.get('daily_budget') or adset_data.get('dailyBudget')
            if budget:
                params[AdSet.Field.daily_budget] = int(float(budget) * 100)
        # For CBO campaigns, don't set daily_budget - it's managed at campaign level

        # Handle start time
        if adset_data.get('start_time') or adset_data.get('startTime'):
            start_time = adset_data.get('start_time') or adset_data.get('startTime')
            params[AdSet.Field.start_time] = start_time

        # Handle bid strategy and bid amount
        # For CBO campaigns, bid_strategy is set at campaign level - don't set at ad set level
        # For ABO campaigns, we can set bid_strategy at ad set level
        bid_amount = adset_data.get('bid_amount') or adset_data.get('bidAmount')
        bid_strategy = adset_data.get('bid_strategy') or adset_data.get('bidStrategy')

        if bid_amount:
            params[AdSet.Field.bid_amount] = int(float(bid_amount) * 100)
            if bid_strategy:
                params[AdSet.Field.bid_strategy] = bid_strategy
        elif budget_type != 'CBO':
            # Only set default bid_strategy for ABO campaigns
            # CBO campaigns inherit bid_strategy from campaign level
            params[AdSet.Field.bid_strategy] = 'LOWEST_COST_WITHOUT_CAP'

        return account.create_ad_set(params=params)

    def upload_image(self, image_path_or_url, ad_account_id=None):
        """Upload an image to the ad library."""
        account = self._get_account(ad_account_id)
        local_path = None
        cleanup_local_path = False

        try:
            local_path, cleanup_local_path = self._resolve_media_source(
                image_path_or_url,
                media_kind="image",
                default_suffix=".jpg",
                timeout=30,
            )

            image = AdImage(parent_id=account.get_id_assured())
            image[AdImage.Field.filename] = local_path
            image.remote_create()
            return image[AdImage.Field.hash]
        finally:
            if cleanup_local_path and local_path:
                try:
                    os.remove(local_path)
                except Exception:
                    pass

    def upload_video(self, video_path_or_url, ad_account_id=None, wait_for_ready=True, timeout=600):
        """Upload a video to the ad library.

        Args:
            video_path_or_url: Local file path or URL to video
            ad_account_id: Optional ad account ID
            wait_for_ready: Whether to wait for video processing to complete
            timeout: Max seconds to wait for processing (default 10 min)

        Returns:
            dict with video_id, status, and thumbnails (if ready)
        """
        account = self._get_account(ad_account_id)
        local_path = None
        cleanup_local_path = False

        try:
            local_path, cleanup_local_path = self._resolve_media_source(
                video_path_or_url,
                media_kind="video",
                default_suffix=".mp4",
                timeout=120,
                allowed_extensions=ALLOWED_VIDEO_EXTENSIONS,
            )

            # Create and upload video
            video = AdVideo(parent_id=account.get_id_assured())
            video[AdVideo.Field.filepath] = local_path
            video.remote_create()

            video_id = video['id']
            logger.info(f"Video uploaded with ID: {video_id}")

            if wait_for_ready:
                # Wait for video processing to complete
                status = self.wait_for_video_ready(video_id, timeout=timeout)
            else:
                status = self.get_video_status(video_id)

            # Get thumbnails if video is ready
            thumbnails = []
            if status.get('status') == 'ready':
                try:
                    thumbnails = self.get_video_thumbnails(video_id)
                except Exception as e:
                    logger.warning(f"Could not fetch thumbnails: {e}")

            return {
                'video_id': video_id,
                'status': status.get('status', 'processing'),
                'thumbnails': thumbnails
            }

        finally:
            if cleanup_local_path and local_path:
                try:
                    os.remove(local_path)
                except Exception:
                    pass

    def get_video_status(self, video_id):
        """Check the processing status of a video.

        Returns:
            dict with status ('processing', 'ready', 'error')
        """

        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{video_id}"
        params = {
            'fields': 'id,status,length,source',
            'access_token': self.access_token
        }

        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if 'error' in data:
            return {'status': 'error', 'error': data['error'].get('message', 'Unknown error')}

        # Facebook video status can be: processing, ready, error
        fb_status = data.get('status', {})
        if isinstance(fb_status, dict):
            video_status = fb_status.get('video_status', 'processing').lower()
        else:
            video_status = str(fb_status).lower()

        return {
            'status': video_status,
            'video_id': video_id,
            'length': data.get('length'),
            'source': data.get('source')
        }

    def wait_for_video_ready(self, video_id, timeout=600, interval=10):
        """Wait for video processing to complete.

        Args:
            video_id: Facebook video ID
            timeout: Max seconds to wait
            interval: Seconds between status checks

        Returns:
            dict with final status
        """
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            status = self.get_video_status(video_id)
            logger.info(f"Video {video_id} status: {status.get('status')}")

            if status.get('status') == 'ready':
                return status
            elif status.get('status') == 'error':
                raise Exception(f"Video processing failed: {status.get('error', 'Unknown error')}")

            time.sleep(interval)

        raise Exception(f"Video processing timeout after {timeout} seconds")

    def get_video_thumbnails(self, video_id):
        """Get auto-generated thumbnails for a video.

        Returns:
            list of thumbnail URLs
        """

        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{video_id}/thumbnails"
        params = {
            'access_token': self.access_token
        }

        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if 'error' in data:
            logger.warning(f"Thumbnail fetch error: {data['error']}")
            return []

        thumbnails = []
        for thumb in data.get('data', []):
            if 'uri' in thumb:
                thumbnails.append(thumb['uri'])

        return thumbnails

    def create_creative(self, creative_data, ad_account_id=None):
        """Create an ad creative (supports both image and video)."""
        account = self._get_account(ad_account_id)

        page_id = creative_data.get('page_id')
        image_hash = creative_data.get('image_hash')
        video_id = creative_data.get('video_id')

        # Determine if this is a video or image creative
        if video_id:
            # Video creative
            object_story_spec = {
                'page_id': page_id,
                'video_data': {
                    'video_id': video_id,
                    'message': creative_data.get('primary_text', ''),
                    'title': creative_data.get('headline', ''),
                    'call_to_action': {
                        'type': creative_data.get('cta', 'LEARN_MORE'),
                        'value': {
                            'link': creative_data.get('website_url')
                        }
                    }
                }
            }

            # Add custom thumbnail if provided
            if creative_data.get('thumbnail_url'):
                object_story_spec['video_data']['image_url'] = creative_data['thumbnail_url']
        else:
            # Image creative (existing logic)
            object_story_spec = {
                'page_id': page_id,
                'link_data': {
                    'image_hash': image_hash,
                    'link': creative_data.get('website_url'),
                    'message': creative_data.get('primary_text'),
                    'name': creative_data.get('headline'),
                    'description': creative_data.get('description'),
                    'call_to_action': {
                        'type': creative_data.get('cta', 'LEARN_MORE'),
                        'value': {
                            'link': creative_data.get('website_url')
                        }
                    }
                }
            }

        if creative_data.get('instagram_actor_id'):
            object_story_spec['instagram_actor_id'] = creative_data['instagram_actor_id']

        params = {
            AdCreative.Field.name: creative_data.get('name'),
            AdCreative.Field.object_story_spec: object_story_spec,
        }

        return account.create_ad_creative(params=params)

    def create_ad(self, ad_data, ad_account_id=None):
        """Create an ad."""
        account = self._get_account(ad_account_id)

        params = {
            Ad.Field.name: ad_data.get('name'),
            Ad.Field.adset_id: ad_data.get('adset_id'),
            Ad.Field.creative: {'creative_id': ad_data.get('creative_id')},
            Ad.Field.status: 'PAUSED',
        }

        return account.create_ad(params=params)

    def get_object(self, object_id):
        """Read a persisted Meta object during worker reconciliation."""
        response = requests.get(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/{object_id}",
            params={"fields": "id,status", "access_token": self.access_token}, timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def set_status(self, object_id, status):
        """Explicit activation path; launch creation never calls this."""
        response = requests.post(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/{object_id}",
            data={"status": status, "access_token": self.access_token}, timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_account_insights(self, ad_account_id=None, date_preset='last_7d'):
        """Fetch account-level performance insights (spend, clicks, purchases, ROAS)."""
        account = self._get_account(ad_account_id)

        insights = account.get_insights(
            fields=['spend', 'impressions', 'clicks', 'cpm', 'ctr', 'actions', 'purchase_roas'],
            params={'date_preset': date_preset, 'level': 'account'},
        )
        if not insights:
            return {'spend': 0, 'impressions': 0, 'clicks': 0, 'cpm': 0, 'ctr': 0, 'purchases': 0, 'roas': 0}

        row = dict(insights[0])
        purchases = 0
        for action in row.get('actions') or []:
            if action.get('action_type') == 'purchase':
                purchases = int(float(action.get('value', 0)))
                break
        roas = 0
        for entry in row.get('purchase_roas') or []:
            if entry.get('action_type') == 'omni_purchase':
                roas = float(entry.get('value', 0))
                break

        return {
            'spend': float(row.get('spend', 0)),
            'impressions': int(row.get('impressions', 0)),
            'clicks': int(row.get('clicks', 0)),
            'cpm': float(row.get('cpm', 0)),
            'ctr': float(row.get('ctr', 0)),
            'purchases': purchases,
            'roas': roas,
        }

    def search_locations(self, query, location_type='city', limit=10, ad_account_id=None):
        """Search for targeting locations."""
        account = self._get_account(ad_account_id)
        
        params = {
            'q': query,
            'type': 'adgeolocation',
            'location_types': [location_type],
            'limit': limit,
        }
        
        return account.get_targeting_search(params=params)
