#!/usr/bin/env python3
"""
RAG 向量库更新工具

使用方式：
    # 全量更新（重建向量库）
    python rag_update.py
    
    # 增量更新（仅添加新文档）
    python rag_update.py --incremental
    
    # 指定文档目录
    python rag_update.py --data ./documents/
"""

import os
import argparse
import hashlib
import shutil

# 在导入前移除代理环境变量
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('all_proxy', None)

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings


class LlamaCppEmbeddings(Embeddings):
    """LlamaCpp 向量化工具"""
    
    def __init__(self, model_path: str, binary_path: str):
        self.model_path = model_path
        self.binary_path = binary_path
        self.default_dim = 1024

    def embed_documents(self, texts: list) -> list:
        import subprocess
        import json
        
        results = []
        temp_file = "/tmp/embedding_input.json"
        
        for text in texts:
            # 写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump({"content": text}, f)
            
            # 调用 llama-embedding
            cmd = [
                self.binary_path,
                "-m", self.model_path,
                "-f", temp_file,
                "--output-json"
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                output = json.loads(result.stdout)
                embeddings = output.get('embedding', [0.0] * self.default_dim)
            except:
                embeddings = [0.0] * self.default_dim
            
            results.append(embeddings)
        
        return results

    def embed_query(self, text: str) -> list:
        return self.embed_documents([text])[0]


def compute_file_hash(file_path: str) -> str:
    """计算文件哈希值"""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def load_existing_hashes(persist_dir: str) -> set:
    """加载已存在的文档哈希值"""
    hash_file = os.path.join(persist_dir, 'document_hashes.txt')
    if os.path.exists(hash_file):
        with open(hash_file, 'r') as f:
            return set(line.strip() for line in f)
    return set()


def save_hashes(persist_dir: str, hashes: set):
    """保存文档哈希值"""
    hash_file = os.path.join(persist_dir, 'document_hashes.txt')
    with open(hash_file, 'w') as f:
        for h in sorted(hashes):
            f.write(h + '\n')


def main():
    parser = argparse.ArgumentParser(description='Update RAG Vector Database')
    parser.add_argument('--data', default='./documents', help='Documents directory')
    parser.add_argument('--persist', default='./chroma_db', help='Vector DB directory')
    parser.add_argument('--incremental', action='store_true', help='Incremental update')
    parser.add_argument('--chunk-size', type=int, default=500, help='Document chunk size')
    parser.add_argument('--chunk-overlap', type=int, default=50, help='Chunk overlap')
    args = parser.parse_args()

    # 配置
    model_path = "/home/kevin/models/bge-m3-Q8_0.gguf"
    embed_bin = "/home/kevin/AI/llama.cpp-master/build/bin/llama-embedding"
    
    print("=" * 60)
    print("📦 RAG Vector Database Update Tool")
    print("=" * 60)
    print(f"📁 Documents directory: {args.data}")
    print(f"💾 Vector DB directory: {args.persist}")
    print(f"🔄 Update mode: {'Incremental' if args.incremental else 'Full Rebuild'}")
    print("-" * 60)

    # 检查文档目录
    if not os.path.exists(args.data):
        print(f"❌ Error: Documents directory '{args.data}' not found")
        return

    # 加载已存在的哈希值
    existing_hashes = set()
    if args.incremental and os.path.exists(args.persist):
        existing_hashes = load_existing_hashes(args.persist)
        print(f"📊 Found {len(existing_hashes)} existing documents")

    # 加载文档
    print("📄 Loading documents...")
    loader = DirectoryLoader(
        args.data,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={'encoding': 'utf-8'}
    )
    
    try:
        docs = loader.load()
    except Exception as e:
        print(f"❌ Error loading documents: {e}")
        return

    if not docs:
        print("⚠️ No documents found")
        return

    print(f"✅ Loaded {len(docs)} documents")

    # 增量更新：过滤已存在的文档
    if args.incremental:
        new_docs = []
        for doc in docs:
            file_hash = compute_file_hash(doc.metadata['source'])
            if file_hash not in existing_hashes:
                new_docs.append(doc)
                existing_hashes.add(file_hash)
        
        print(f"🔄 Adding {len(new_docs)} new documents (skipped {len(docs) - len(new_docs)} existing)")
        
        if not new_docs:
            print("✅ No new documents to add")
            return
        
        docs = new_docs

    # 分割文档
    print("✂️ Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    chunks = text_splitter.split_documents(docs)
    print(f"✅ Split into {len(chunks)} chunks")

    # 初始化向量化工具
    print("🔧 Initializing embeddings...")
    embeddings = LlamaCppEmbeddings(model_path, embed_bin)

    # 创建/更新向量库
    print("💾 Updating vector database...")
    
    if args.incremental and os.path.exists(args.persist):
        # 增量更新：加载现有向量库并添加新文档
        vectorstore = Chroma(
            persist_directory=args.persist,
            embedding_function=embeddings
        )
        vectorstore.add_documents(chunks)
    else:
        # 全量重建
        if os.path.exists(args.persist):
            shutil.rmtree(args.persist)
        
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=args.persist
        )

    # 保存哈希值（用于增量更新）
    save_hashes(args.persist, existing_hashes)

    print("=" * 60)
    print("✅ Vector database updated successfully!")
    print(f"📊 Total chunks: {vectorstore._collection.count()}")
    print("=" * 60)


if __name__ == '__main__':
    main()