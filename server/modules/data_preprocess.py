from utils.preprocess.docx2md import DocxToMdConverter  # DOCX 转 Markdown 的工具
from utils.preprocess.pdf2md import PDFProcessor  # PDF 转 Markdown 的工具
from utils.preprocess.md2chunks import MdProcessor  # Markdown 分块工具


class DataPreprocess:
    """
    数据预处理类，负责处理上传的文档，预处理（转为Markdown并分块）。
    """

    def __init__(self):
        pass

    def preprocess(self, file_path):
        """
        根据文件类型（DOCX 或 PDF）对文件进行预处理（转为 Markdown 并分块）。

        参数:
        - file_path (str): 输入文件路径。

        返回:
        - list: 包含原文件路径、Markdown 文件路径、图片保存路径、分块文件路径。
        """
        if file_path.endswith('.docx'):
            # 处理 DOCX 文件
            converter = DocxToMdConverter(file_path)  # 初始化 DOCX 转换器
            md_file_path = converter.convert()  # 转为 Markdown 文件
            md_preper = MdProcessor(md_file_path)  # 初始化 Markdown 处理器
            md_preper.run()  # 分块处理
            return [file_path, md_file_path, md_preper.image_save_dir, md_preper.chunks_dir]

        elif file_path.endswith('.pdf'):
            # 处理 PDF 文件
            pdf_processor = PDFProcessor(file_path)  # 初始化 PDF 转换器
            md_file_path = pdf_processor.execute()  # 转为 Markdown 文件
            md_preper = MdProcessor(md_file_path)  # 初始化 Markdown 处理器
            md_preper.run()  # 分块处理
            return [file_path, md_file_path, md_preper.image_save_dir, md_preper.chunks_dir]
        else:
            raise ValueError('Unsupported file format.')  # 不支持的文件格式



if __name__ == "__main__":
    # 示例用法
    name = "string"  # 知识库名称
    file_path = "../database/kbs/string/比亚迪维修手册.docx"  # 输入 DOCX 文件路径

    # 初始化数据预处理器并运行
    processor = DataPreprocess()
    processor.preprocess(name, file_path)