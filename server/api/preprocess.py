import os
import asyncio  # 引入 asyncio
import random
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from main import CarRepairDP  # 确保正确导入预处理逻辑类
from utils.api.classes import KnowledgeBaseImageVo

# 定义FastAPI的路由对象，设置前缀和标签
router = APIRouter(
    tags=["Data Preprocessing"],
    responses={404: {"description": "Not found"}},  # 自定义404响应信息
)

class PreprocessingState:
    """
    管理全局预处理状态，用于初始化数据预处理逻辑。
    """
    def __init__(self):
        self.dp_instance = CarRepairDP()  # 实例化预处理逻辑

# 全局状态对象
preprocessing_state = PreprocessingState()

# 从配置文件加载 RAG 系统所需配置
from utils.config_loader import load_config

CONFIG_PATH = "config.yaml"
config = load_config(CONFIG_PATH)

@router.post("/upload", description="向知识库中添加文档")
async def upload_file(
        name: str = Form(...),  # 知识库名称，从表单中获取
        file: UploadFile = File(...),  # 上传的文件，从文件输入获取
):
    """
    上传文件到指定知识库并触发数据预处理任务，等待任务完成后返回结果。

    参数:
    - name: 知识库名称，用户指定
    - file: 用户上传的文件

    返回:
    - 成功消息或失败信息
    """
    try:
        # 创建目标目录（如果不存在）
        # 拼接目标文件路径
        target_dir = os.path.join("..", "database", "kbs", name)  # 使用 os.path.join 构建路径
        os.makedirs(target_dir, exist_ok=True)

        # 拼接目标文件路径
        target_file_path = os.path.join(target_dir, file.filename)

        #判断文件是否重复上传
        if os.path.exists(target_file_path):
            raise HTTPException(status_code=500, detail=f"文件名{file.filename}已存在，请先删除再上传！")

        # 读取文件内容，计算文件大小（单位：MB）
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)  # 转换大小为MB

        # 将文件内容写入目标文件
        with open(target_file_path, "wb") as target_file:
            target_file.write(file_content)

        # 使用 asyncio.run_in_executor 运行同步的预处理逻辑
        loop = asyncio.get_event_loop()  # 获取当前事件循环
        await loop.run_in_executor(
            None,  # 使用默认线程池
            preprocessing_state.dp_instance.run,  # 同步的预处理方法
            name,  # 知识库名称
            target_file_path,  # 上传文件路径
            round(file_size_mb, 2)  # 文件大小，保留两位小数
        )

        # 返回成功响应
        return {
            "message": f"文件 {file.filename} 已成功上传至本地知识库 {name}",
            "file_size_mb": round(file_size_mb, 2),
            "preprocessing_status": "Completed"
        }
    except Exception as e:
        # 捕获异常并返回错误响应
        raise HTTPException(status_code=500, detail=f"添加文件失败：{e}")


