import pytest
from httpx import ASGITransport, AsyncClient

from server.main import app
from server.utils.auth_middleware import get_current_user


@pytest.fixture(autouse=True)
def mock_auth():
    """绕过 JWT 鉴权依赖"""
    app.dependency_overrides[get_current_user] = lambda: None
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_empty():
    """无传感器数据时返回空结构"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/iot/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["air"] is None
    assert data["soil"] is None
    assert data["actuators"]["irrigation"] is False
    assert data["actuators"]["mist"] is False


@pytest.mark.asyncio
async def test_air_sensor_empty():
    """无数据时返回 404"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/iot/sensors/air")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_soil_sensor_empty():
    """无数据时返回 404"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/iot/sensors/soil")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_actuator_invalid_key():
    """非法的执行器 key 应返回 503"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/iot/actuators/invalid_key?value=true")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_actuator_mist_unsupported():
    """v1.1 协议未定义 mist 控制命令"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/iot/actuators/mist?value=true")
    assert resp.status_code == 503
