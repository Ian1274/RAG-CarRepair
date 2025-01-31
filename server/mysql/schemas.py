from pydantic import BaseModel

class KnowledgeBase(BaseModel):
    """
    用于描述知识库相关信息的数据模型。

    属性：
    - name (str): 知识库的唯一编码。
    - description (str): 知识库的描述。
    """
    name: str 
    description: str  

    class Config:
    # 启用从 ORM 对象加载数据的支持
        from_attributes = True