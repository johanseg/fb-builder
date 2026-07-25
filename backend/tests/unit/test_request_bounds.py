"""Trust-boundary limits for paid or batch generation requests."""

import pytest
from pydantic import ValidationError

from app.api.v1.copy_generation import CopyGenerationRequest
from app.api.v1.generated_ads import BatchSaveRequest, ImageGenerationRequest
from app.api.v1.modular_generation import IterationRequest, ModularGenerationRequest


def test_image_generation_limits_total_outputs_to_eight():
    with pytest.raises(ValidationError):
        ImageGenerationRequest(count=3, imageSizes=[{}, {}, {}])


def test_copy_and_module_generation_counts_are_bounded():
    with pytest.raises(ValidationError):
        CopyGenerationRequest(
            brand={}, product={}, profile={}, campaignDetails={}, variationCount=11
        )
    with pytest.raises(ValidationError):
        ModularGenerationRequest(product_id="product", module_type="intro", count=11)
    with pytest.raises(ValidationError):
        IterationRequest(module_id="module", count=0)


def test_batch_save_limits_ads_to_one_hundred():
    ad = {
        "id": "ad",
        "headline": "Headline",
        "body": "Body",
        "imageUrl": "https://example.com/image.png",
        "cta": "SHOP_NOW",
    }
    with pytest.raises(ValidationError):
        BatchSaveRequest(ads=[ad] * 101)
