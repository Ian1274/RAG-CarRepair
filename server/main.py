import os
from datetime import datetime  # 时间日期处理

from modules.custom_rag import CustomRAG  # 导入自定义RAG模块
from modules.data_preprocess import DataPreprocess  # 导入数据预处理模块
from mysql import crud, models  # 数据库操作与模式定义
from mysql.database import engine, Base, SessionLocal  # MySQL数据库基础设施
from utils.config_loader import load_config  # 导入配置加载器


class CarRepairDP(DataPreprocess):
    """
    CarRepair 数据预处理类，继承自 DataPreprocess，添加数据库相关的功能。
    """

    def __init__(self):
        """
        初始化 CR 数据预处理类，调用父类的初始化方法，并初始化数据库连接。
        """
        super().__init__()
        self.db = None
        self.initializeMySQL()  # 初始化数据库连接
        if not self.db:
            raise ConnectionError("MySQL 数据库连接失败，请检查数据库配置或服务状态。")

    def initializeMySQL(self):
        """
        初始化 MySQL 数据库连接，确保数据库表结构存在。
        """
        try:
            Base.metadata.create_all(bind=engine)  # 确保数据库表结构已创建
            self.db = SessionLocal()  # 创建数据库会话
        except Exception as e:
            print(f"数据库初始化失败：{e}")
            self.db = None

    def run(self, name, file_path, file_size):
        """
        对上传的文档进行预处理，生成分块后的 chunk 路径，并将文档信息存储到数据库。

        参数:
        - name (str): 知识库名称（标识符）。
        - file_path (str): 上传文档的路径。
        - file_size (float): 上传文档的大小。

        返回:
        - str: 最终生成的分块文件路径。
        """
        try:
            # 获取上传文件的名称（去掉扩展名）和扩展名
            file_name_without_type = os.path.splitext(os.path.basename(file_path))[0]
            file_type = os.path.splitext(os.path.basename(file_path))[1].replace(".", "")

            # step 01: 对文件进行预处理（转 Markdown 并分块）
            file_dirs_list = self.preprocess(file_path)

            # 获取当前时间作为上传时间
            upload_time = datetime.now()

            # step 02: 将文档信息存储到数据库
            crud.store_document_to_database(self.db, name, file_name_without_type, file_type, file_size, file_dirs_list, upload_time)
            return file_dirs_list[-1]

        except Exception as e:
            self.db.rollback()  # 回滚数据库事务
            print(f"处理文档时发生错误：{e}")
            raise  # 重新抛出异常以便上层捕获


class CarRepairRAG(CustomRAG):
    """
    CarRepairRAG 类继承自 CustomRAG，不添加任何额外功能。

    该类可以用于专门针对汽车维修知识库的定制和扩展。
    目前，它与 CustomRAG 的功能完全一致，但为未来的特定需求保留了扩展的空间。
    """
    pass