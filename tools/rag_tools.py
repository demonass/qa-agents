import os
import subprocess
import json
import tempfile
from typing import List, Optional
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings


class LlamaCppEmbeddings(Embeddings):
    def __init__(self, model_path: str, binary_path: str):
        self.model_path = model_path
        self.binary_path = binary_path
        self.default_dim = 1024

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        total = len(texts)
        print(f"   🔄 Processing {total} chunks via llama-embedding...")
        
        for i, text in enumerate(texts):
            tmp_file = None
            try:
                if not text.strip():
                    embeddings.append([0.0] * self.default_dim)
                    continue

                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                    f.write(text)
                    tmp_file = f.name

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
                         embeddings.append([0.0] * self.default_dim)
                         continue

                try:
                    result = json.loads(clean_out)
                    embedding_vector = result.get("embedding", [])
                    
                    if len(embedding_vector) == 0:
                        embeddings.append([0.0] * self.default_dim)
                    else:
                        embeddings.append(embedding_vector)
                        
                except json.JSONDecodeError:
                    embeddings.append([0.0] * self.default_dim)

            except Exception as e:
                if tmp_file and os.path.exists(tmp_file):
                    try: os.remove(tmp_file)
                    except: pass
                embeddings.append([0.0] * self.default_dim)
            
            if (i + 1) % 10 == 0:
                print(".", end="", flush=True)
                
        print("\n✅ Embedding processing completed.")
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


class RAGSystem:
    def __init__(self, data_path: str, persist_dir: str, 
                 model_path: str, embed_bin: str):
        self.data_path = data_path
        self.persist_dir = persist_dir
        self.model_path = model_path
        self.embed_bin = embed_bin
        self.vectorstore = None
        self._initialize()
    
    def _initialize(self):
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
            print(f"⚠️ Created empty data directory: {self.data_path}")
            return
        
        try:
            embeddings = LlamaCppEmbeddings(self.model_path, self.embed_bin)
            
            if os.path.exists(self.persist_dir):
                print(f"📂 Loading existing vector store from {self.persist_dir}")
                self.vectorstore = Chroma(
                    persist_directory=self.persist_dir,
                    embedding_function=embeddings
                )
            else:
                print(f"📂 Loading documents from {self.data_path}")
                loader = DirectoryLoader(
                    self.data_path, 
                    glob="**/*.txt", 
                    loader_cls=TextLoader,
                    loader_kwargs={'encoding': 'utf-8'}
                )
                docs = loader.load()
                
                if not docs:
                    print("⚠️ No documents found in data directory")
                    return
                
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=500, 
                    chunk_overlap=50
                )
                chunks = text_splitter.split_documents(docs)
                print(f"✅ Processed {len(chunks)} document chunks")
                
                self.vectorstore = Chroma.from_documents(
                    documents=chunks,
                    embedding=embeddings,
                    persist_directory=self.persist_dir
                )
                print(f"✅ Vector store saved to {self.persist_dir}")
                
        except Exception as e:
            print(f"❌ Failed to initialize RAG system: {e}")
    
    def retrieve(self, query: str, k: int = 3) -> str:
        if not self.vectorstore:
            return ""
        
        try:
            docs = self.vectorstore.similarity_search(query, k=k)
            return "\n\n---\n\n".join([doc.page_content for doc in docs])
        except Exception as e:
            print(f"❌ RAG retrieval failed: {e}")
            return ""


_rag_system: Optional[RAGSystem] = None


def get_rag_system():
    global _rag_system
    
    if _rag_system is None:
        print("🔧 Initializing RAG system...")
        _rag_system = RAGSystem(
            data_path="./documents",
            persist_dir="./chroma_db",
            model_path="/home/kevin/models/bge-m3-Q8_0.gguf",
            embed_bin="/home/kevin/AI/llama.cpp-master/build/bin/llama-embedding"
        )
    
    return _rag_system


def rag_retrieve(query: str, k: int = 3) -> str:
    rag = get_rag_system()
    return rag.retrieve(query, k)