import os
import re

from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod


class PDFProcessor:
    def __init__(self, pdf_path):
        """
        初始化 PDFProcessor 类，设置输入路径及输出目录。

        参数：
            pdf_path (str): PDF 文件路径。
        """
        self.pdf_file_path = pdf_path
        self.name_without_suff = os.path.splitext(os.path.basename(pdf_path))[0]  # 获取文件名（无后缀）
        self.base_dir = os.path.dirname(pdf_path)  # 获取文件所在目录
        self.kb_name = os.path.basename(os.path.dirname(pdf_path))  # 获取知识库名称

        # 定义 Markdown 输出路径和图片保存路径
        self.output_md_path = os.path.join(
            "../database/kbs_md", self.kb_name, f"{self.name_without_suff}.md"
        )
        self.image_save_dir = os.path.join(
            "../database/kbs_imgs", self.kb_name, self.name_without_suff
        )
        self.output_md_dir = os.path.dirname(self.output_md_path)

        # 创建必要的目录
        os.makedirs(self.image_save_dir, exist_ok=True)
        os.makedirs(self.output_md_dir, exist_ok=True)

        # 初始化数据写入器
        self.image_writer = FileBasedDataWriter(self.image_save_dir)
        self.md_writer = FileBasedDataWriter(self.output_md_dir)

    def read_pdf(self):
        """
        读取 PDF 文件的二进制内容。
        """
        reader = FileBasedDataReader("")  # 初始化文件读取器
        self.pdf_bytes = reader.read(self.pdf_file_path)  # 读取 PDF 文件

    def process_pdf(self):
        """
        使用模型对 PDF 进行分析，并提取内容。
        支持 OCR 模式和文本解析模式。
        """
        self.ds = PymuDocDataset(self.pdf_bytes)  # 创建数据集实例

        # 根据解析模式进行推理处理
        if self.ds.classify() == SupportedPdfParseMethod.OCR:
            self.infer_result = self.ds.apply(doc_analyze, ocr=True)  # OCR 模式推理
            self.pipe_result = self.infer_result.pipe_ocr_mode(self.image_writer)  # 保存 OCR 模式结果
        else:
            self.infer_result = self.ds.apply(doc_analyze, ocr=False)  # 文本解析模式推理
            self.pipe_result = self.infer_result.pipe_txt_mode(self.image_writer)  # 保存文本模式结果

    def save_results(self):
        """
        保存分析结果到 Markdown 文件，同时处理图片路径。
        """
        self.pipe_result.dump_md(
            self.md_writer,
            f"{self.name_without_suff}.md",
            os.path.relpath(self.image_save_dir, self.output_md_dir),
        )

    def convert_md_image_paths(self, md_line):
        """
        修改 Markdown 文件中的图片路径，将路径中第二个 ".." 替换为 "database"。

        参数：
            md_line (str): Markdown 文件中的一行文本。

        返回：
            str: 修改后的 Markdown 文本。
        """
        if "![](" in md_line:  # 检查行是否包含图片路径
            start_idx = md_line.find("![](") + 4  # 获取路径起始位置
            end_idx = md_line.find(")", start_idx)  # 获取路径结束位置

            if start_idx != -1 and end_idx != -1:
                # 提取图片路径并替换第二个 ".."
                path = md_line[start_idx:end_idx]
                normalized_path = re.sub(r"[\\/]+", "/", path)  # 统一路径分隔符
                parts = normalized_path.split("/")
                dotdot_count = 0

                for i, part in enumerate(parts):
                    if part == "..":
                        dotdot_count += 1
                        if dotdot_count == 2:  # 替换第二个 ".."
                            parts[i] = "database"
                            break

                # 拼接修改后的路径
                updated_path = os.path.join(*parts)
                md_line = md_line[:start_idx] + updated_path + md_line[end_idx:]

        return md_line

    def process_and_update_markdown(self):
        """
        更新 Markdown 文件内容：
        1. 修改图片路径。
        2. 规范标题格式。
        """
        try:
            with open(self.output_md_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()  # 读取 Markdown 文件内容

            updated_lines = []  # 存储更新后的内容

            for line in lines:
                # 修改图片路径
                line = self.convert_md_image_paths(line)

                # 如果是标题行，移除无效的 #
                if line.startswith("#"):
                    if not re.search(r'[一二三四五六七八九十]|\b[1-9][0-9]?\b', line):
                        line = line.lstrip('#').strip()

                updated_lines.append(line)

            # 将处理后的内容覆盖写入文件
            with open(self.output_md_path, 'w', encoding='utf-8') as file:
                file.writelines(updated_lines)

        except Exception as e:
            print(f"处理 Markdown 文件时发生错误：{e}")

    def execute(self):
        """
        执行完整的 PDF 处理流程：
        1. 读取 PDF 文件。
        2. 分析 PDF 内容。
        3. 保存 Markdown 和图片。
        4. 更新 Markdown 文件。
        """
        self.read_pdf()  # 读取 PDF 文件
        self.process_pdf()  # 分析 PDF 内容
        self.save_results()  # 保存结果
        self.process_and_update_markdown()  # 更新 Markdown 文件路径
        return self.output_md_path  # 返回 Markdown 文件路径


if __name__ == "__main__":
    # 示例用法：处理 PDF 文件
    pdf_processor = PDFProcessor("../database/kbs/yyx/pdftest.pdf")  # 替换为实际 PDF 文件路径
    pdf_processor.execute()  # 执行处理流程
