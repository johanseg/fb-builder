"""Shared utility regression tests."""

import json

import pytest


def test_extract_json_from_text_strips_markdown_fences():
    from app.core.utils import extract_json_from_text

    payload = extract_json_from_text(
        """```json
        {"variations": [{"headline": "Test"}]}
        ```"""
    )

    assert payload == {"variations": [{"headline": "Test"}]}


def test_extract_json_from_text_accepts_plain_json():
    from app.core.utils import extract_json_from_text

    payload = extract_json_from_text('{"ok": true, "count": 2}')

    assert payload == {"ok": True, "count": 2}


def test_extract_json_from_text_raises_on_invalid_json():
    from app.core.utils import extract_json_from_text

    with pytest.raises(json.JSONDecodeError):
        extract_json_from_text("not valid json")


def test_extract_markdown_list_items_splits_actual_newlines():
    from app.core.utils import extract_markdown_list_items

    items = extract_markdown_list_items("- first\n* second\n3. third")

    assert items == ["first", "second", "third"]


def test_extract_markdown_list_items_falls_back_to_full_text():
    from app.core.utils import extract_markdown_list_items

    raw_text = "single response without bullets"

    assert extract_markdown_list_items(raw_text) == [raw_text]
