"""
FastAPI 应用入口

配置并启动 FastAPI 应用，包括路由、中间件、异常处理等
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import health, chat, feedback, datasources
import logging

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用

    Returns:
        FastAPI: 配置好的 FastAPI 应用实例
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="基于 FastAPI + LangGraph + MCP + Skills 的智能数据分析平台\n\n核心功能：\n- 智能意图识别（LLM + 规则双模式）\n- 参数提取（Function Calling + Few-shot）\n- 并行 Skill 执行\n- 用户反馈机制\n- 多数据源支持（Database, HTTP, Excel, API）",
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
    app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])
    app.include_router(datasources.router, prefix="/api/v1/datasources", tags=["Datasources"])

    # 启动事件
    @app.on_event("startup")
    async def startup_event():
        """应用启动时执行的初始化逻辑"""
        logger.info(f"启动 {settings.app_name} v{settings.app_version}")
        logger.info(f"环境: {settings.environment}")
        logger.info(f"调试模式: {settings.debug}")

    # 关闭事件
    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭时执行的清理逻辑"""
        logger.info(f"关闭 {settings.app_name}")

    # 根路径
    @app.get("/")
    async def root():
        """根路径，返回 API 信息"""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health"
        }

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
