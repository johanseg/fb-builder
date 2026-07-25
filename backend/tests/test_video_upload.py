"""Tests for video upload functionality."""
import pytest
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import os


class TestFacebookServiceVideo:
    """Tests for FacebookService video methods."""

    @pytest.fixture(autouse=True)
    def allow_test_account(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_FB_ACCOUNTS", "act_123456")

    def test_upload_video_from_url(self):
        """Test uploading video from URL."""
        from app.services.facebook_service import FacebookService

        with patch.object(FacebookService, 'initialize'):
            service = FacebookService()
        service.api = MagicMock()
        service.access_token = "test_token"
        service.ad_account_id = "123456"
        service.account = MagicMock()
        service.account.get_id_assured.return_value = "act_123456"
        service.account.get_id.return_value = "act_123456"
        mock_video = MagicMock()
        mock_video.__getitem__ = MagicMock(return_value="video_123")
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as media:
            media.write(b"fake video content")
            media_path = media.name

        with patch('app.services.facebook_service.download_remote_media_to_tempfile', return_value=media_path):
            with patch('app.services.facebook_service.AdVideo', return_value=mock_video):
                with patch.object(service, 'wait_for_video_ready', return_value={'status': 'ready'}):
                    with patch.object(service, 'get_video_thumbnails', return_value=['thumb1.jpg']):
                        result = service.upload_video("https://example.com/video.mp4", ad_account_id="123456")

        assert result['video_id'] == "video_123"
        assert result['status'] == 'ready'
        assert 'thumbnails' in result

    def test_upload_video_from_local_file(self):
        """Test uploading video from local file path."""
        from app.services.facebook_service import FacebookService

        with patch.object(FacebookService, 'initialize'):
            service = FacebookService()
        service.api = MagicMock()
        service.access_token = "test_token"
        service.ad_account_id = "123456"
        service.account = MagicMock()
        service.account.get_id_assured.return_value = "act_123456"
        service.account.get_id.return_value = "act_123456"
        mock_video = MagicMock()
        mock_video.__getitem__ = MagicMock(return_value="video_456")

        with patch.object(service, '_resolve_media_source', return_value=("/tmp/test.mp4", False)):
            with patch('app.services.facebook_service.AdVideo', return_value=mock_video):
                with patch.object(service, 'wait_for_video_ready', return_value={'status': 'ready'}):
                    with patch.object(service, 'get_video_thumbnails', return_value=[]):
                        result = service.upload_video(
                            "/path/to/video.mp4",
                            wait_for_ready=True
                        )

        assert result['video_id'] == "video_456"

    def test_get_video_status_ready(self):
        """Test getting video status when ready."""
        from app.services.facebook_service import FacebookService

        with patch.object(FacebookService, 'initialize'):
            service = FacebookService()
            service.access_token = "test_token"

            mock_response = MagicMock()
            mock_response.json.return_value = {
                'id': 'video_123',
                'status': {'video_status': 'ready'},
                'length': 30.5
            }

            with patch('requests.get', return_value=mock_response):
                result = service.get_video_status("video_123")

            assert result['status'] == 'ready'
            assert result['video_id'] == 'video_123'
            assert result['length'] == 30.5

    def test_get_video_status_processing(self):
        """Test getting video status when still processing."""
        from app.services.facebook_service import FacebookService

        with patch.object(FacebookService, 'initialize'):
            service = FacebookService()
            service.access_token = "test_token"

            mock_response = MagicMock()
            mock_response.json.return_value = {
                'id': 'video_123',
                'status': {'video_status': 'processing'}
            }

            with patch('requests.get', return_value=mock_response):
                result = service.get_video_status("video_123")

            assert result['status'] == 'processing'

    def test_get_video_status_error(self):
        """Test getting video status with error response."""
        from app.services.facebook_service import FacebookService

        with patch.object(FacebookService, 'initialize'):
            service = FacebookService()
            service.access_token = "test_token"

            mock_response = MagicMock()
            mock_response.json.return_value = {
                'error': {'message': 'Video not found'}
            }

            with patch('requests.get', return_value=mock_response):
                result = service.get_video_status("invalid_id")

            assert result['status'] == 'error'
            assert 'Video not found' in result['error']

    def test_get_video_thumbnails(self):
        """Test fetching video thumbnails."""
        from app.services.facebook_service import FacebookService

        with patch.object(FacebookService, 'initialize'):
            service = FacebookService()
            service.access_token = "test_token"

            mock_response = MagicMock()
            mock_response.json.return_value = {
                'data': [
                    {'uri': 'https://example.com/thumb1.jpg'},
                    {'uri': 'https://example.com/thumb2.jpg'},
                ]
            }

            with patch('requests.get', return_value=mock_response):
                result = service.get_video_thumbnails("video_123")

            assert len(result) == 2
            assert 'thumb1.jpg' in result[0]
            assert 'thumb2.jpg' in result[1]

    def test_wait_for_video_ready_success(self):
        """Test waiting for video to be ready."""
        from app.services.facebook_service import FacebookService

        with patch.object(FacebookService, 'initialize'):
            service = FacebookService()

            # First call returns processing, second returns ready
            with patch.object(service, 'get_video_status') as mock_status:
                mock_status.side_effect = [
                    {'status': 'processing'},
                    {'status': 'ready'}
                ]
                with patch('time.sleep'):  # Skip actual sleeping
                    result = service.wait_for_video_ready("video_123", timeout=60, interval=1)

            assert result['status'] == 'ready'

    def test_wait_for_video_ready_timeout(self):
        """Test timeout when waiting for video."""
        from app.services.facebook_service import FacebookService

        with patch.object(FacebookService, 'initialize'):
            service = FacebookService()

            with patch.object(service, 'get_video_status', return_value={'status': 'processing'}):
                with patch('time.sleep'):
                    with patch('time.time') as mock_time:
                        # Simulate timeout by returning increasing times
                        mock_time.side_effect = [0, 100, 200]
                        with pytest.raises(Exception, match="timeout"):
                            service.wait_for_video_ready("video_123", timeout=1)

    def test_create_creative_with_video(self):
        """Test creating ad creative with video."""
        from app.services.facebook_service import FacebookService

        with patch.object(FacebookService, 'initialize'):
            service = FacebookService()
        service.api = MagicMock()
        service.ad_account_id = "123456"
        service.account = MagicMock()
        service.account.get_id_assured.return_value = "act_123456"
        service.account.get_id.return_value = "act_123456"
        service.account.create_ad_creative.return_value = {'id': 'creative_123'}
        with patch.object(service, '_get_account', return_value=service.account):
            result = service.create_creative({'name': 'Test Video Creative', 'page_id': 'page_123', 'video_id': 'video_456', 'primary_text': 'Check out this video!', 'headline': 'Amazing Product', 'website_url': 'https://example.com', 'cta': 'SHOP_NOW', 'thumbnail_url': 'https://example.com/thumb.jpg'})
        params = service.account.create_ad_creative.call_args[1]['params']
        assert params['object_story_spec']['video_data']['video_id'] == 'video_456'
        assert params['object_story_spec']['video_data']['image_url'] == 'https://example.com/thumb.jpg'

    def test_create_creative_with_image(self):
        """Test creating ad creative with image (existing behavior)."""
        from app.services.facebook_service import FacebookService

        with patch.object(FacebookService, 'initialize'):
            service = FacebookService()
        service.api = MagicMock()
        service.ad_account_id = "123456"
        service.account = MagicMock()
        service.account.get_id_assured.return_value = "act_123456"
        service.account.get_id.return_value = "act_123456"
        service.account.create_ad_creative.return_value = {'id': 'creative_789'}
        with patch.object(service, '_get_account', return_value=service.account):
            result = service.create_creative({'name': 'Test Image Creative', 'page_id': 'page_123', 'image_hash': 'abc123hash', 'primary_text': 'Check this out!', 'headline': 'Great Deal', 'website_url': 'https://example.com', 'cta': 'LEARN_MORE'})
        story_spec = service.account.create_ad_creative.call_args[1]['params']['object_story_spec']
        assert 'link_data' in story_spec
        assert 'video_data' not in story_spec
        assert story_spec['link_data']['image_hash'] == 'abc123hash'
