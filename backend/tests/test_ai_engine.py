import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.src.ai.ai_engine import AIEngine, AIResponse


@pytest.fixture
def ai_engine():
    engine = AIEngine()
    return engine


def test_ai_response_parse_json():
    response = AIResponse(content='{"score": 7.5, "tags": ["test"]}')
    data = response.parse_json()
    assert data["score"] == 7.5
    assert data["tags"] == ["test"]


def test_ai_response_parse_json_with_markdown():
    response = AIResponse(content='```json\n{"score": 8.0}\n```')
    data = response.parse_json()
    assert data["score"] == 8.0


def test_cache_key_deterministic(ai_engine):
    key1 = ai_engine._cache_key("prompt", "system", "model")
    key2 = ai_engine._cache_key("prompt", "system", "model")
    assert key1 == key2


def test_cache_key_different_for_different_inputs(ai_engine):
    key1 = ai_engine._cache_key("prompt1", "system", "model")
    key2 = ai_engine._cache_key("prompt2", "system", "model")
    assert key1 != key2


@pytest.mark.asyncio
async def test_complete_returns_none_when_disabled(ai_engine):
    with patch("backend.src.ai.ai_engine.settings") as mock_settings:
        mock_settings.ai_enabled = False
        result = await ai_engine.complete("test prompt")
        assert result is None


@pytest.mark.asyncio
async def test_complete_uses_cache():
    engine = AIEngine()
    cache_key = engine._cache_key("test", "", "test-model")
    engine._cache[cache_key] = {"content": "cached result", "tokens": 0}

    with patch("backend.src.ai.ai_engine.settings") as mock_settings:
        mock_settings.ai_enabled = True
        mock_settings.ai_default_provider = "anthropic"
        mock_settings.ai_default_model = "test-model"
        mock_settings.ai_timeout_seconds = 3.0

        result = await engine.complete("test", model="test-model")
        assert result is not None
        assert result.content == "cached result"
        assert result.cached is True


def test_clear_cache(ai_engine):
    ai_engine._cache["test_key"] = {"content": "test", "tokens": 0}
    assert len(ai_engine._cache) > 0
    ai_engine.clear_cache()
    assert len(ai_engine._cache) == 0
