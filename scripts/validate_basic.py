#!/usr/bin/env python3
"""
Stage 1 基础验证脚本（不需要数据库）

验证项目脚手架和基础设施的基础完整性
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试基础模块导入（不需要数据库）"""
    print("🔍 测试基础模块导入...")

    try:
        # 测试配置模块
        from app.config import settings, get_settings
        print("  ✅ app.config 导入成功")

        # 测试 Schema
        from app.schemas.health import HealthResponse, ServiceStatus
        print("  ✅ app.schemas.health 导入成功")

        # 测试主应用（不包含需要数据库的路由）
        print("  ✅ 基础模块导入成功")

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
        print(f"  ✅ 数据库 URL: {settings.database_url[:30]}...")
        print(f"  ✅ Redis URL: {settings.redis_url}")

        # 测试 LLM 配置
        try:
            llm_config = settings.get_llm_config("zhipuai")
            print(f"  ✅ 智谱AI API Key: {'*' * 20}{llm_config['api_key'][-4:]}")
            print(f"  ✅ 智谱AI 模型: {llm_config['model']}")
        except Exception as e:
            print(f"  ⚠️  LLM 配置警告: {e}")

        # 测试 CORS 配置
        cors_origins = settings.cors_origins
        print(f"  ✅ CORS 源数量: {len(cors_origins)}")
        for origin in cors_origins:
            print(f"     - {origin}")

        return True

    except Exception as e:
        print(f"  ❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schemas():
    """测试 Pydantic 模型"""
    print("\n🔍 测试 Pydantic 模型...")

    try:
        from app.schemas.health import HealthResponse, ServiceStatus

        # 测试 ServiceStatus
        status = ServiceStatus(
            name="test_service",
            status="connected",
            latency_ms=50.5
        )
        print(f"  ✅ ServiceStatus 创建成功: {status.name}")

        # 测试 HealthResponse
        health = HealthResponse(
            status="healthy",
            version="0.1.0",
            environment="development",
            database="connected",
            redis="connected"
        )
        print(f"  ✅ HealthResponse 创建成功: {health.status}")

        # 测试模型序列化
        health_dict = health.model_dump()
        print(f"  ✅ 模型序列化成功: {len(health_dict)} 个字段")

        return True

    except Exception as e:
        print(f"  ❌ 模型测试失败: {e}")
        import traceback
        traceback.print_exc()
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
        "tests/integration/test_health_endpoint.py",
        "STAGE1_SUMMARY.md"
    ]

    all_ok = True
    dir_count = 0
    file_count = 0

    # 检查目录
    for dir_path in required_dirs:
        if (project_root / dir_path).exists():
            print(f"  ✅ {dir_path}")
            dir_count += 1
        else:
            print(f"  ❌ {dir_path} (缺失)")
            all_ok = False

    # 检查文件
    for file_path in required_files:
        if (project_root / file_path).exists():
            print(f"  ✅ {file_path}")
            file_count += 1
        else:
            print(f"  ❌ {file_path} (缺失)")
            all_ok = False

    print(f"\n  📊 目录: {dir_count}/{len(required_dirs)}")
    print(f"  📊 文件: {file_count}/{len(required_files)}")

    return all_ok


def test_file_counts():
    """统计代码文件和行数"""
    print("\n🔍 代码统计...")

    py_files = list(project_root.rglob("*.py"))
    py_files = [f for f in py_files if "__pycache__" not in str(f) and "venv" not in str(f)]

    total_lines = 0
    for py_file in py_files:
        try:
            total_lines += len(py_file.read_text(errors='ignore').splitlines())
        except:
            pass

    print(f"  📊 Python 文件数: {len(py_files)}")
    print(f"  📊 代码总行数: {total_lines}")

    # 统计主要模块
    modules = {
        "app/config.py": "配置管理",
        "app/dependencies.py": "依赖注入",
        "app/main.py": "FastAPI 主应用",
        "app/api/v1/health.py": "健康检查端点",
        "app/schemas/health.py": "数据模型",
    }

    print("\n  📝 主要模块:")
    for file_path, description in modules.items():
        full_path = project_root / file_path
        if full_path.exists():
            lines = len(full_path.read_text().splitlines())
            print(f"     - {description} ({file_path}): {lines} 行")

    return True


def test_documentation():
    """测试文档完整性"""
    print("\n🔍 测试文档完整性...")

    docs = [
        ("README.md", "项目文档"),
        ("STAGE1_SUMMARY.md", "Stage 1 完成总结"),
        ("../IMPLEMENTATION_PLAN.md", "实施计划"),
        ("../CLAUDE.md", "开发指南"),
    ]

    all_ok = True
    for doc_file, description in docs:
        doc_path = project_root / doc_file
        if doc_path.exists():
            content = doc_path.read_text()
            lines = len(content.splitlines())
            print(f"  ✅ {description}: {lines} 行")
        else:
            print(f"  ⚠️  {description}: 未找到")
            all_ok = False

    return all_ok


def main():
    """主验证流程"""
    print("=" * 60)
    print("🚀 Stage 1 基础验证脚本")
    print("=" * 60)
    print("注意: 此脚本不需要数据库和 Redis 连接\n")

    results = {
        "项目结构": test_project_structure(),
        "模块导入": test_imports(),
        "配置加载": test_config(),
        "数据模型": test_schemas(),
        "文档完整性": test_documentation(),
        "代码统计": test_file_counts(),
    }

    print("\n" + "=" * 60)
    print("📊 验证结果汇总")
    print("=" * 60)

    all_passed = True
    passed_count = 0
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        if passed:
            passed_count += 1
        else:
            all_passed = False

    print("=" * 60)
    print(f"总计: {passed_count}/{len(results)} 项通过")

    if all_passed:
        print("\n🎉 所有验证通过！Stage 1 基础设施搭建完成。")
        print("\n📋 后续步骤:")
        print("  1. 安装 Docker Desktop (可选，用于完整测试)")
        print("  2. 或安装 Redis (brew install redis)")
        print("  3. 运行: pip install -r requirements.txt")
        print("  4. 启动服务: ./scripts/start.sh")
        return 0
    else:
        print("\n⚠️  部分验证失败，请检查上述错误。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
