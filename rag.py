"""
rag.py — Retrieval-Augmented Generation logic for the London Tube Assistant.

Pipeline:
  1. Load TFL documents from ./data
  2. Chunk them
  3. Embed and store in a local Chroma vector store
  4. Retrieve candidates, then rerank with a cross-encoder for precision
  5. Ask a local LLM (Ollama) to answer, grounded ONLY in the top chunks

Runs fully locally and free: HuggingFace embeddings + Ollama LLM. No API key needed.
"""

import os
import glob
from dataclasses import dataclass

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from sentence_transformers import CrossEncoder

# ---------- Config ----------
DATA_DIR = "data"
PERSIST_DIR = "chroma_store"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

RETRIEVE_K = 10      # retrieve  candidates by vector similarity...
RERANK_K = 4         # ...then keep the best few after cross-encoder reranking

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"#both are huggingface models, but the cross-encoder is more precise for reranking
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LLM_MODEL = "llama3.2"   

@dataclass
class Answer:
    text: str
    sources: list



_reranker = None
def _get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANK_MODEL)
    return _reranker


def _load_documents():
    """Load every .txt and .pdf file in the data directory."""
    docs = []
    for path in glob.glob(os.path.join(DATA_DIR, "*")):
        if path.lower().endswith(".txt"):
            docs.extend(TextLoader(path, encoding="utf-8").load())
        elif path.lower().endswith(".pdf"):
            docs.extend(PyPDFLoader(path).load())
    if not docs:
        raise RuntimeError(
            f"No .txt or .pdf files found in '{DATA_DIR}/'. "
            "Add some TFL documents there first."
        )
    return docs


def build_or_load_index():
    """Build the vector store from documents, or load it if it already exists."""
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        return Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)

    docs = _load_documents()
    
    # In rag.py, improve the splitter with better separators and smaller chunks
    splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,          # slightly smaller = more precise retrieval
    chunk_overlap=120,       # a bit more overlap preserves context across splits
    separators=["\n\n", "\n", ". ", " ", ""],  # prefer paragraph > line > sentence
)
    chunks = splitter.split_documents(docs)

    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
    )
    return vectordb

def transform_query(question: str) -> str:
    """Rewrite the user's question into a more retrieval-friendly form."""
    llm = ChatOllama(model=LLM_MODEL, temperature=0)
    prompt = (
        "Rewrite the following user question into a clear, specific search query "
        "for retrieving London transport (TFL) information. Keep it short. "
        "Return ONLY the rewritten query, nothing else.\n\n"
        f"User question: {question}"
    )
    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        rewritten = response.content.strip()
        # safety: if it returns something weird/empty, fall back to original
        return rewritten if rewritten and len(rewritten) < 300 else question
    except Exception:
        return question   # if transformation fails, use the original
def answer_question(vectordb, question: str) -> Answer:
    """
    Retrieve candidates, rerank them with a cross-encoder, and ask the LLM
    to answer grounded in the top reranked chunks (with sources).
    """
    
    # 0. Transform the query for better retrieval
    # search_query = transform_query(question)

    # 1. Retrieve using the transformed query
    # candidates = vectordb.similarity_search(search_query, k=RETRIEVE_K)
    candidates = vectordb.similarity_search(question, k=RETRIEVE_K)
    if not candidates:
        return Answer(text="I don't have information on that.", sources=[])

    # 2. Rerank with a cross-encoder for precision
    reranker = _get_reranker()
    pairs = [(question, doc.page_content) for doc in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    top_docs = [doc for _, doc in ranked[:RERANK_K]]

    # 3. Build context + collect sources
    context_parts, sources = [], []
    for i, doc in enumerate(top_docs):
        src = os.path.basename(doc.metadata.get("source", "unknown"))
        context_parts.append(f"[Source {i+1}: {src}]\n{doc.page_content}")
        if src not in sources:
            sources.append(src)
    context = "\n\n".join(context_parts)

    # 4. Ground the LLM in the reranked context
    system_prompt = (
        "You are a helpful assistant for Transport for London (TFL) information. "
        "Answer the user's question using ONLY the context provided below. "
        "If the answer is not in the context, say you don't have that information "
        "rather than guessing. Be concise and clear. "
        "Do NOT refer to the context as 'Source 1', 'Source 2', etc. "
        "Answer directly, as if the information is your own knowledge about TFL.\n\n"
        f"Context:\n{context}"
    )

    llm = ChatOllama(model=LLM_MODEL, temperature=0)
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
    )

    return Answer(text=response.content, sources=sources)