"""Unit tests for the Gemini API proxy endpoint in main.py."""
import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@patch("httpx.AsyncClient.send")
def test_gemini_proxy_get_models(mock_send, client):
    """Test that a GET request to /v1beta/models is routed and forwarded correctly."""
    # Mock the response from Google API
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = b'{"models": [{"name": "models/gemini-1.5-pro"}]}'
    mock_response.headers = httpx.Headers({"content-type": "application/json"})
    
    mock_send.return_value = mock_response

    # Make request to the proxy
    response = client.get("/v1beta/models?key=test-api-key")

    assert response.status_code == 200
    assert response.json() == {"models": [{"name": "models/gemini-1.5-pro"}]}
    
    # Assert httpx was called with the correct forwarded URL
    mock_send.assert_called_once()
    called_request = mock_send.call_args[0][0]
    assert called_request.url == "https://generativelanguage.googleapis.com/v1beta/models?key=test-api-key"
    assert called_request.method == "GET"


@patch("httpx.AsyncClient.send")
@patch("asyncio.sleep")
def test_gemini_proxy_no_retry_on_429(mock_sleep, mock_send, client):
    """Test that the proxy fails immediately on 429 rate limit responses without retrying."""
    mock_response_429 = MagicMock(spec=httpx.Response)
    mock_response_429.status_code = 429
    mock_response_429.content = b"Rate limit exceeded"
    mock_response_429.headers = httpx.Headers({"content-type": "text/plain"})
    
    mock_send.return_value = mock_response_429

    response = client.post(
        "/v1beta/models/gemini-1.5-pro:generateContent",
        json={"contents": []}
    )

    assert response.status_code == 429
    assert response.content == b"Rate limit exceeded"
    
    # Verify we did NOT retry and did NOT sleep
    assert mock_send.call_count == 1
    mock_sleep.assert_not_called()


@patch("httpx.AsyncClient.send")
@patch("asyncio.sleep")
def test_gemini_proxy_retry_on_503(mock_sleep, mock_send, client):
    """Test that the proxy automatically retries on transient 503 service unavailable errors."""
    mock_response_503 = MagicMock(spec=httpx.Response)
    mock_response_503.status_code = 503
    mock_response_503.content = b"Service Unavailable"
    mock_response_503.headers = httpx.Headers({"content-type": "text/plain"})
    
    mock_response_200 = MagicMock(spec=httpx.Response)
    mock_response_200.status_code = 200
    mock_response_200.content = b'{"candidates": []}'
    mock_response_200.headers = httpx.Headers({"content-type": "application/json"})

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent")
    err = httpx.HTTPStatusError("Service Unavailable", request=req, response=mock_response_503)
    
    mock_send.side_effect = [err, mock_response_200]

    response = client.post(
        "/v1beta/models/gemini-1.5-pro:generateContent",
        json={"contents": []}
    )

    assert response.status_code == 200
    assert response.json() == {"candidates": []}
    
    # Verify we retried and slept once
    assert mock_send.call_count == 2
    mock_sleep.assert_called_once()

