import re
import os
import time
import uuid
from shutil import copy2
import paramiko
from datetime import datetime
from tqdm import tqdm  # 用于显示进度条
from concurrent.futures import ThreadPoolExecutor
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter

# 配置远程服务器信息
remote_host = "127.0.0.1:8011"
# 配置图片存储的本地目录和 FastAPI 服务器信息
IMAGE_FOLDER = os.path.join("..", "database", "temp_imgs")  # 兼容不同操作系统

class MdProcessor:
    def __init__(self, md_file_path):
        """
        初始化 MdProcessor 类。

        参数：
            md_file_path (str): 输入的 Markdown 文件路径。
        """
        self.md_file_path = md_file_path
        self.generate_output_paths()
        
        # 确保输出目录存在
        os.makedirs(self.chunks_dir, exist_ok=True)
        os.makedirs(IMAGE_FOLDER, exist_ok=True)  # 确保图片保存目录存在

    def generate_output_paths(self):
        """
        生成分块文件和图片保存的输出路径。
        """
        # 获取文件名和路径信息
        base_name = os.path.basename(self.md_file_path)
        base_dir = os.path.dirname(self.md_file_path)
        file_name = os.path.splitext(base_name)[0]

        # 定义输出路径
        self.chunks_dir = os.path.join(base_dir.replace("kbs_md", "kbs_chunks"), file_name)
        self.image_save_dir = os.path.join(base_dir.replace("kbs_md", "kbs_imgs"), file_name)

    def save_image_locally(self, local_path):
        """
        将本地图片文件复制到 temp_imgs 目录，并返回新的图片路径。

        参数：
            local_path (str): 本地图片路径。

        返回值：
            str: 新的图片路径（在 temp_imgs 目录下）。
        """
        # 生成独一无二的 ID 作为图片的新文件名
        unique_id = str(uuid.uuid4())
        file_extension = os.path.splitext(local_path)[1]  # 获取文件的扩展名
        new_image_name = f"{unique_id}{file_extension}"
        new_image_path = os.path.join(IMAGE_FOLDER, new_image_name)

        # 复制图片到新的路径
        copy2(local_path, new_image_path)

        return new_image_name

    def process_md_file(self):
        """
        将 Markdown 文件中的图片替换为本地生成的新图片路径，并改为 FastAPI 路由格式。
        """
        # 读取 Markdown 文件内容
        with open(self.md_file_path, "r", encoding="utf-8") as md_file:
            md_content = md_file.read()

        # 查找 Markdown 中的图片地址
        image1_pattern = r"!\[.*?\]\((.*?)\)"
        matches = re.findall(image1_pattern, md_content)

        # 筛选存在的本地图片路径
        image_paths = [path for path in matches if os.path.exists(path)]

        # 处理图片并替换路径为 FastAPI 路由样式
        for local_path in image_paths:
            new_image_name = self.save_image_locally(local_path)
            new_image_url = f"http://{remote_host}/image/{new_image_name}"
            md_content = md_content.replace(local_path, new_image_url)

        # 修改图片地址格式为 HTML 格式
        img2_pattern = r"!\[.*?\]\((.*?)\)"
        md_content = re.sub(img2_pattern, r'<img src="\1" />', md_content)

        # 保存修改后的 Markdown 文件
        base_name, ext = os.path.splitext(os.path.basename(self.md_file_path))
        updated_md_path = os.path.join(os.path.dirname(self.md_file_path), f"{base_name}_updated{ext}")

        with open(updated_md_path, "w", encoding="utf-8") as updated_md_file:
            updated_md_file.write(md_content)

        return updated_md_path, len(image_paths)

    def split_md_file(self, updated_md_path):
        """
        按照 LangChain 格式对 Markdown 文件进行分块。

        参数：
            updated_md_path (str): 修改后的 Markdown 文件路径。
        """
        # 加载 Markdown 文件
        loader = TextLoader(updated_md_path, autodetect_encoding=True)
        documents = loader.load()

        # 使用 MarkdownHeaderTextSplitter 进行分块
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[ 
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ])
        splits = markdown_splitter.split_text(documents[0].page_content)

        # 保存分块结果
        for i, split in enumerate(splits):
            # 生成标题和说明
            header_1 = split.metadata.get("Header 1", "")
            header_2 = split.metadata.get("Header 2", "")
            header_3 = split.metadata.get("Header 3", "")
            title = f"{header_1} {header_2} {header_3}".strip()
            introduction = f"以下是{header_1}-{header_2}-{header_3}的相关内容。" if header_1 and header_2 and header_3 else ""

            # 生成分块文件名和路径
            safe_title = "".join(c if c.isalnum() or c.isspace() else "_" for c in title).strip()
            filename = f"chunk_{i+1}_{safe_title}.md"
            file_path = os.path.join(self.chunks_dir, filename)

            # 写入分块内容
            with open(file_path, "w", encoding="utf-8") as chunk_file:
                chunk_file.write(f"{title}\n\n{introduction}\n\n{split.page_content}")

        print(f"Splits saved to: {self.chunks_dir}")
        return len(splits)

    def run(self):
        """
        执行完整的 Markdown 处理流程：
        1. 替换图片路径为 FastAPI 路由格式并保存。
        2. 按照 LangChain 格式分块。
        """
        start_time = time.time()  # 记录开始时间

        # 替换图片并保存 Markdown 文件
        updated_md_path, image_count = self.process_md_file()

        # 按标题分块处理 Markdown 文件
        chunk_count = self.split_md_file(updated_md_path)

        # 删除临时文件
        if os.path.exists(updated_md_path):
            os.remove(updated_md_path)

        # 打印处理结果
        elapsed_time = time.time() - start_time
        print(f"处理图片数量: {image_count}")
        print(f"分块文件数量: {chunk_count}")
        print(f"总耗时: {elapsed_time:.2f} 秒")

        return self.chunks_dir


if __name__ == "__main__":
    # 示例用法
    md_file_path = "../database/kbs_md/A0_byd/比亚迪电动车维修手册.md"  # 输入 Markdown 文件路径
    processor = MdProcessor(md_file_path)
    processor.run()
