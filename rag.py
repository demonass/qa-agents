import os
import subprocess
import json
import tempfile
from typing import List

# LangChain 导入
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_classic.chains import RetrievalQA
from langchain_openai import ChatOpenAI 
from langchain_core.embeddings import Embeddings

# ==========================================
# 自定义 LlamaCpp Embedding 包装器
# ==========================================
class LlamaCppEmbeddings(Embeddings):
    def __init__(self, model_path: str, binary_path: str):
        self.model_path = model_path
        self.binary_path = binary_path
        self.default_dim = 1024 

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        total = len(texts)
        print(f"   🔄 正在通过 llama-embedding 处理 {total} 个片段...")
        
        for i, text in enumerate(texts):
            tmp_file = None
            try:
                if not text.strip():
                    embeddings.append([0.0] * self.default_dim)
                    continue

                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                    f.write(text)
                    tmp_file = f.name

                # 关键参数：--output-json
                cmd = [
                    self.binary_path,
                    "-m", self.model_path,
                    "-f", tmp_file,
                    "--output-json"
                ]
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )
                
                out, err = process.communicate(timeout=60)
                
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)

                clean_out = out.strip()
                
                # 兼容处理：如果输出包含调试信息或为空
                if not clean_out or "[New LWP" in clean_out:
                     lines = clean_out.split('\n')
                     found_json = False
                     for line in reversed(lines):
                         line = line.strip()
                         if line.startswith('{') and '"embedding"' in line:
                             clean_out = line
                             found_json = True
                             break
                     if not found_json and not clean_out:
                         # 如果是短文本导致的无输出，直接给个空向量兜底
                         embeddings.append([0.0] * self.default_dim)
                         continue

                # 解析 JSON
                try:
                    result = json.loads(clean_out)
                    embedding_vector = result.get("embedding", [])
                    
                    if len(embedding_vector) == 0:
                        embeddings.append([0.0] * self.default_dim)
                    else:
                        embeddings.append(embedding_vector)
                        
                except json.JSONDecodeError:
                    # 解析失败也给个默认值，不要让整个程序挂掉
                    embeddings.append([0.0] * self.default_dim)

            except Exception as e:
                if tmp_file and os.path.exists(tmp_file):
                    try: os.remove(tmp_file)
                    except: pass
                embeddings.append([0.0] * self.default_dim)
            
            # 进度条
            if (i + 1) % 10 == 0:
                print(".", end="", flush=True)
                
        print("\n✅ Embedding 处理循环结束。")
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

# ==========================================
# 主程序
# ==========================================
def main():
    print("🚀 正在启动 RAG 系统...")
    
    # --- 配置区域 ---
    DATA_PATH = "./documents"          
    PERSIST_DIR = "./chroma_db"        
    
    GGUF_MODEL_PATH = "/home/kevin/models/bge-m3-Q8_0.gguf"
    LLAMA_EMBED_BIN = "/home/kevin/AI/llama.cpp-master/build/bin/llama-embedding"

    # --- 1. 加载文档 & 分割文本 ---
    print(f"📂 正在从 {DATA_PATH} 加载文档...")
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
        print(f"⚠️ 目录不存在，已创建空目录: {DATA_PATH}")
        return

    loader = DirectoryLoader(DATA_PATH, glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()
    
    if not docs:
        print("❌ 未找到任何文档内容！")
        return

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(docs)
    print(f"✅ 文档处理完成，共切分为 {len(chunks)} 个片段。")

    # --- 2. 向量化与存储 ---
    print("🧠 正在初始化 Embedding 模型...")
    embeddings = LlamaCppEmbeddings(
        model_path=GGUF_MODEL_PATH,
        binary_path=LLAMA_EMBED_BIN
    )

    print("💾 正在构建/加载向量数据库...")
    vectorstore = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory=PERSIST_DIR
    )
    print("✅ 向量数据库准备就绪。")

    # --- 3. 创建问答链 ---
    print("🤖 正在连接本地 LLM...")
    
    llm = ChatOpenAI(
        model="qwen-2.5",
        openai_api_base="http://localhost:8080/v1",
        openai_api_key="sk-no-key-required",
        temperature=0.3
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )

    # --- 4. 启动交互 ---
    print("\n" + "="*50)
    print("💬 问答系统已就绪！请输入问题 (输入 'exit' 退出):")
    print("="*50)
    
    while True:
        query = input("\n👤 用户: ")
        if query.lower() in ["exit", "quit"]:
            print("👋 再见！")
            break
        
        if not query.strip():
            continue
            
        print("🤔 思考中...", end="\r")
        try:
            # 【修改】使用 invoke 替代废弃的调用方式
            result = qa_chain.invoke({"query": query})
            print(" " * 20, end="\r") # 清除“思考中”
            print(f"🤖 AI: {result['result']}")
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            print("请检查 llama-server 是否正在运行且端口为 8080")

if __name__ == "__main__":
    main()
