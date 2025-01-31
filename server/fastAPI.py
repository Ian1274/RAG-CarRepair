import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.preprocess import router as preprocess_router  # 导入预处理路由器
from api.rag import router as rag_router  # 导入 RAG 路由器

# 初始化日志设置，降低 httpx 模块的日志级别，避免不必要的日志输出
logging.getLogger("httpx").setLevel(logging.WARNING)

# 初始化 FastAPI 应用实例，设置标题、版本和描述
app = FastAPI(
    title="RAG Q&A System",  # 应用标题
    version="1.0.0",  # 应用版本
    description="API documentation for RAG Analysis",  # 应用描述
)

# 解决跨域问题的中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源的跨域请求
    allow_credentials=True,  # 允许发送凭据
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 包含预处理和 RAG 系统的路由器
app.include_router(preprocess_router)  # 注册预处理路由
app.include_router(rag_router)  # 注册 RAG 系统路由

# 启动应用程序入口点
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastAPI:app", host="127.0.0.1", port=7011, reload=True)  # 启动本地开发服务器
