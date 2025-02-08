import os
import asyncio
import logging
import json
from pydantic import BaseModel
import requests
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from main import CarRepairRAG  # 导入 RAG 系统主类
from mysql import crud
from mysql.database import SessionLocal
from utils.api.classes import KnowledgeBaseQueryRequest, KnowledgeBaseVo, KnowledgeBaseDelleteVo, KnowledgeBaseCreateVo, KnowledgeBaseFileVo
from mysql import models

# 定义 API 路由对象，指定前缀和标签
router = APIRouter(
    tags=["RAG System"],
    responses={404: {"description": "Not found"}},  # 自定义 404 错误响应
)

class RAGState:
    """
    维护 RAG 系统的全局状态。
    """
    def __init__(self, config):
        self.rag_instance = CarRepairRAG(config)  # 初始化 RAG 系统实例


# 从配置文件加载 RAG 系统所需配置
from utils.config_loader import load_config

CONFIG_PATH = "config.yaml"
config = load_config(CONFIG_PATH)

# 初始化 RAG 系统的全局状态
rag_state = RAGState(config)

# 提供数据库会话
def get_db():
    db = rag_state.rag_instance.db
    try:
        yield db
    finally:
        db.close()

# 获取知识库信息接口
@router.get("/get_all_knowledge", description="获取所有知识库信息")
async def get_all_knowledge():
    """
    获取所有知识库的信息。

    返回:
    - 知识库信息列表
    """
    try:
        return rag_state.rag_instance.get_all_knowledge()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识库信息失败：{e}")

# 创建知识库接口
@router.post("/create_knowledge", description="创建新的知识库")
async def create_knowledge(request: KnowledgeBaseCreateVo):
    """
    创建新的知识库。

    参数:
    - request: 请求体，包含知识库创建所需信息

    返回:
    - 创建成功或失败的消息
    """
    try:
        rag_state.rag_instance.create_kb(
            request.brand, 
            request.model, 
            request.knowledge_code,
            request.knowledge_name, 
            request.remark
        )
        return {"message": f"知识库 {request.knowledge_code} 创建成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建知识库失败：{e}")

# 添加文件到知识库
@router.post("/add_files", description="将文件添加到知识库中，分块后向量化存储")
async def add_files_to_kb(request:  KnowledgeBaseFileVo):
    """
    将文件添加到指定知识库中，完成分块和向量化存储。

    参数:
    - name: 知识库名称
    - file_name: 上传文件名字
    - drop_old: 是否删除旧的向量化数据

    返回:
    - 成功或失败的消息
    """
    target_dir = os.path.join("..", "database", "kbs_chunks", request.name)
    os.makedirs(target_dir, exist_ok=True)

    md_chunks_dir = os.path.join(target_dir, request.file_name)

    if not os.path.exists(md_chunks_dir):
        raise HTTPException(status_code=400, detail="目标分块目录不存在，请先上传文件并进行预处理。")

    try:
        rag_state.rag_instance.add_files2kb(request.name, md_chunks_dir, request.drop_old)
        return {"message": f"文件已成功添加到知识库 {request.name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加文件到知识库失败：{e}")

# 删除指定文档
@router.post("/delete_file", description="删除知识库中指定文档")
async def delete_file(request: KnowledgeBaseDelleteVo):
    """
    删除知识库中的指定文档。

    参数:
    - request: 请求体，包含知识库和文档的名称

    返回:
    - 成功或失败的消息
    """
    try:
        rag_state.rag_instance.delete_file(request.name, 
                                           request.file_name)
        return {"message": f"文档 {request.file_name} 已从知识库 {request.name} 删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败：{e}")

# 删除整个知识库
@router.post("/delete_knowledge", description="删除知识库")
async def delete_knowledge(request: KnowledgeBaseVo):
    """
    删除整个知识库。

    参数:
    - request: 请求体，包含知识库的名称

    返回:
    - 成功或失败的消息
    """
    try:
        rag_state.rag_instance.delete_kb(request.name)
        return {"message": f"知识库 {request.name} 已成功删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除知识库失败：{e}")

# 选择知识库用于问答
@router.post("/select_knowledge", description="选择知识库用于问答")
async def select_knowledge(request: KnowledgeBaseVo):
    """
    选择知识库用于问答。

    参数:
    - request: 请求体，包含知识库名称

    返回:
    - 成功或失败的消息
    """
    try:
        rag_state.rag_instance.qa_initialize(request.name)
        return {"message": f"知识库 {request.name} 问答链已生成"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"选择知识库失败：{e}")

@router.post("/knowledge_base_chat", description="基于选定知识库进行问答")
async def knowledge_base_chat(request: KnowledgeBaseQueryRequest, db: Session = Depends(get_db)):
    """
    知识库问答接口，基于流式响应返回问答结果。

    参数:
    - request: 请求体，包含知识库名称和用户提问

    返回:
    - 流式响应，返回问答结果
    """
    try:
        async def response_generator():
            name = request.name
            question = request.question
   
            try:
                async for chunk in rag_state.rag_instance.qa_stream(name, question):
                    if isinstance(chunk, dict) and 'answer' in chunk and chunk['answer']:
                        # print(chunk)
                        yield chunk['answer']
                        # await asyncio.sleep(0.03)
            except Exception as e:
                yield f"发生错误: {e}"

        return StreamingResponse(response_generator(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询知识库时发生错误: {e}")

IMAGE_FOLDER = "../database/temp_imgs"
@router.get("/image/{image_name}")
async def get_image(image_name: str):
    image_path = os.path.join(IMAGE_FOLDER, image_name)
    
    # 检查图片是否存在
    if os.path.exists(image_path):
        return FileResponse(image_path)
    return {"error": "Image not found"}
