#!/usr/bin/env python3
"""
Stage 1 验证脚本

验证项目脚手架和基础设施的完整性
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试所有模块是否可以正常导入"""
    print("🔍 测试模块导入...")

    try:
        # 测试配置模块
        from app.config import settings, get_settings
        print("  ✅ app.config 导入成功")

        # 测试依赖注入模块
        from app.dependencies import get_settings, get_database_pool, get_redis_client
        print("  ✅ app.dependencies 导入成功")

        # 测试 Schema
        from app.schemas.health import HealthResponse, ServiceStatus
        print("  ✅ app.schemas.health 导入成功")

        # 测试主应用
        from app.main import app, create_app
        print("  ✅ app.main 导入成功")

        # 测试 API 路由
        from app.api.v1.health import router
        print("  ✅ app.api.v1.health 导入成功")

        return True

    except ImportError as e:
        print(f"  ❌ 导入失败: {e}")
        return False


def test_config():
    """测试配置加载"""
    print("\n🔍 测试配置加载...")

    try:
        from app.config import settings

        print(f"  ✅ 应用名称: {settings.app_name}")
        print(f"  ✅ 应用版本: {settings.app_version}")
        print(f"  ✅ 运行环境: {settings.environment}")
        print(f"  ✅ 调试模式: {settings.debug}")

        # 测试 LLM 配置
        llm_config = settings.get_llm_config("zhipuai")
        print(f"  ✅ 智谱AI API Key: {'*' * 20}{llm_config['api_key'][-4:]}")
        print(f"  ✅ 智谱AI 模型: {llm_config['model']}")

        # 测试 CORS 配置
        cors_origins = settings.cors_origins
        print(f"  ✅ CORS 源: {cors_origins}")

        return True

    except Exception as e:
        print(f"  ❌ 配置加载失败: {e}")
        return False


def test_app_creation():
    """测试 FastAPI 应用创建"""
    print("\n🔍 测试 FastAPI 应用创建...")

    try:
        from app.main import create_app

        app = create_app()

        # 验证应用配置
        assert app.title == "IntelligentAgentMVP"
        assert app.version == "0.1.0"
        print(f"  ✅ 应用标题: {app.title}")
        print(f"  ✅ 应用版本: {app.version}")

        # 验证路由
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/health" in routes
        assert "/health/detailed" in routes
        print(f"  ✅ 路由已注册: {len(routes)} 个")

        return True

    except Exception as e:
        print(f"  ❌ 应用创建失败: {e}")
        return False


def test_project_structure():
    """测试项目结构完整性"""
    print("\n🔍 测试项目结构...")

    required_dirs = [
        "app",
        "app/api/v1",
        "app/core/graph",
        "app/core/skills",
        "app/core/mcp",
        "app/core/memory",
        "app/core/models",
        "app/observability",
        "app/schemas",
        "app/utils",
        "tests/unit",
        "tests/integration",
        "tests/e2e",
        "docker",
        "scripts",
        "sql"
    ]

    required_files = [
        "app/main.py",
        "app/config.py",
        "app/dependencies.py",
        "app/api/v1/health.py",
        "app/schemas/health.py",
        "requirements.txt",
        ".env.example",
        ".env",
        "README.md",
        "docker/docker-compose.yml",
        "docker/Dockerfile",
        "sql/01_init_database.sql",
        "scripts/start.sh",
        "tests/conftest.py",
        "tests/integration/test_health_endpoint.py"
    ]

    all_ok = True

    # 检查目录
    for dir_path in required_dirs:
        if (project_root / dir_path).exists():
            print(f"  ✅ {dir_path}")
        else:
            print(f"  ❌ {dir_path} (缺失)")
            all_ok = False

    # 检查文件
    for file_path in required_files:
        if (project_root / file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} (缺失)")
            all_ok = False

    return all_ok


def test_file_counts():
    """统计代码文件和行数"""
    print("\n🔍 代码统计...")

    py_files = list(project_root.rglob("*.py"))
    py_files = [f for f in py_files if "__pycache__" not in str(f)]

    total_lines = 0
    for py_file in py_files:
        total_lines += len(py_file.read_text().splitlines())

    print(f"  📊 Python 文件数: {len(py_files)}")
    print(f"  📊 代码总行数: {total_lines}")

    return True


def main():
    """主验证流程"""
    print("=" * 60)
    print("🚀 Stage 1 验证脚本")
    print("=" * 60)

    results = {
        "项目结构": test_project_structure(),
        "模块导入": test_imports(),
        "配置加载": test_config(),
        "应用创建": test_app_creation(),
        "代码统计": test_file_counts(),
    }

    print("\n" + "=" * 60)
    print("📊 验证结果汇总")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("🎉 所有验证通过！Stage 1 基础设施搭建完成。")
        return 0
    else:
        print("⚠️  部分验证失败，请检查上述错误。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
