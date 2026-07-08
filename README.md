# 🚇 London Tube Assistant

An applied-AI assistant for the London Underground that combines **retrieval-augmented
generation (RAG)** for document questions, **live Transport for London (TfL) API
integration** for real-time data, and an **agentic routing layer** that sends each
question to the right tool automatically.

Runs **fully locally and free** — HuggingFace embeddings + a local Ollama LLM, with no
paid API keys required.

---

## What it does

The app has one intelligent **Smart Assistant** mode plus dedicated tool modes:

| Capability | How it works | Type |
|---|---|---|
| **Smart Assistant** | An LLM router reads the question and dispatches it to the right tool below, with a RAG fallback | Agentic routing |
| **Ask a Question** | Answers questions about fares, zones, accessibility, night services, and airports from a local document corpus | RAG |
| **Live Tube Status** | Real-time line status (good service / delays) | Live TfL API |
| **Fare Calculator** | Real single fares between two stations (cash / peak / off-peak) | Live TfL API |
| **Next Trains** | Live arrival predictions for a chosen station | Live TfL API |
| **Tube Map** | Displays the network map with a download option | File serving |

## Architecture

```
User question
     │
     ▼
┌─────────────────┐     keyword rules for reliable cases (e.g. maps)
│  Agentic Router │ ──► few-shot LLM classification for the rest
└─────────────────┘
     │
     ├── status   → TfL Line Status API
     ├── fare      → TfL FareTo API
     ├── arrivals  → TfL Arrivals API
     ├── map       → local map image + download
     └── rag       → Chroma vector search → cross-encoder rerank → local LLM
```

### The RAG pipeline (the "Ask a Question" / rag route)

1. **Ingestion** — TfL documents in `data/` are chunked (`RecursiveCharacterTextSplitter`).
2. **Embedding** — chunks embedded with `sentence-transformers/all-MiniLM-L6-v2`.
3. **Vector store** — stored in a local **Chroma** database.
4. **Retrieval** — top-10 candidates fetched by vector similarity.
5. **Reranking** — a **cross-encoder** (`ms-marco-MiniLM-L-6-v2`) re-scores candidates and
   keeps the best few, improving precision over plain similarity search.
6. **Generation** — a local **Ollama** LLM answers grounded strictly in the retrieved
   context, with source attribution.

## Tech stack

- **Python**, **Streamlit** (UI)
- **LangChain** (RAG orchestration)
- **Chroma** (vector database)
- **sentence-transformers** — bi-encoder embeddings + cross-encoder reranking
- **Ollama** (local LLM, e.g. `llama3.2`)
- **Transport for London Unified API** (live status, fares, arrivals)

## Setup

1. **Install [Ollama](https://ollama.com)** and pull a model:
   ```bash
   ollama pull llama3.2
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Add documents:** place TfL `.txt`/`.pdf` files in `data/` (a sample is included).
4. **(Optional) TfL API key:** the app works without one; for higher rate limits, add
   `TFL_APP_KEY=your-key` to a `.env` file (free key from
   [api-portal.tfl.gov.uk](https://api-portal.tfl.gov.uk)).
5. **Run:**
   ```bash
   streamlit run app.py
   ```
   Opens at `http://localhost:8501`.

## Design notes & honest limitations

- **This is not a pure RAG project.** Only the document-Q&A route uses RAG; the status,
  fares, and arrivals routes are live API calls, and the router is an agentic layer on
  top. It is best described as *RAG + live API integration + agentic routing*.
- **Routing runs on a small local model** and is therefore imperfect. To make it robust,
  reliably-detectable intents (e.g. map requests) are handled with deterministic keyword
  rules, the LLM router is guided with few-shot examples, and anything uncertain falls
  back to RAG.
- **Fares are live** from the TfL API; actual charges may still vary with capping and
  railcards.
- The official tube map is © Transport for London and is used here for a local
  demo only; for public use, link to [tfl.gov.uk/maps](https://tfl.gov.uk/maps) instead
  of redistributing the image.


## 🎥 Demo Video

Watch the London Tube Assistant in action:

https://www.youtube.com/watch?v=m0-3QXqZvxA

## Possible extensions

- Journey planning (TfL Journey Planner API)
- Multi-mode status (Overground, DLR, Elizabeth line)
- A stronger routing model for more reliable agentic dispatch
- Retrieval evaluation harness (Hit Rate / MRR / semantic similarity)

---

*Built as a portfolio project to demonstrate RAG, live API integration, and agentic
tool-routing in a single applied-AI application.*
