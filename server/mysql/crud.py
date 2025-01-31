
import logging

from typing import List, Dict
from collections import defaultdict
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import outerjoin
from sqlalchemy.orm import Session, joinedload

from mysql import models


# 配置日志
logger = logging.getLogger("knowledge_base")
logger.setLevel(logging.ERROR)


def format_datetime(dt: datetime) -> str:
    """格式化 datetime 对象为字符串"""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def to_dict(obj) -> Dict:
    """将 SQLAlchemy 对象转换为字典"""
    return {col.name: getattr(obj, col.name) for col in obj.__table__.columns}


# 查询知识库信息
def db_get_all_knowledge(db: Session) -> List[Dict]:
    """
    查询并返回知识库的所有信息，包括 KnowledgeBase 和 KnowledgeFile 中的所有字段。
    """
    try:
        # 查询 KnowledgeBase 表的所有字段
        db.commit()  # 确保事务提交
        knowledge_items = db.query(models.KnowledgeBase).all()

        # 获取所有 KnowledgeFile 关联字段
        knowledge_codes = [item.knowledge_code for item in knowledge_items]

        docs_query = db.query(models.KnowledgeFile).filter(
            models.KnowledgeFile.knowledge_code.in_(knowledge_codes)
        ).all()

        # 将文档信息按 knowledge_code 分组
        docs_dict = defaultdict(list)
        for doc in docs_query:
            docs_dict[doc.knowledge_code].append({
                "id": doc.id,
                "knowledge_code": doc.knowledge_code,
                "file_name": doc.file_name,
                "file_type": doc.file_type,
                "file_size": float(doc.file_size) if doc.file_size else None,
                "delete_dirs": doc.delete_dirs,
                "upload_time": format_datetime(doc.upload_time),
            })

        # 整理返回结果
        result = []
        for item in knowledge_items:
            result.append({
                **to_dict(item),
                "create_time": format_datetime(item.create_time),
                "documents": docs_dict.get(item.knowledge_code, []),
            })

        return result
    except Exception as e:
        db.rollback()
        logger.error(f"Error querying knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to query knowledge base.")


# 新建知识库（根据名称和描述）
def db_create_knowledge(
    db: Session, 
    id: int, 
    brand: str, 
    model: str, 
    knowledge_code: str, 
    knowledge_name: str, 
    remark: str, 
    delete_dirs: List[str]
) -> models.KnowledgeBase:
    """
    新建知识库，根据输入的知识库信息添加记录。

    参数：
    - db (Session): 数据库会话。
    - id (int): 知识库主键 ID。
    - brand (str): 品牌信息。
    - model (str): 型号信息。
    - knowledge_code (str): 知识库代码。
    - knowledge_name (str): 知识库名称。
    - remark (str): 备注信息。
    - delete_dirs (List[str]): 需要删除的路径列表。

    返回：
    - models.KnowledgeBase: 新建的知识库对象。
    
    抛出：
    - HTTPException: 如果知识库代码或 ID 已存在，抛出 409 错误。
    """
    # 检查知识库代码是否已存在
    existing_item = db.query(models.KnowledgeBase).filter(models.KnowledgeBase.knowledge_code == knowledge_code).first()
    if existing_item:
        raise HTTPException(status_code=409, detail=f"知识库代码 {knowledge_code} 已经存在！")

    # 检查 ID 是否已存在
    existing_id = db.query(models.KnowledgeBase).filter(models.KnowledgeBase.id == id).first()
    if existing_id:
        raise HTTPException(status_code=409, detail=f"知识库 ID {id} 已经存在！")

    # 获取当前时间（使用 UTC 时间）
    now = datetime.utcnow()

    # 校验 delete_dirs 是否为列表
    if not isinstance(delete_dirs, list):
        raise HTTPException(status_code=400, detail="delete_dirs 必须是列表格式")

    # 创建新的知识库对象
    db_knowledge = models.KnowledgeBase(
        id=id,
        brand=brand,
        model=model,
        knowledge_code=knowledge_code,
        knowledge_name=knowledge_name,
        remark=remark,
        create_time=now,
        delete_dirs=delete_dirs
    )
    
    # 添加到数据库并提交
    try:
        db.add(db_knowledge)
        db.commit()
        db.refresh(db_knowledge)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建知识库失败：{str(e)}")

    return db_knowledge


# 将文档信息存储到数据库
def store_document_to_database(
    db: Session, knowledge_code: str, file_name: str, file_type: str, file_size: float, file_dirs_list: list, upload_time: datetime
):
    """
    将文档信息存储到数据库。

    参数:
    - knowledge_code (str): 知识库标识符。
    - file_name (str): 文档文件名称（去掉扩展名）。
    - file_type (str): 文档文件类型（扩展名）。
    - file_size (float): 文档文件大小。
    - file_dirs_list (list): 文件生成的路径列表。
    - upload_time (datetime): 上传时间。

    返回:
    - None

    抛出:
    - HTTPException: 如果已经存在相同的文档信息。
    """
    try:
        # 查询是否已经存在相同的文档记录
        existing_file = (
            db.query(models.KnowledgeFile)
            .filter(
                models.KnowledgeFile.knowledge_code == knowledge_code,
                models.KnowledgeFile.file_name == file_name,
                models.KnowledgeFile.file_type == file_type,
            )
            .first()
        )

        if existing_file:
            raise HTTPException(
                status_code=400, detail=f"文件 '{file_name}' (类型: {file_type}) 已存在于知识库 '{knowledge_code}' 中，请检查。"
            )

        # 创建新的 KnowledgeFile 实例
        new_file = models.KnowledgeFile(
            knowledge_code=knowledge_code,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            delete_dirs=file_dirs_list,
            upload_time=upload_time,
        )
        db.add(new_file)
        db.commit()  # 提交事务

        # 刷新会话
        db.refresh(new_file)
    except Exception as e:
        db.rollback()
        logger.error(f"Error storing document to database: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to store document.")


def delete_document_by_code_and_name(db: Session, knowledge_code: str, file_name: str) -> dict:
    """
    删除 KnowledgeFile 表中与指定知识库代码和文件名关联的文档记录，并返回其 delete_dirs。

    参数：
    - db (Session): 数据库会话。
    - knowledge_code (str): 知识库代码。
    - file_name (str): 文档文件名。

    返回：
    - dict: 包含删除文档数据的 delete_dirs。

    抛出：
    - HTTPException: 如果记录不存在或删除失败。
    """
    try:
        # 查询指定的文档记录
        document = (
            db.query(models.KnowledgeFile)
            .filter(
                models.KnowledgeFile.knowledge_code == knowledge_code,
                models.KnowledgeFile.file_name == file_name,
            )
            .first()
        )

        if document is None:
            raise HTTPException(
                status_code=404,
                detail=f"Document with knowledge_code {knowledge_code} and file_name {file_name} does not exist",
            )

        # 提取 delete_dirs
        delete_dirs = document.delete_dirs

        # 删除文档记录
        db.delete(document)
        db.commit()

        # 返回 delete_dirs
        return delete_dirs

    except Exception as e:
        db.rollback()
        logger.error(
            f"Error deleting KnowledgeFile record for knowledge_code {knowledge_code} and file_name {file_name}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting KnowledgeFile record: {str(e)}",
        )


def db_delete_knowledge_by_name(db: Session, knowledge_code: str):
    """
    根据输入的知识库代码删除其所有信息，包括关联的文档记录。

    参数：
    - db (Session): 数据库会话。
    - knowledge_code (str): 知识库代码。

    返回：
    - 成功删除消息。

    抛出：
    - HTTPException: 如果知识库不存在，抛出 404 错误。
    """
    try:
        # 检查知识库是否存在
        item = db.query(models.KnowledgeBase).filter(models.KnowledgeBase.knowledge_code == knowledge_code).first()
        if item is None:
            raise HTTPException(status_code=404, detail=f"KnowledgeBase {knowledge_code} does not exist")
        
        # 获取知识库的 delete_dirs
        delete_dirs = item.delete_dirs

        # 删除关联文档
        db.query(models.KnowledgeFile).filter(models.KnowledgeFile.knowledge_code == knowledge_code).delete()

        # 删除知识库记录
        db.delete(item)
        db.commit()

        return delete_dirs
    except Exception as e:
        db.rollback()  # 回滚事务
        logger.error(f"Error deleting KnowledgeBase {knowledge_code}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting KnowledgeBase: {str(e)}")
    

#判断知识库文档是否存在
def chek_document_exist(db: Session, upload_file_name: str):
    # 检查知识库是否存在
    item = db.query(models.KnowledgeFile).filter(models.KnowledgeFile.file_name == upload_file_name).first()
    if item is not None:
        raise Exception(status_code=500, message=f"当前知识库已存在文件名： {upload_file_name} ")


#根据id获取经验库记录信息
def get_experience_model(db: Session, id: int):
    # 检查知识库是否存在
    item = db.query(models.AskAnswer).filter(models.AskAnswer.id == id).first()
    return item