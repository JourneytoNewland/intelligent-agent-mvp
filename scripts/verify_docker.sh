#!/bin/bash

# Docker 安装验证脚本

echo "🐳 Docker 安装验证"
echo "="
echo ""

# 检查 Docker 命令是否可用
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 命令未找到"
    echo ""
    echo "请确保 Docker Desktop 已正确安装:"
    echo "  1. 检查 Applications 文件夹中是否有 Docker"
    echo "  2. 启动 Docker Desktop"
    echo "  3. 等待顶部菜单栏出现 Docker 图标"
    echo ""
    echo "详细安装指南: cat DOCKER_INSTALL_GUIDE.md"
    exit 1
fi

echo "✅ Docker 命令已找到"
docker --version
echo ""

# 检查 Docker 是否运行
echo "🔍 检查 Docker 运行状态..."
if docker info &> /dev/null; then
    echo "✅ Docker 正在运行"
    echo ""

    # 显示 Docker 信息
    echo "📊 Docker 系统信息:"
    echo "  - 操作系统: $(docker info --format '{{.OperatingSystem}}')"
    echo "  - 架构: $(docker info --format '{{.Architecture}}')"
    echo "  - CPU 数: $(docker info --format '{{.NCPU}}')"
    echo "  - 内存: $(docker info --format '{{.MemTotal}}' | awk '{printf "%.2f GB", $1/1073741824}')"
    echo ""

    # 检查 Docker Compose
    echo "🔍 检查 Docker Compose..."
    if docker compose version &> /dev/null; then
        echo "✅ Docker Compose 可用"
        docker compose version
        echo ""
    else
        echo "❌ Docker Compose 未找到"
        echo "Docker Desktop 应该包含 Docker Compose，请重新安装"
        exit 1
    fi

    echo "="
    echo "🎉 Docker 安装验证通过！"
    echo ""
    echo "📋 下一步:"
    echo "  1. 启动项目服务:"
    echo "     ./scripts/start.sh"
    echo ""
    echo "  2. 或单独启动 Docker 服务:"
    echo "     docker compose -f docker/docker-compose.yml up -d"
    echo ""
    exit 0

else
    echo "❌ Docker 未运行"
    echo ""
    echo "请执行以下操作:"
    echo "  1. 从 Applications 文件夹打开 Docker Desktop"
    echo "  2. 等待 Docker 图标显示在顶部菜单栏"
    echo "  3. 等待图标停止闪烁（表示完全启动）"
    echo "  4. 重新运行此脚本"
    echo ""
    echo "或者查看详细指南:"
    echo "  cat DOCKER_INSTALL_GUIDE.md"
    exit 1
fi
