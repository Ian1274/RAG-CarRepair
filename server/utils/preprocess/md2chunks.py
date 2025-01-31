import re
import os
import time
import uuid
import paramiko
from datetime import datetime
from tqdm import tqdm  # 用于显示进度条
from concurrent.futures import ThreadPoolExecutor
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter

# 配置远程服务器信息
remote_host = "10.18.50.117:7012"

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

    def upload_image(self, local_path):
        return f"http://{remote_host}/{local_path.replace('../', '', 1)}"

    def upload_images_concurrently(self, image_paths):
        """
        并发上传多张图片到远程服务器。

        参数：
            image_paths (list): 图片本地路径列表。

        返回值：
            dict: 本地路径到远程 URL 的映射。
        """
        url_mapping = {}

        def upload_task(local_path):
            url_mapping[local_path] = self.upload_image(local_path)

        # 设置最大并发数，并使用 tqdm 显示进度条
        max_workers = 8
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(tqdm(executor.map(upload_task, image_paths), total=len(image_paths), desc="Uploading Images"))

        return url_mapping

    def process_md_file(self):
        """
        上传 Markdown 文件中的本地图片到远程服务器，并替换图片地址。
        """
        # 读取 Markdown 文件内容
        with open(self.md_file_path, "r", encoding="utf-8") as md_file:
            md_content = md_file.read()

        # 查找 Markdown 中的图片地址
        image1_pattern = r"!\[.*?\]\((.*?)\)"
        matches = re.findall(image1_pattern, md_content)

        # 筛选存在的本地图片路径
        image_paths = [path for path in matches if os.path.exists(path)]

        # 上传图片并替换地址
        url_mapping = self.upload_images_concurrently(image_paths)
        for local_path, remote_url in url_mapping.items():
            if remote_url:
                md_content = md_content.replace(local_path, remote_url)

        # 修改图片地址格式为 HTML 格式
        img2_pattern = r"!\[.*?\]\((http.*?)\)"
        md_content = re.sub(img2_pattern, r'<img  src="\1"  />', md_content)

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
        1. 上传图片并替换地址。
        2. 按照 LangChain 格式分块。
        """
        start_time = time.time()  # 记录开始时间

        # 上传图片并替换 Markdown 文件中的图片地址
        updated_md_path, image_count = self.process_md_file()

        # 按标题分块处理 Markdown 文件
        chunk_count = self.split_md_file(updated_md_path)

        # 删除临时文件
        if os.path.exists(updated_md_path):
            os.remove(updated_md_path)

        # 打印处理结果
        elapsed_time = time.time() - start_time
        print(f"上传图片数量: {image_count}")
        print(f"分块文件数量: {chunk_count}")
        print(f"总耗时: {elapsed_time:.2f} 秒")

        return self.chunks_dir


if __name__ == "__main__":
    # 示例用法
    md_file_path = "../database/kbs_md/yyx/pdftest.md"  # 输入 Markdown 文件路径
    processor = MdProcessor(md_file_path)
    processor.run()
