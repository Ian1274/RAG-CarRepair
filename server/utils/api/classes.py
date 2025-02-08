from pydantic import BaseModel


class KnowledgeBaseQueryRequest(BaseModel):
    name: str
    question: str

class KnowledgeBaseVo(BaseModel):
    name: str

class KnowledgeBaseDelleteVo(BaseModel):
    name: str
    file_name: str

class KnowledgeBaseFileVo(BaseModel):
    name: str
    file_name: str
    drop_old: bool

class KnowledgeBaseCreateVo(BaseModel):
    brand: str
    model: str
    knowledge_code: str
    knowledge_name: str
    remark: str

class KnowledgeBaseImageVo(BaseModel):
    view_url: str
    save_url: str
    info: str
    extension: str
