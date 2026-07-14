<div align="center">

# 🧠 **AI BOOK TEACHER** 📚

### **Transforming Static Books & Handwritten Notes into Interactive AI Tutors**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.137%2B-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Relational_DB-336791.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-white.svg?style=for-the-badge&logo=ollama&logoColor=black)](https://ollama.ai)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Storage-FF69B4.svg?style=for-the-badge)](https://trychroma.com)

<br/>

**[▶️ Watch the Full System Demo on YouTube](https://youtu.be/3lOMYnohyYk)**

</div>

---

<br/>

# 📖 **OVERVIEW**

**AI Book Teacher** is a Retrieval-Augmented Generation (RAG) system built to act as your personalized tutor. Upload a textbook, a digital PDF, or a scan of handwritten notes, and the system intelligently extracts, cleans, and vectorizes the knowledge to teach you the concepts logically.

---

<br/>

# ✨ **KEY FEATURES**

- 📚 **HYBRID DOCUMENT INGESTION** <br/> Handles both native digital PDFs and scanned image-based notebooks. 
- 👁️ **WHY WE USE VLM INSTEAD OF OCR** <br/> Traditional OCR models struggle heavily with messy handwritten notes taken from phone cameras. Instead, we use local **Ollama Vision Language Models (VLMs)** to accurately transcribe complex handwritten text directly from scanned pages.
- 🛡️ **PRIVACY-AWARE DATA STRIPPER** <br/> Automatically redacts personal metadata (Student Name, Roll No., School) using Regex to keep the LLM focused on teaching, not user data.
- 🧠 **PEDAGOGICAL AI ENGINE** <br/> Uses strict system prompting to ensure the AI explains concepts cleanly for absolute beginners.

---

<br/>

# 🏗 **SYSTEM ARCHITECTURE**

## 1. INGESTION PIPELINE

```mermaid
graph TD;
    A[User Uploads PDF] --> B{Is Page a Scanned Image?};
    B -- Yes --> C[Ollama VLM Extraction];
    B -- No --> D[PyMuPDF Direct Text Extraction];
    C --> E[(PostgreSQL Metadata Store)];
    D --> E;
    E --> F[Text Chunking Module];
    F --> G[Sentence Transformers Embedding];
    G --> H[(ChromaDB Vector Store)];
```

<br/>

## 2. THE AI TEACHING ENGINE

```mermaid
graph TD;
    A[User Requests to Learn a Page] --> B[(PostgreSQL Database)];
    B --> C[Retrieve Raw Page Content];
    C --> D[Metadata Stripper];
    D --> E[Inject into Pedagogical System Prompt];
    E --> F{LLM Inference Engine};
    F -- Local --> G[Ollama Models];
    F -- API --> H[OpenAI / Groq API];
    G --> I[Formatted, Beginner-Friendly Output];
    H --> I;
```

---

<br/>

# 🚀 **QUICKSTART GUIDE**

## 1. INSTALLATION

First, ensure you have [uv](https://github.com/astral-sh/uv) installed. It is an incredibly fast Python package manager.

**Install uv:**
```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Clone and Setup the Project:**
```bash
git clone https://github.com/your-username/ai-book-teacher.git
cd ai_book_teacher

# Sync dependencies using uv
uv sync
```
*(Alternatively: `pip install -r requirements.txt`)*

## 2. ENVIRONMENT CONFIGURATION
Create a `.env` file in the root of the project:
```ini
LLM_MODEL_NAME=qwen3:8b
VLM_MODEL_NAME=qwen2.5vl:7b  
```

## 3. INITIALIZE THE DATABASE
```bash
alembic revision --autogenerate -m "Initial migration" # this will create all the models
alembic upgrade head
```

## 4. RUN THE APPLICATION
Ensure Ollama is running if using local models, then start the server:
```bash
uvicorn backend.main:app --reload

