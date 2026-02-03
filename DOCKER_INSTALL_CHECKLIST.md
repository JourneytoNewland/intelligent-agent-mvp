# Docker 安装清单

## 📋 快速安装步骤

### 1️⃣ 下载 Docker Desktop

**直接下载链接** (适用于你的 Apple Silicon Mac):
```
https://desktop.docker.com/mac/main/arm64/Docker.dmg
```

或者访问官网:
```
https://www.docker.com/products/docker-desktop/
```

---

### 2️⃣ 安装步骤

1. **打开下载的 Docker.dmg**

2. **将 Docker 图标拖到 Applications 文件夹**

3. **从 Applications 启动 Docker Desktop**
   - 如果提示安全问题，右键点击 → 选择"打开"

4. **等待初始化完成**
   - 顶部菜单栏会出现鲸鱼图标
   - 等待图标停止闪烁（约 1-2 分钟）

---

### 3️⃣ 验证安装

**安装完成后，运行验证脚本**:

```bash
cd intelligent-agent-mvp
./scripts/verify_docker.sh
```

预期输出:
```
✅ Docker 命令已找到
Docker version 27.x.x, build xxxxx

✅ Docker 正在运行

✅ Docker Compose 可用
Docker Compose version v2.x.x

🎉 Docker 安装验证通过！
```

---

## 🚀 安装后的下一步

安装成功后，启动所有服务:

```bash
# 一键启动所有服务
./scripts/start.sh

# 查看服务状态
docker compose -f docker/docker-compose.yml ps

# 查看日志
docker compose -f docker/docker-compose.yml logs -f
```

---

## 📚 相关文档

- **详细安装指南**: [DOCKER_INSTALL_GUIDE.md](DOCKER_INSTALL_GUIDE.md)
- **Stage 1 验证报告**: [STAGE1_VALIDATION_REPORT.md](STAGE1_VALIDATION_REPORT.md)
- **项目 README**: [README.md](README.md)

---

## ⏱️ 预计时间

- 下载 Docker.dmg: 约 5-10 分钟（取决于网络速度）
- 安装: 约 2-3 分钟
- 初始化: 约 1-2 分钟
- **总计**: 约 10-15 分钟

---

## ❓ 遇到问题?

查看详细安装指南:
```bash
cat DOCKER_INSTALL_GUIDE.md
```

或访问 Docker 官方文档:
```
https://docs.docker.com/desktop/install/mac-install/
```

---

**准备好后，让我们继续！** 🎉
