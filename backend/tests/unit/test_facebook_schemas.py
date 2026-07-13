"""Facebook schema regression tests."""


def test_campaign_create_request_accepts_camel_case_aliases(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/testdb")
    from app.api.v1.facebook import CampaignCreateRequest

    request = CampaignCreateRequest(
        name="Alias Campaign",
        objective="CONVERSIONS",
        budgetType="CBO",
        dailyBudget=25.0,
        bidStrategy="LOWEST_COST_WITHOUT_CAP",
    )

    dumped = request.model_dump(exclude_none=True)

    assert request.budget_type == "CBO"
    assert request.daily_budget == 25.0
    assert request.bid_strategy == "LOWEST_COST_WITHOUT_CAP"
    assert dumped["budget_type"] == "CBO"
    assert dumped["daily_budget"] == 25.0
    assert dumped["bid_strategy"] == "LOWEST_COST_WITHOUT_CAP"
    assert "budgetType" not in dumped


def test_adset_create_request_accepts_aliases_for_optional_fields(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/testdb")
    from app.api.v1.facebook import AdSetCreateRequest

    request = AdSetCreateRequest(
        name="Alias AdSet",
        campaign_id="campaign-123",
        optimizationGoal="OFFSITE_CONVERSIONS",
        dailyBudget=15.0,
        bidAmount=5.0,
        pixelId="pixel-123",
        conversionEvent="PURCHASE",
        startTime="2026-04-01T00:00:00Z",
    )

    dumped = request.model_dump(exclude_none=True)

    assert request.optimization_goal == "OFFSITE_CONVERSIONS"
    assert request.daily_budget == 15.0
    assert request.bid_amount == 5.0
    assert request.pixel_id == "pixel-123"
    assert request.conversion_event == "PURCHASE"
    assert request.start_time == "2026-04-01T00:00:00Z"
    assert dumped["optimization_goal"] == "OFFSITE_CONVERSIONS"
    assert dumped["pixel_id"] == "pixel-123"
    assert dumped["conversion_event"] == "PURCHASE"
