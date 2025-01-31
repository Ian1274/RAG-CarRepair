from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from utils.config_loader import load_config

# 配置文件路径和加载
CONFIG_PATH = "config.yaml"  # 配置文件路径
config = load_config(CONFIG_PATH)  # 加载配置文件
mysql_config = config['mysql']  # 获取 MySQL 配置项

# 数据库连接配置
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{mysql_config['user']}:{mysql_config['password']}@{mysql_config['ip']}:{mysql_config['port']}/{mysql_config['database']}"
"""
SQLALCHEMY_DATABASE_URL:
- 使用 pymysql 驱动连接 MySQL 数据库。
- 格式: mysql+pymysql://用户名:密码@主机IP:端口/数据库名
"""

# 创建数据库引擎
# `echo=True` 表示引擎将记录所有语句及其参数列表到日志中（仅供开发和调试使用）。
engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)

# 创建数据库会话
SessionLocal = sessionmaker(
    autocommit=False,  # 禁用自动提交，需手动调用 commit() 提交事务
    autoflush=False,   # 禁用自动刷新，需手动调用 flush() 将更改发送到数据库
    bind=engine         # 绑定到数据库引擎
)
"""
SessionLocal:
- 每个实例是一个数据库会话 (session)。
- 提供与数据库交互的方法，例如查询和更新操作。
- `autocommit=False`：需要显式提交事务。
- `autoflush=False`：需要显式刷新语句。
"""

# 创建基本映射类
Base = declarative_base()
"""
Base:
- 基础映射类，用于声明 ORM 模型类。
- 每个继承 Base 的类将被映射到数据库表中。
"""

