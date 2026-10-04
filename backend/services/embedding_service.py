# 创建 embedding 服务 pip install sentence-transformers 安装本地 Embedding 模型
from langchain_community.embeddings import HuggingFaceEmbeddings



embedding_model = HuggingFaceEmbeddings(

    model_name="BAAI/bge-small-zh"

)