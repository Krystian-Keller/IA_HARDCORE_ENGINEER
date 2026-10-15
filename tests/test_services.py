from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from google.genai import errors

from app.config import Settings
from app.schemas import AppError, RouteDecision
from app.services.gemini import Gemini
from app.tools.web_search import web_search


def sdk_mock(monkeypatch):
    factory = MagicMock()
    client = factory.return_value.__enter__.return_value
    monkeypatch.setattr("app.services.gemini.genai.Client", factory)
    return factory, client


def test_gemini_uses_env_configuration_and_structured_json(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "7")
    factory, client = sdk_mock(monkeypatch)
    client.models.generate_content.return_value = SimpleNamespace(text='{"route":"knowledge_web"}')
    result = Gemini(Settings.from_env()).generate("classify", schema=RouteDecision)
    assert result == '{"route":"knowledge_web"}'
    assert factory.call_args.kwargs["api_key"] == "fake-test-key"
    assert factory.call_args.kwargs["http_options"].timeout == 7000
    assert factory.call_args.kwargs["http_options"].retry_options.attempts == 1
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "test-model"
    assert kwargs["config"].response_mime_type == "application/json"
    assert kwargs["config"].response_schema is RouteDecision


def test_missing_key_is_controlled():
    with pytest.raises(AppError) as error:
        Gemini(Settings()).generate("hello")
    assert error.value.status_code == 503


@pytest.mark.parametrize("failure,status", [
    (httpx.ReadTimeout("timeout"), 504),
    (httpx.ConnectError("offline"), 502),
    (errors.ClientError(429, {"error": {"message": "quota"}}), 502),
    (errors.ServerError(504, {"error": {"message": "timeout"}}), 504),
])
def test_gemini_failures(monkeypatch, failure, status):
    _, client = sdk_mock(monkeypatch)
    client.models.generate_content.side_effect = failure
    with pytest.raises(AppError) as error:
        Gemini(Settings(gemini_api_key="fake")).generate("hello")
    assert error.value.status_code == status


@pytest.mark.parametrize("text", [None, "", "   "])
def test_empty_or_blocked_gemini_response(monkeypatch, text):
    _, client = sdk_mock(monkeypatch)
    client.models.generate_content.return_value = SimpleNamespace(text=text)
    with pytest.raises(AppError) as error:
        Gemini(Settings(gemini_api_key="fake")).generate("hello")
    assert error.value.status_code == 502


def test_search_normalizes_results_and_uses_duckduckgo(monkeypatch):
    factory = MagicMock()
    factory.return_value.text.return_value = [
        {"title": "Result", "body": "Context", "href": "https://example.com/news"},
        {"title": "Invalid", "body": "No URL", "href": "javascript:alert(1)"},
        {"title": "", "body": "Empty title", "href": "https://example.com"},
    ]
    monkeypatch.setattr("app.tools.web_search.DDGS", factory)
    results = web_search("query", max_results=3, timeout=8)
    assert len(results) == 1
    assert results[0].snippet == "Context"
    assert str(results[0].url) == "https://example.com/news"
    factory.assert_called_once_with(timeout=8)
    factory.return_value.text.assert_called_once_with("query", max_results=3, backend="duckduckgo")


def test_search_failure_is_controlled(monkeypatch):
    monkeypatch.setattr("app.tools.web_search.DDGS", MagicMock(side_effect=RuntimeError("blocked")))
    with pytest.raises(AppError) as error:
        web_search("query")
    assert error.value.status_code == 502
