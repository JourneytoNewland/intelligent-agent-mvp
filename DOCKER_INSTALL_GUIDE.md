# Docker Desktop 手动安装指南

## 系统信息
- **架构**: Apple Silicon (M1/M2/M3)
- **系统**: macOS 26.0 (Sequoia)

---

## 📥 安装步骤

### 步骤 1: 下载 Docker Desktop

**方法 A: 直接下载链接**
```
https://desktop.docker.com/mac/main/arm64/Docker.dmg
```

**方法 B: 官网下载**
1. 访问: https://www.docker.com/products/docker-desktop/
2. 看到 "Download for Mac - Apple Chip" 按钮
3. 点击下载 Docker.dmg (约 500MB)

---

### 步骤 2: 安装 Docker Desktop

1. **打开下载的 Docker.dmg 文件**
   - 通常在 `~/Downloads/` 文件夹

2. **将 Docker 拖到 Applications**
   - 会看到 Docker 图标和 Applications 文件夹
   - 拖拽 Docker 图标到 Applications 文件夹

3. **首次启动 Docker Desktop**
   - 从 Applications 文件夹打开 Docker
   - 如果提示"无法打开，因为来自身份不明的开发者"
   - 右键点击 Docker → 选择"打开" → 点击"打开"

4. **等待初始化**
   - Docker Desktop 会自动初始化
   - 顶部菜单栏会出现 Docker 图标（鲸鱼图标）
   - 等待图标停止闪烁（变为静止状态）
   - 通常需要 1-2 分钟

---

### 步骤 3: 验证安装

打开终端，运行以下命令：

```bash
# 检查 Docker 版本
docker --version

# 检查 Docker 是否运行
docker info

# 检查 Docker Compose
docker compose version
```

预期输出：
```
Docker version 27.x.x, build xxxxx
...
Docker Compose version v2.x.x
```

---

### 步骤 4: 配置 Docker (可选但推荐)

1. **打开 Docker Desktop 设置**
   - 点击顶部菜单栏的 Docker 图标
   - 选择 "Settings..."

2. **推荐配置**:
   - **Resources → Advanced**:
     - Memory: 4 GB (最小 2 GB)
     - CPUs: 2 (最小 1)
   - **Resources → File Sharing**:
     - 添加项目目录: `/Users/你的用户名/Downloads/playDemo/AntigravityDemo/BDMVP/intelligent-agent-mvp`

3. **点击 "Apply & Restart"**

---

## 🚀 安装后的下一步

安装完成后，运行我们的验证脚本：

```bash
cd intelligent-agent-mvp
./scripts/install_docker.sh
```

如果显示 "✅ Docker 正在运行"，就可以继续下一步了！

---

## 📝 常见问题

### Q1: Docker Desktop 无法启动
**A**: 确保系统权限允许：
- 系统设置 → 隐私与安全性 → 开发者
- 查看 "Docker Inc." 是否被允许

### Q2: docker info 报错 "Cannot connect to the Docker daemon"
**A**: Docker Desktop 未完全启动，等待 1-2 分钟后重试

### Q3: Docker 占用太多资源
**A**: 在 Docker Desktop 设置中限制资源使用（Memory, CPUs）

### Q4: 卸载 Docker Desktop
**A**:
```bash
# 1. 退出 Docker Desktop
# 2. 删除应用
rm -rf /Applications/Docker.app
# 3. 清理数据（可选）
rm -rf ~/Library/Containers/com.docker.docker
rm -rf ~/.docker
```

---

## 📞 需要帮助？

如果安装过程中遇到问题：
1. 查看官方文档: https://docs.docker.com/desktop/install/mac-install/
2. 检查系统要求: macOS 11 或更高版本
3. 确保有足够的磁盘空间（至少 4 GB）

---

**准备好后，让我们继续测试！** 🚀
