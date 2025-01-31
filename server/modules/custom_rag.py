# 导入必要的模块
import os
import uuid
import torch
import atexit
import logging
import shutil

from dotenv import load_dotenv  # 加载环境变量
from typing import List  # 类型提示
from pymilvus import connections, utility, Collection  # Milvus相关库
from langchain_openai import ChatOpenAI  # OpenAI模型接口
from langchain_ollama import ChatOllama  # Ollama模型接口
from langchain_huggingface import HuggingFaceEmbeddings  # HuggingFace嵌入
from langchain_milvus.vectorstores.milvus import Milvus  # Milvus向量数据库接口
from langchain_community.document_loaders import DirectoryLoader  # 文档加载器
from langchain_text_splitters import RecursiveCharacterTextSplitter  # 文本分割器
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever  # 上下文压缩检索器
from langchain_core.documents import Document  # 文档结构
from langchain_core.prompts import ChatPromptTemplate  # 提示模板
from langchain_core.runnables import RunnablePassthrough  # 可运行对象
from langchain_core.output_parsers import StrOutputParser  # 输出解析器

from mysql import crud, models  # 数据库操作与模式定义
from mysql.database import engine, Base, SessionLocal  # MySQL数据库基础设施
from utils.rag.BCERerank import BCERerank  # 自定义Reranker
from utils.rag.customTextLoader import CustomTextLoader  # 自定义文本加载器

# 设置日志级别，忽略httpx模块的详细日志
logging.getLogger("httpx").setLevel(logging.WARNING)


class CustomRAG:
    """
    自定义RAG（Retrieval Augmented Generation）类，用于知识库构建、文档管理、向量化存储，以及问答功能。
    """

    def __init__(self, config):
        """
        初始化RAG实例，包括模型加载、数据库连接和资源清理注册。

        参数:
        - config (dict): 配置字典，包含模型、向量库、检索等配置项。
        """
        self.config = config  # 加载配置
        self.model_method = self.config['model_method']  # 模型方法
        self.llm = None  # 大语言模型实例
        self.embedding = None  # 嵌入模型实例
        self.is_reranker = False  # 是否启用Reranker（重排序器）
        self.reranker = None  # Reranker模型实例
        self.chains = {}  # 存储知识库链对象
        self.db = None  # 数据库会话对象

        # 加载环境变量（如API密钥等）
        load_dotenv()

        # 初始化模型加载
        self.load_model()

        # 初始化MySQL数据库连接
        self.initializeMySQL()

        # 注册程序退出时的资源清理操作
        atexit.register(self.cleanup)

    def cleanup(self):
        """
        释放GPU资源，清理显存。
        """
        try:
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        except Exception as e:
            print(f"释放显存时出错：{e}")

    def load_model(self):
        """
        加载LLM（大语言模型）和嵌入模型。
        """
        try:
            # 根据配置选择并加载LLM模型
            if self.model_method == "openai":
                model_config = self.config['models']['openai']
                self.llm = ChatOpenAI(
                    temperature=model_config['temperature'],
                    max_tokens=model_config['max_tokens'],
                    presence_penalty=model_config['presence_penalty'],
                    model=model_config['model'],
                    openai_api_key=os.getenv('DEEPSEEK_API_KEY'),
                    openai_api_base=model_config['openai_api_base'],
                )
            elif self.model_method == "ollama":
                model_config = self.config['models']['ollama']
                self.llm = ChatOllama(
                    temperature=model_config['temperature'],
                    num_predict=model_config['num_predict'],
                    repeat_penalty=model_config['repeat_penalty'],
                    model=model_config['model'],
                )
        except Exception as e:
            raise RuntimeError(f"模型加载失败：{e}")

        # 嵌入模型加载
        embedding_config = self.config['embedding']
        self.embedding = HuggingFaceEmbeddings(
            model_name=embedding_config['model_name'],
            model_kwargs=embedding_config['model_kwargs'],
            encode_kwargs=embedding_config['encode_kwargs'],
        )

        # 如果启用了Reranker，加载Reranker模型
        if self.is_reranker:
            reranker_config = self.config['reranker']
            self.reranker = BCERerank(
                model=reranker_config['model'],
                top_n=reranker_config['top_n'],
                device=reranker_config['device']
            )

    def initializeMySQL(self):
        """
        初始化MySQL数据库连接，并自动创建表结构。
        """
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()

    def get_all_knowledge(self):
        """
        获取所有知识库的基本信息。

        返回:
        - list: 知识库信息列表。
        """
        return crud.db_get_all_knowledge(self.db)

    def load_Milvus_store(self, name: str, drop_old: bool):
        """
        加载或创建Milvus向量数据库。

        参数:
        - name (str): 知识库名称。
        - drop_old (bool): 是否清空旧数据。

        返回:
        - Milvus: Milvus向量数据库实例。
        """
        try:
            milvus_config = self.config['milvus']
            return Milvus(
                embedding_function=self.embedding,
                collection_name=name,
                connection_args={"uri": milvus_config['url']},
                drop_old=drop_old,
                auto_id=True,
                enable_dynamic_field=True
            )
        except Exception as e:
            raise RuntimeError(f"Milvus 知识库创建失败：{e}")

    def create_kb(self, brand: str, model: str, knowledge_code: str, knowledge_name: str, remark: str):
        """
        创建新知识库，包括本地目录、数据库记录和Milvus向量库。

        参数:
        - brand (str): 品牌名称。
        - model (str): 车型或模型名称。
        - knowledge_code (str): 知识库代码。
        - knowledge_name (str): 知识库名称。
        - remark (str): 知识库备注信息。
        """
        # 创建本地目录结构
        base_paths = [
            f"../database/kbs/{knowledge_code}",
            f"../database/kbs_md/{knowledge_code}",
            f"../database/kbs_imgs/{knowledge_code}",
            f"../database/kbs_chunks/{knowledge_code}"
        ]
        for path in base_paths:
            if not os.path.exists(path):
                os.makedirs(path)
            else:
                print(f"目录已存在: {path}")
        
        # 在MySQL数据库中记录知识库信息
        unique_id = uuid.uuid4()
        crud.db_create_knowledge(self.db, unique_id, brand, model, knowledge_code, knowledge_name, remark, base_paths)

        # 创建Milvus向量库
        self.load_Milvus_store(knowledge_code, drop_old=True)

    def add_files2kb(self, name: str, md_chunks_dir: str, drop_old: bool):
        """
        将文件添加到指定知识库中，分块后向量化存储。

        参数:
        - name (str): 知识库名称
        - md_chunks_dir (str): 分块后的Markdown文件路径
        - drop_old (bool): 是否清空旧的向量数据
        """
        try:
            # 加载文档数据
            loader_config = self.config['document_loader']
            loader = DirectoryLoader(
                path=md_chunks_dir,
                glob="**/*.md",  # 匹配所有Markdown文件
                loader_cls=CustomTextLoader,  # 自定义文本加载器
                loader_kwargs=loader_config['loader_kwargs'],
                show_progress=loader_config['show_progress'],
                use_multithreading=loader_config['use_multithreading'],
            )
            documents = loader.load()  # 加载文件为文档对象

            # 文本分割
            text_splitter_config = self.config['text_splitter']
            splitter = RecursiveCharacterTextSplitter(
                separators=["。|！|？", "\.\s|\!\s|\?\s", "；|;\s", "，|,\s"],  # 定义分割符
                keep_separator="end",
                is_separator_regex=True,
                chunk_size=text_splitter_config['chunk_size'],  # 每块大小
                chunk_overlap=text_splitter_config['chunk_overlap'],  # 重叠大小
            )
            chunks = splitter.split_documents(documents)  # 分割文档

            # 加载向量库并存储分块数据
            milvus_store = self.load_Milvus_store(name=name, drop_old=drop_old)
            milvus_store.add_documents(chunks)

        except Exception as e:
            raise RuntimeError(f"添加文件到知识库失败：{e}")

    def delete_file(self, name: str, file_name: str):
        """
        删除知识库中的指定文档，包括本地文件和向量库数据。

        参数:
        - name (str): 知识库名称
        - file_name (str): 文档文件名
        """
        try:
            delete_dirs = crud.delete_document_by_code_and_name(self.db, name, file_name)  # 从数据库中查询文件记录

            # 删除本地文件和目录
            for path in delete_dirs:
                if os.path.exists(path):
                    if os.path.isfile(path):
                        os.remove(path)  # 删除文件
                    elif os.path.isdir(path):
                        shutil.rmtree(path)  # 删除文件夹

            # 删除Milvus向量库中的相关数据
            milvus_config = self.config['milvus']
            connections.connect(
                alias="default",
                uri=milvus_config['url'].replace('http', 'tcp'),
            )
            collection = Collection(name)
            filter_expression = f"file == '{file_name}'"
            collection.delete(filter_expression)

        except Exception as e:
            self.db.rollback()  # 回滚数据库事务
            raise RuntimeError(f"删除文档失败：{e}")

    def delete_kb(self, name: str):
        """
        删除整个知识库，包括MySQL记录、本地文件和向量库数据。

        参数:
        - name (str): 知识库名称
        """
        try:
            # 从MySQL中删除知识库记录
            delete_dirs = crud.db_delete_knowledge_by_name(self.db, name)

            # 删除本地文件和目录
            for path in delete_dirs:
                if os.path.exists(path):
                    if os.path.isfile(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)

            # 删除Milvus中的向量库
            milvus_config = self.config['milvus']
            connections.connect(
                alias="default",
                uri=milvus_config['url'].replace('http', 'tcp'),
            )
            if utility.has_collection(name):
                utility.drop_collection(name)

        except Exception as e:
            self.db.rollback()  # 回滚事务
            raise RuntimeError(f"删除知识库失败：{e}")

    def get_retriever(self, name: str):
        """
        创建知识库的检索器。

        参数:
        - name (str): 知识库名称

        返回:
        - 检索器对象
        """
        try:
            # 加载向量存储
            milvus_store = self.load_Milvus_store(name=name, drop_old=False)

            # 基本检索器
            retriever_config = self.config['retrieval']
            retriever = milvus_store.as_retriever(
                search_type=retriever_config['search_type'],
                search_kwargs=retriever_config['search_kwargs'],
            )

            # 如果启用Reranker，构造上下文压缩检索器
            if self.is_reranker:
                return ContextualCompressionRetriever(
                    base_compressor=self.reranker,
                    base_retriever=retriever,
                )
            return retriever

        except Exception as e:
            raise RuntimeError(f"创建检索器失败：{e}")

    def combine_content(self, retrieved_chunks: List[Document]) -> str:
        """
        合并检索到的文档块为完整的字符串。

        参数:
        - retrieved_chunks (List[Document]): 检索到的文档块列表

        返回:
        - str: 合并后的内容
        """
        contents = []
        for chunk in retrieved_chunks:
            source = chunk.metadata['source']  # 获取文档来源
            content = CustomTextLoader(
                file_path=source, autodetect_encoding=True
            ).load()[0].page_content  # 加载文档内容
            contents.append(content)
        return "\n\n".join(contents)  # 合并所有内容

    def qa_initialize(self, name: str):
        """
        初始化问答链，将知识库检索器与语言模型结合。

        参数:
        - name (str): 知识库名称
        """
        try:
            # 加载检索器
            retriever = self.get_retriever(name)

            # 创建提示模板
            system_prompt = self.config['context_prompts']['system_prompt']
            user_prompt = self.config['context_prompts']['user_prompt']
            prompt = ChatPromptTemplate.from_messages(
                [("system", system_prompt), ("human", user_prompt)]
            )

            # 定义问答链
            rag_chain = (
                {"input": lambda x: x["input"], "context": lambda x: x["context"]}
                | prompt
                | self.llm
                | StrOutputParser()
            )

            # 定义检索结果字符串生成过程
            retrieved_str = (lambda x: x["input"]) | retriever | self.combine_content

            # 结合检索和问答链为最终链
            chain = RunnablePassthrough.assign(
                context=retrieved_str
            ).assign(answer=rag_chain)

            # 存储链
            self.chains[name] = chain

        except Exception as e:
            raise RuntimeError(f"问答链初始化失败：{e}")

    def qa(self, name: str):
        """
        启动交互式问答助手。

        参数:
        - name (str): 知识库名称
        """
        try:
            chain = self.chains[name]
            print("知识库问答助手已启动。输入问题进行提问，输入 'q' 退出。")

            while True:
                question = input("问题：")
                if question.lower() == "q":
                    print("程序已退出。")
                    break

                try:
                    for chunk in chain.stream({"input": question}):
                        if 'answer' in chunk and chunk['answer']:
                            print(chunk['answer'], end='', flush=True)
                    print('\n')
                except Exception as e:
                    print(f"处理问题时发生错误：{e}")
        except Exception as e:
            raise RuntimeError(f"启动问答助手失败：{e}")

    async def qa_stream(self, name: str, question: str):
        """
        异步在线问答，逐步返回问答结果。

        参数:
        - name (str): 知识库名称
        - question (str): 用户提问

        返回:
        - 异步生成器，逐步返回问答结果
        """
        try:
            chain = self.chains[name]
            async for chunk in chain.astream({"input": question}):
                yield chunk
        except Exception as e:
            print(f"处理问题时发生错误：{e}")
            yield f"错误: {e}"

