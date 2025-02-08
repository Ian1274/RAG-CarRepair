# 汽车维修智能问答系统


## 📑 目录

- [项目简介](#-项目简介)
- [更新记录](#-更新记录)
- [特色功能](#-特色功能)
- [使用场景](#-使用场景)
- [安装与配置](#-安装与配置)
  - [配置PDF解析环境](#1-配置PDF解析环境)
  - [安装LangChain相关包](#2-安装LangChain相关包)
  - [配置数据库](#3-配置数据库)
  - [运行系统](#4-运行系统)
- [引用与致谢](#-引用与致谢)

## 🚗 项目简介

**汽车维修智能问答系统**是一个结合数据处理与基于RAG（Retrieval-Augmented Generation）的智能问答框架，旨在通过知识库的构建与维护，为用户提供精准、快速的汽车维修相关问题解答。系统支持多种文档解析与知识库管理功能，优化了查询流程，并实现了高效的问答体验。

## 🆕 更新记录

### **V0.6 更新 - 2025/2/08**

- Streamlit构建**Web界面**。

### ~~V0.5~~ ~~更新~~ ~~-~~ ~~2025/1/10~~

- ~~添加输入图片的功能，用户可以输入图片进行提问。~~
- ~~此功能接口有待优化。~~

### **V0.4 更新 - 2024/12/28**
- 完成项目模块化设计，分为 **数据处理模块** 和 **RAG模块**。
- 支持两个模块 **并行运行**，大幅提升系统运行效率。

### **V0.3 更新 - 2024/12/25**
- 新增 **PDF 文档解析** 功能，扩展知识库支持的文档类型。

### **V0.2 更新 - 2024/12/16**
- 核心功能增强：
  - 新增 **知识库文档追加功能**。
  - 新增 **删除知识库中指定文档** 的功能。
- 流程优化：显著提升知识库操作的速度和效率。
- 优化知识库路径管理：将存储在内存中的知识库和文档相关路径迁移至 **SQL 数据库**，提升存储与管理效率。

### **V0.1 更新 - 2024/11/30**
- 完成初版核心功能：
  - 支持精准的 **docx 文档解析**。
  - 实现 **智能RAG问答** 功能。
  - 支持 **图文并茂** 的问答展示形式。

## ⚙️ 特色功能

- **高效文档解析**：支持 `docx` 和 `PDF` 文档解析，确保知识库数据的完整性与准确性。
- **模块化设计**：数据处理与问答模块独立运行，彼此协同，提高系统的灵活性。
- **知识库管理**：支持文档追加、删除与查询，结合 SQL 数据库实现高效管理。
- **智能问答**：基于 RAG 技术，提供精准且直观的汽车维修问题解答。
- **图文展示**：问答内容支持图文结合，为用户提供直观的交互体验。

## 🛠️ 使用场景

- **维修知识辅助**：为维修人员快速查找汽车故障相关信息。
- **客户服务支持**：帮助客服人员高效解答客户咨询。
- **维修培训支持**：作为技术学习和案例教学的辅助工具。

## 📦 安装与配置

按照以下步骤进行环境配置并运行系统：

### 1. 配置PDF解析环境

按照以下参考配置`mineru` PDF解析的环境：

```
https://github.com/opendatalab/MinerU
```

### 2. 安装LangChain相关包

安装所需的`LangChain`及相关库：

```bash
pip install -r requirements.txt
```

embedding模型选用的是BCEmbedding，因此需要按照以下参考进行langchain的适配：

```
https://github.com/netease-youdao/BCEmbedding
```

也可以选择Ollama拉取embedding模型使用。

### 3. 配置数据库

配置一个mysql数据库与一个Milvus向量数据库，也可以选择其他的数据库，但都要得到两者的地址，在config文件中需做相应修改。

### 4. 运行系统

根据配置完成后，运行以下命令启动问答系统：

```bash
# 启动问答系统
cd server
python fastAPI.py
streamlit run app.py
```

## 📜 引用与致谢

如果您使用该系统进行研究或项目开发，欢迎引用本项目：

```bibtex
@misc{carrepairqa,
  author = {汽车维修智能问答系统},
  title = {Car Repair Intelligent QA System},
  year = {2024},
  url = {https://github.com/Ian1274/RAG-CarRepair}
}
```

感谢所有为该项目做出贡献的开发者和开源项目，特别是[LangChain](https://github.com/hwchase17/langchain)和[mineru](https://gitee.com/myhloli/MinerU)。

---

该系统将持续更新，不断优化性能与功能，以满足更多场景需求！
