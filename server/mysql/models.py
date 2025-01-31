from sqlalchemy.dialects.mysql import DECIMAL
from sqlalchemy import Boolean, Column, Integer, String, DateTime, JSON, Float
from mysql.database import Base

class KnowledgeBase(Base):
    """
    定义数据库表 'knowledge' 的 ORM 模型。

    表名：knowledge
    知识库表。
    """

    __tablename__ = "knowledge"  # 数据库表名称

    id = Column(Integer, primary_key=True, index=True)
    """
    主键 ID：
    - 数据类型：Integer
    - 属性：主键，索引
    """

    brand = Column(String(500))
    """
    知识库描述：
    - 数据类型：String，长度 999
    """

    model = Column(String(500))
    """
    知识库描述：
    - 数据类型：String，长度 999
    """

    knowledge_code = Column(String(50), unique=True, index=True)
    """
    知识库代码：
    - 数据类型：String，长度 50
    - 属性：唯一约束，索引
    """

    knowledge_name = Column(String(100))
    """
    知识库名称：
    - 数据类型：String，长度 50
    """

    delete_dirs = Column(JSON, nullable=True)  # JSON 类型字段
    """
    删除目录路径：
    - 数据类型：JSON
    - 属性：可为空
    - 用途：存储与知识库相关的文件路径列表
    - 示例：['../database/kbs/yyx_test', '../database/kbs_md/yyx_test']
    """

    remark = Column(String(500))
    """
    知识库描述：
    - 数据类型：String，长度 999
    """

    create_time = Column(DateTime)
    """
    创建日期：
    - 数据类型：DateTime
    """

class KnowledgeFile(Base):
    """
    数据库表 'knowledge_file' 的 ORM 模型。

    表名：knowledge_file
    用途：存储知识库中文档的信息
    """

    __tablename__ = "knowledge_file"  # 数据库表名称

    id = Column(Integer, primary_key=True, index=True)
    """
    主键 ID：
    - 数据类型：Integer
    - 属性：主键，索引
    - 用途：唯一标识每条文档记录
    """

    knowledge_code = Column(String(50), index=True)
    """
    知识库名称：
    - 数据类型：String
    - 最大长度：50
    - 属性：索引
    - 用途：存储该文档所属的知识库名称
    """

    file_name = Column(String(255))
    """
    文档名称：
    - 数据类型：String
    - 最大长度：255
    - 用途：存储文档的文件名称
    """

    file_type = Column(String(50))
    """
    文件类型：
    - 数据类型：String，长度 50
    """

    file_size = Column(DECIMAL(10, 2))  # 使用 DECIMAL 强制两位小数
    """
    文档大小：
    - 数据类型：Float
    - 精度：保留两位小数
    """

    delete_dirs = Column(JSON, nullable=False)
    """
    文档路径列表：
    - 数据类型：JSON
    - 属性：非空
    - 用途：存储与文档相关的文件路径列表
    - 示例：['/path/to/file1.docx', '/path/to/file2.docx']
    """

    upload_time = Column(DateTime)
    """
    上传时间：
    - 数据类型：DateTime
    - 用途：记录文档上传的时间
    """

class AskAnswer(Base):
    """
    数据库表 'k_ask_answer' 的 ORM 模型。

    表名：k_ask_answer
    用途：经验库信息
    """

    __tablename__ = "k_ask_answer"  # 数据库表名称

    id = Column(Integer, primary_key=True, index=True)
    """
    主键 ID：
    - 数据类型：Integer
    - 属性：主键，索引
    - 用途：唯一标识每条文档记录
    """

    ask = Column(String(5000))
    """
    问题关键字：
    - 数据类型：String
    - 最大长度：5000
    """

    answer_name = Column(String(100))
    """
    维修标题：
    - 数据类型：String
    - 最大长度：100
    """

    answer = Column(String(5000))
    """
    维修信息：
    - 数据类型：String
    - 最大长度：5000
    """

    table_name = Column(String(100))
    """
    表格名称：
    - 数据类型：String
    - 最大长度：100
    """

    table_html = Column(String(5000))
    """
    表格：
    - 数据类型：String
    - 最大长度：5000
    """

    images_name = Column(String(100))
    """
    图片名称：
    - 数据类型：String
    - 最大长度：100
    """

    images = Column(String(200))
    """
    图片：
    - 数据类型：String
    - 最大长度：200
    """

    video_name = Column(String(200))
    """
    视频名称：
    - 数据类型：String
    - 最大长度：200
    """

    video = Column(String(200))
    """
    视频：
    - 数据类型：String
    - 最大长度：200
    """

    link_name = Column(String(100))
    """
    链接名称：
    - 数据类型：String
    - 最大长度：100
    """

    link = Column(String(100))
    """
    链接：
    - 数据类型：String
    - 最大长度：100
    """

    flow_name = Column(String(100))
    """
    流程名称：
    - 数据类型：String
    - 最大长度：100
    """

    flow = Column(String(5000))
    """
    流程：
    - 数据类型：String
    - 最大长度：5000
    """

    milvus_id = Column(Integer)
    """
    向量数据库id：
    - 数据类型：Integer
    """

    state = Column(Integer)
    """
    状态(0生效,1失效)：
    - 数据类型：Integer
    """

    create_time = Column(DateTime)
    """
    创建时间：
    - 数据类型：DateTime
    """
