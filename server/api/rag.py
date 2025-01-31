import os
import asyncio
import logging
import json
from pydantic import BaseModel
import requests
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from main import CarRepairRAG  # 导入 RAG 系统主类
from mysql import crud
from mysql.database import SessionLocal
from utils.api.classes import KnowledgeBaseQueryRequest, KnowledgeBaseVo, KnowledgeBaseDelleteVo, KnowledgeBaseCreateVo, KnowledgeBaseFileVo
from mysql import models

# 定义 API 路由对象，指定前缀和标签
router = APIRouter(
    prefix="/chat",
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
    target_dir = f"../database/kbs_chunks/{request.name}"
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

# 知识库问答接口
from fastapi.responses import StreamingResponse
from fastapi import HTTPException

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

            # 图片识别
            image_question = ""
            if request.img:
                image_question = get_image_recognition(request.img)
            if image_question:
                # 图像识别的结果拼接到用户问题
                question = f"用户的问题是:{image_question},{question}"

            # 主体流式回答内容
            async for chunk in rag_state.rag_instance.qa_stream(name, question):
                if isinstance(chunk, dict) and 'answer' in chunk and chunk['answer']:
                    yield chunk['answer']
                    # 调整流式传输的速度，这里设置为每个 chunk 间隔 0.2 秒
                    await asyncio.sleep(0.03)

            # 相似度查询经验库信息
            stream_text, no_stream_text = get_experience_info(question, db)
            #经验库文字信息流式输出
            if stream_text:
                for char in stream_text:
                    yield char
                    await asyncio.sleep(0.03)

            #流式输出和不流式输出分界线
            yield "\n no-stream \n"

            # 经验库多媒休信息不流式输出
            if no_stream_text:
               yield no_stream_text

            # 打印结束标志
            yield "\n all_done"

        return StreamingResponse(response_generator(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询知识库时发生错误: {e}")



def get_image_recognition(img_url:str):
    """
    用户上传图片识别

    参数:
    - img_url: 上传图片地址

    返回:
    - str: 图片识别结果
    """
    try:
        # 远程服务器的上传接口URL
        http = config['http']['images_detect']
        upload_url = f'{http}/detect/'

        # 打开图片文件，准备上传
        with open(img_url, 'rb') as file:
            # 构建请求的multipart/form-data数据
            files = {'file': (img_url, file, 'image/jpeg')}  # 假设图片是JPEG格式

            # 发送POST请求，上传文件，识别图片
            response = requests.post(upload_url, files=files)

            # 检查响应状态
            if response.status_code == 200:
                print('文件上传成功')
                # 使用 json.loads() 方法将 JSON 字符串转换为 Python 对象
                data = json.loads(response.text)
                # 通过键名 "detected_classes" 访问列表
                return '，'.join(data["detected_classes"])
                print(result)  # 打印服务器返回的信息
            else:
                print('文件上传失败')
                print(response.text)  # 打印错误信息
        return ""
    except requests.RequestException as e:
        # 处理请求异常，打印错误信息
        print(f"Error occurred: {e}")
        return None

def get_experience_info(question:str,db: Session):
    """
    相似度查询经验库，组装经验库信息

    返回:
    - str: 经验库信息
    """
    try:
        #定义返回的信息变量
        stream_text=""
        #定义返回的信息变量
        no_stream_text=""
        # 请求的JSON数据
        data = {
            'raw_content': question
        }
        # 将字典转换为JSON字符串
        json_data = json.dumps(data)
        # 设置请求头
        headers = {
            'Content-Type': 'application/json; charset=UTF-8'
        }
        # 相似度查询URL
        http=config['http']['similarity_search']
        url = f'{http}/search'
        # 发送POST请求
        response = requests.post(url, headers=headers, data=json_data)
        # 将JSON字符串解析为Python字典
        data = json.loads(response.text)
        # 检查results列表是否不为空
        if len(data['results']) > 0:
            # 访问results列表，并取出第一条数据
            first_item = data['results'][0][0]
            # 提取distance字段
            distance = first_item['distance']
            if distance>0.90:
                # 提取entity字段中的mysqlid
                mysqlid = first_item['entity']['mysqlid']
                item=crud.get_experience_model(db,int(mysqlid))
                if item:
                    # 拼接经验库信息，最后输出回答结束标志
                    stream_text,no_stream_text=assemble_experience_info(item)
        return stream_text,no_stream_text
    except requests.RequestException as e:
        # 处理请求异常，打印错误信息
        print(f"Error occurred: {e}")
        return None

def assemble_experience_info(item: models.AskAnswer):
    """
    组装经验库信息

    返回:
    - str: 经验库信息
    """

    #定义经验库信息列表，流式输出
    stream_strings = []
    stream_strings.append("\n")

    #拼接文字html
    if item.answer:
        stream_strings.append(item.answer_name+"\n")
        stream_strings.append(item.answer+"\n")

    # 拼接链接html
    if item.link:
        stream_strings.append("<a href=\"" + item.link + "\" target=\"_blank\">" + item.link_name + "，点击查看详情</a>\n")

    #定义经验库表格文本，流式输出
    no_stream_strings = []
    no_stream_strings.append("<div style=\"width: 85%;margin: 10px 0px; display:flex;gap:15px; flex-direction: column;\">")
    # 拼接图片html
    if item.images:
        no_stream_strings.append("<div><h4>" + item.images_name + "</h4></div>")
        no_stream_strings.append("<div><img id=\"html-img\" src=\"" + item.images + "\"  /></div>")
    # 拼接视频html
    if item.video:
        no_stream_strings.append("<div><h4>" + item.video_name + "</h4></div>")
        no_stream_strings.append("<div><video id=\"html-video\" src=\"" + item.video + "\" controls /></div>")
    # 拼接流程html
    if item.flow:
        #调用java接口生成流程图图片，返回可以访问的http地址
        no_stream_strings.append("<div><img id=\"html-flowimg\" src=\"" + get_flow_image(item.flow) + "\" /></div>")
    # 拼接表格html
    if item.table_html:
        no_stream_strings.append("<div><h4>" + item.table_name + "</h4></div>")
        no_stream_strings.append("<div id=\"html-table\">" + item.table_html + "</div>")
    no_stream_strings.append("</div>");
    return "".join(stream_strings),"".join(no_stream_strings)

def get_flow_image(flow_text:str):
    """
    根据流程文本生成流程图片

    返回:
    - str: 可浏览的流程图片
    """
    try:
        #定义返回的信息变量
        return_text=""
        # 请求的JSON数据
        data = {
            'flowText': flow_text
        }
        # 将字典转换为JSON字符串
        json_data = json.dumps(data)
        # 设置请求头
        headers = {
            'Content-Type': 'application/json; charset=UTF-8'
        }
        # java应用流程文本生成图片接口
        http=config['http']['flow_image']
        url = f'{http}/repair/experience/getFlowImage'
        # 发送POST请求
        response = requests.post(url, headers=headers, data=json_data)
        # 解析JSON字符串
        data = json.loads(response.text)
        # 判断接口调用是否成功
        if data['code']==0:
            # 取出流程图浏览链接
            return_text = data['data']
        return return_text
    except requests.RequestException as e:
        # 处理请求异常，打印错误信息
        print(f"Error occurred: {e}")
        return None

def fetch_data_from_api(url):
    try:
        # 发送 GET 请求到指定的 URL
        response = requests.get(url)
        # 检查响应的状态码，如果状态码不是 200，则抛出异常
        response.raise_for_status()
        # 返回响应的文本内容
        return response.text
    except requests.RequestException as e:
        # 处理请求异常，打印错误信息
        print(f"Error occurred: {e}")
        return None

