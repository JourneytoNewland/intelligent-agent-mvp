"""
健康检查端点集成测试
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.integration
async def test_health_endpoint():
    """测试健康检查端点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "database" in data
        assert "redis" in data


@pytest.mark.integration
async def test_health_endpoint_with_services_down():
    """测试服务不可用时的健康检查"""
    # 这个测试需要数据库和 Redis 不可用时运行
    # 在 CI/CD 环境中可以通过环境变量控制
    pass


@pytest.mark.integration
async def test_detailed_health_endpoint():
    """测试详细健康检查端点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health/detailed")

        assert response.status_code == 200

        data = response.json()
        assert "database" in data
        assert "redis" in data


@pytest.mark.integration
async def test_root_endpoint():
    """测试根路径端点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")

        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data
