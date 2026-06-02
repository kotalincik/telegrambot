"""
Тесты для FastAPI endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Тест корневого endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Dental Booking API"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check():
    """Тест health check."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}