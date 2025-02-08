# api_methods.py
import os
import re
import requests
import time
import streamlit as st


# 上传文件函数
def upload_file(API_URL, kb_code, uploaded_file):
    try:
        upload_response = requests.post(
            f"{API_URL}/upload", 
            data={"name": kb_code,},
            files={"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}, 
        )
        if upload_response.status_code == 200:
            st.success(f"\"{uploaded_file.name}\" 文件已上传！")
            return True
        else:
            st.error(f"文件上传失败: {upload_response.status_code}, 详细信息: {upload_response.text}")
            return False
    except Exception as e:
        handle_api_error(e, "上传文件时发生错误")
        return False

# 获取知识库列表
def get_all_knowledge(API_URL):
    try:
        response = requests.get(API_URL + "/get_all_knowledge")
        response.raise_for_status()
        return  response.json()
    except requests.exceptions.RequestException as e:
        return handle_api_error(e, "获取知识库失败")

# 创建知识库
def create_knowledge(API_URL, info):
    try:
        create_response = requests.post(f"{API_URL}/create_knowledge", json=info)
        if create_response.status_code == 200:
            st.success(f"知识库创建成功！")
            return True
        else:
            st.error(f"创建知识库失败: {create_response.json().get('detail', '未知错误')}")
            return False
    except Exception as e:
        handle_api_error(e, "创建知识库时发生错误")
        return False
    
# 文件添加至知识库
def add_files_to_kb(API_URL, name, file_name, drop_old):
    try:
        # 构建请求体，符合后端的 KnowledgeBaseFileVo 数据结构
        payload = {
            "name": name,
            "file_name": file_name,
            "drop_old": drop_old
        }

        # 发送 POST 请求添加文件至知识库
        response = requests.post(f"{API_URL}/add_files", json=payload)
        response.raise_for_status()
        # 处理成功响应
        st.success(f"文件已成功添加到知识库 {name}！")
        return True
    except requests.exceptions.RequestException as e:
        # 处理错误响应
        st.error(f"添加文件到知识库失败: {e}")
        return False

# 删除指定文件
def delete_file(API_URL, name, file_name):
    try:
        # 构建请求体
        payload = {
            "name": name,        # 知识库名称
            "file_name": file_name  # 文件名称
        }

        # 发送 POST 请求到后端的 /delete_file 接口来删除文档
        response = requests.post(f"{API_URL}/delete_file", json=payload)
        response.raise_for_status()  # 如果响应错误，抛出异常
        st.success(f"文件 \"{file_name}\" 已删除！")
        # 处理成功响应
        return True
    except requests.exceptions.RequestException as e:
        # 处理错误响应
        return False

# 删除知识库
def delete_knowledge_base(API_URL, kb_name):
    try:
        # 修改请求为 POST，并传递包含知识库名称的 JSON 数据
        delete_response = requests.post(
            f"{API_URL}/delete_knowledge",
            json={"name": kb_name}  # API 期望的 JSON 请求体，包含知识库名称
        )
        st.success(f"知识库 \"{kb_name}\" 删除成功！")

    except Exception as e:
        # 处理异常和 API 错误
        handle_api_error(e, "删除知识库时发生错误")
        return False
    
# 加载知识库
def select_knowledge(API_URL, kb_name):
    try:
        response = requests.post(f"{API_URL}/select_knowledge", json={"name": kb_name})
        response.raise_for_status()
        st.sidebar.success(f"知识库 {kb_name} 已加载成功")
    except requests.exceptions.RequestException as e:
        handle_api_error(e, f"加载知识库 {kb_name} 失败")

# 智能问答功能
def knowledge_base_chat(API_URL, kb_name, question):
    try:
        # 发起 POST 请求，获取流式响应
        response = requests.post(
            f"{API_URL}/knowledge_base_chat",
            json={"name": kb_name, "question": question},
            stream=True
        )
        response.raise_for_status()
        # 逐步读取流式返回的数据
        for chunk in response.iter_lines(decode_unicode=True):
            # print(type(chunk), chunk)
            if chunk:
                try:
                    formatted_chunk = format_to_markdown(chunk.strip())  # 格式化响应内容
                    for char in formatted_chunk:  # 逐字输出
                        # print(type(char), char)
                        yield char
                except UnicodeDecodeError:
                    continue  # 跳过解码失败的 chunk，避免中断流式传输

    except requests.exceptions.RequestException as e:
        handle_api_error(e, "查询知识库时发生错误")
        yield "发生错误，请稍后再试。"

# 辅助函数：格式化响应为Markdown
def format_to_markdown(chunk):
    """
    将返回的内容格式化为适合 Markdown 渲染的结构。

    功能说明:
    - 将内容中的换行符替换为 Markdown 的 `<br>` 标签。
    - 自动处理序号（中文括号、英文括号以及数字点形式）的格式，适应 Markdown 的渲染需求。
    - 确保以 `-` 开头的列表项正确替换为 Markdown 格式的换行加列表形式，例如 "- item" 替换为 "<br> item"。

    参数:
        chunk (str): 需要格式化的原始内容字符串。

    返回:
        str: 格式化后的 Markdown 渲染内容。
    """
    # 替换段落换行为 Markdown 换行标记
    chunk = chunk.replace("\n", "<br>")

    # 使用正则表达式替换序号和列表项
    chunk = re.sub(r"（(\d{1,2})）", r"<br>（\1）.", chunk)  # 替换中文括号序号，例如 "（1）" 替换为 "<br>（1）."
    chunk = re.sub(r"\((\d{1,2})\)", r"<br>(\1).", chunk)   # 替换英文括号序号，例如 "(1)" 替换为 "<br>(1)."
    chunk = re.sub(r"(\d{1,2})\. ", r"<br>\1. ", chunk)     # 替换数字点序号，例如 "1. " 替换为 "<br>1. "
    chunk = re.sub(r"^- ", r"<br> ", chunk, flags=re.M)    # 确保以 `-` 开头的列表项前加上 `<br>`

    return chunk


# 处理API请求错误
def handle_api_error(e, custom_message="发生错误"):
    st.sidebar.error(f"{custom_message}: {e}")
    return []
