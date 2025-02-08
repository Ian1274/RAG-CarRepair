import os
import streamlit as st
from utils.streamlit.methods import *
import time

# 配置后端 API 地址
API_URL = "http://127.0.0.1:8011"

# 设置页面的配置
st.set_page_config(
    page_title="维修小法",
    page_icon="🔧",
    initial_sidebar_state="expanded",
)

# 初始化全局变量
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 页面标题部分
img_path_Farben = os.path.join("..", "images", "01.png")
st.sidebar.image(img_path_Farben, use_container_width=True)
st.sidebar.caption(f"""<p align="right">当前版本：0.6</p>""", unsafe_allow_html=True)

# 侧边栏功能选择
sidebar_option = st.sidebar.radio(label="选择功能", options=["**知识库问答**", "**创建知识库**", "**知识库列表**"], label_visibility="hidden")

# 知识库问答
if sidebar_option == "**知识库问答**":
    img_path_title = os.path.join("..", "images", "title.jpg")
    st.image(image=img_path_title, caption="我可以快速帮您查询汽车维修中的问题，请把问题交给我吧~🚀", use_container_width=True)

    all_kb_infos = get_all_knowledge(API_URL)
    knowledge_bases = [kb['knowledge_name'] for kb in all_kb_infos]
    knowledge_dict = {kb['knowledge_name']: kb['knowledge_code'] for kb in all_kb_infos}
    knowledge_bases.insert(0, "请选择知识库")
    option = st.sidebar.selectbox("选择知识库", knowledge_bases)

    if option == "请选择知识库":
        st.sidebar.warning("请选择一个知识库进行问答")
    else:
        select_knowledge(API_URL, knowledge_dict[option])

        question = st.chat_input("请输入问题")
        
        # 显示历史消息
        for role, message in st.session_state.get("chat_history", []):
            with st.chat_message(role):
                st.markdown(message, unsafe_allow_html=True)

        if question:
            with st.chat_message("human"):
                st.write(question)
                st.session_state.chat_history.append(("human", question))  # 仅在这里添加

            # 显示流式回答
            with st.chat_message("assistant"):
                response_placeholder = st.empty()  # 预留一个空位置来动态更新
                response_placeholder.markdown("思考中...")  # 显示等待标识
                full_response = ""  # 初始化完整响应
                response_stream = knowledge_base_chat(API_URL, knowledge_dict[option], question)
                for chunk in response_stream:
                    full_response += chunk  # 逐块拼接完整回答
                    response_placeholder.markdown(full_response, unsafe_allow_html=True)  # 实时更新 UI
                    time.sleep(0.01)  # 控制输出速度，模拟逐字打字效果
            st.session_state.chat_history.append(("assistant", full_response))  # 仅在此添加 AI 的回答
            
        if st.sidebar.button("清空历史消息"):
            st.session_state.chat_history = []

# 创建知识库
elif sidebar_option == "**创建知识库**":
    st.header("**创建知识库**")
    
    # 获取用户输入的知识库代码和描述
    kb_code = st.text_input("知识库代码")  # 这里将用户输入为知识库代码
    kb_name = st.text_input("知识库名称")   # 用户输入知识库名称
    col1, col2 = st.columns([0.5, 0.5], gap="small")
    with col1:
        brand = st.text_input("品牌")  # 用户输入品牌
    with col2:
        model = st.text_input("型号")  # 用户输入型号
    kb_description = st.text_area("知识库描述")  # 用户输入知识库描述

    if st.button("创建知识库"):
        if not kb_code or not kb_name or not kb_description:
            st.error("请填写所有字段！")
        else:
            info = {
                "brand": brand,
                "model": model,
                "knowledge_code": kb_code,
                "knowledge_name": kb_name,
                "remark": kb_description
            }
            create_knowledge(API_URL, info)


# 知识库列表
elif sidebar_option == "**知识库列表**":
    st.header("**知识库列表**")
    
    # 获取知识库列表
    all_kb_infos = get_all_knowledge(API_URL)
    knowledge_bases = [kb['knowledge_name'] for kb in all_kb_infos]
    knowledge_dict = {kb['knowledge_name']: kb['knowledge_code'] for kb in all_kb_infos}
    if not knowledge_bases:
        st.info("当前没有任何知识库。")
    else:
        selected_kb = st.selectbox("选择一个知识库", knowledge_bases)
        selected_kb_code = knowledge_dict[selected_kb]
        documents = next((kb["documents"] for kb in all_kb_infos if kb["knowledge_code"] == selected_kb_code), [])
        
        if not documents:
            st.warning(f"知识库 \"{selected_kb}\" 中没有文件，您可以上传文件。")
        else:
            st.subheader(f"知识库 \"{selected_kb}\" 中的文件:")
            for document in documents:
                file_name = document['file_name']
                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    st.write(document['file_name'])  # 显示文档名称
                with col2:
                    if st.button(f"删除", key=f"delete_{file_name}"):
                        delete_file(API_URL, selected_kb_code, file_name)

        uploaded_file = st.file_uploader("上传文件 (支持docx/pdf格式)", type=["docx", "pdf"])
    
        col1, col2, col3 = st.columns([0.5, 0.5, 0.5], gap="small")
        with col1:
            if st.button("上传文件"):
                upload_file(API_URL, selected_kb_code, uploaded_file)  
                
        with col2:
            if st.button("文件添加至知识库"):
                file_name = os.path.splitext(uploaded_file.name)[0]
                add_files_to_kb(API_URL, selected_kb_code, file_name, True)
    
        with col3:
            if st.button(f"删除知识库"):
                delete_knowledge_base(API_URL, selected_kb_code)
