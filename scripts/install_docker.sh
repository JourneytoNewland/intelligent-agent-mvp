#!/bin/bash

# Docker Desktop 安装指南 (macOS Apple Silicon)

echo "🍎 Docker Desktop 安装指南 - macOS Apple Silicon"
echo "="
echo ""
echo "你的系统信息:"
echo "  架构: Apple Silicon (arm64)"
echo "  macOS 版本: $(sw_vers -productVersion)"
echo ""

# 检查 Docker 是否已安装
if command -v docker &> /dev/null; then
    echo "✅ Docker 已安装"
    docker --version
    echo ""
    echo "检查 Docker Desktop 是否运行..."
    if docker info &> /dev/null; then
        echo "✅ Docker 正在运行"
        echo ""
        echo "你可以继续进行服务测试！"
        exit 0
    else
        echo "❌ Docker 已安装但未运行"
        echo ""
        echo "请启动 Docker Desktop:"
        echo "  1. 在应用程序文件夹中找到 Docker"
        echo "  2. 双击启动 Docker Desktop"
        echo "  3. 等待 Docker 图标显示为运行状态"
        exit 1
    fi
else
    echo "❌ Docker 未安装"
    echo ""
    echo "📥 安装步骤:"
    echo ""
    echo "方法 1: 使用 Homebrew (推荐)"
    echo "  brew install --cask docker"
    echo "  或"
    echo "  brew install --cask docker-edge"  # 预览版
    echo ""
    echo "方法 2: 手动下载安装"
    echo "  1. 访问: https://www.docker.com/products/docker-desktop/"
    echo "  2. 点击 'Download for Mac - Apple Chip'"
    echo "  3. 下载 Docker.dmg 文件"
    echo "  4. 打开 Docker.dmg 并将 Docker 拖到应用程序文件夹"
    echo "  5. 从应用程序文件夹启动 Docker Desktop"
    echo ""
    echo "安装后，请运行此脚本再次检查。"
    exit 1
fi
