import os
from langchain_community.document_loaders import TextLoader, Docx2txtLoader, UnstructuredMarkdownLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import create_retriever_tool
from typing import List
from langchain_core.documents import Document
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Embedding 配置（从环境变量读取，与 model.py 保持一致的风格）
EMBEDDING_API_KEY = os.getenv("SILICONFLOW_API_KEY")
if not EMBEDDING_API_KEY:
    raise ValueError("未找到 SILICONFLOW_API_KEY 环境变量，请检查 .env 文件")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1")

# 定义数据目录
DATA_DIR = os.path.join(os.path.dirname(__file__), "../RAG_data")

# 全局变量缓存 retriever，避免每次调用都重新构建索引
_cached_retriever = None

def load_documents(directory: str) -> List[Document]:
    """加载指定目录下的多种格式文档"""
    documents = []
    
    # 1. 加载 .txt
    txt_loader = DirectoryLoader(directory, glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
    documents.extend(txt_loader.load())
    
    # 2. 加载 .md
    md_loader = DirectoryLoader(directory, glob="**/*.md", loader_cls=UnstructuredMarkdownLoader)
    documents.extend(md_loader.load())
    
    # 3. 加载 .docx
    docx_loader = DirectoryLoader(directory, glob="**/*.docx", loader_cls=Docx2txtLoader)
    documents.extend(docx_loader.load())
    
    print(f"[RAG] 已加载 {len(documents)} 个文档")
    return documents

def _get_retriever():
    """获取或初始化检索器（单例模式）"""
    global _cached_retriever
    if _cached_retriever is not None:
        return _cached_retriever

    # 1. 加载文档
    if not os.path.exists(DATA_DIR):
        print(f"[RAG] 警告: 数据目录不存在 {DATA_DIR}")
        return None
        
    docs = load_documents(DATA_DIR)
    
    if not docs:
        print("[RAG] 警告: 未找到任何文档")
        return None

    # 2. 切分文档
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  # 每个切片500字符
        chunk_overlap=50 # 重叠50字符，保持上下文连贯
    )
    splits = text_splitter.split_documents(docs)
    print(f"[RAG] 文档切分完成，共 {len(splits)} 个片段")

    # 3. 初始化 Embedding（使用文件开头定义的配置常量）
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_base=EMBEDDING_BASE_URL,
        openai_api_key=EMBEDDING_API_KEY,
        check_embedding_ctx_length=False
    )
    
    # 4. 创建向量库 (使用 FAISS)
    vectorstore = FAISS.from_documents(splits, embeddings)
    
    # 5. 创建检索器
    _cached_retriever = vectorstore.as_retriever(
        search_type="similarity", # 相似度搜索
        search_kwargs={"k": 3}    # 每次召回最相关的3个片段
    )
    
    return _cached_retriever

def query_knowledge_base(query: str) -> str:
    """
    直接查询知识库，返回检索到的文本内容拼接字符串
    
    Args:
        query (str): 查询语句
        
    Returns:
        str: 检索到的相关文档内容
    """
    retriever = _get_retriever()
    if not retriever:
        return "知识库暂时无法使用（初始化失败）。"
        
    # 执行检索
    docs = retriever.invoke(query)
    
    if not docs:
        return "未在知识库中找到相关信息。"
        
    # 拼接结果
    result_text = "根据知识库检索到的信息：\n\n"
    for i, doc in enumerate(docs, 1):
        result_text += f"--- 相关片段 {i} ---\n{doc.page_content}\n\n"
        
    return result_text
