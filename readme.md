# 📄 Document Processing & Retrieval System

A full-stack FastAPI application for secure document upload, semantic search, and Retrieval-Augmented Generation (RAG)-based querying.

---

## 🚀 Features

- 🔐 **User Authentication** (Register/Login via Supabase)  
- 📤 **File Upload & Processing** (PDF/Image to refined text)  
- 🧠 **LLM-powered Querying** using Groq (LLaMA 3 8B)  
- 🧾 **Theme Extraction** from documents  
- 📦 **Vector Store Integration** with Qdrant  
- 🧷 **Embeddings** using Cloudflare  
- 🗃️ **Document Storage** in MongoDB  
- 🛠️ **Tech Stack**

---

## 🛠️ Tech Stack

| Layer            | Tech / Service           |
|------------------|-------------------------|
| Backend API      | FastAPI                 |
| Authentication  | Supabase                |
| Embeddings      | Cloudflare Workers AI   |
| Vector DB       | Qdrant                  |
| Document Storage| MongoDB                 |
| LLM (RAG)       | Groq + LLaMA 3 8B       |
| OCR             | Tesseract               |
| Containerization| Docker                  |

---

## 📁 Project Structure

```bash
fastApiProject/
│
├── auth/                  # Handles Supabase Auth
│   ├── __init__.py
│   └── auth.py
│
├── chat/                  # Document processing and chat logic
│   ├── __init__.py
│   ├── chat.py            # Main RAG pipeline
│   ├── doc.py             # PDF/Image OCR & refinement
│   ├── embeddings.py      # Cloudflare embeddings
│   └── vectorstore.py     # Qdrant operations
│
├── db/
│   └── mongo/             # MongoDB integration
│       ├── __init__.py
│       └── mongo.py
│   └── supa/              # Supabase helpers (if any)
│
├── schema/                # Pydantic schemas
│   ├── __init__.py
│   └── types.py
│
├── main.py                # FastAPI entry point
├── Dockerfile
├── .env                   # Environment variables
└── README.md              # You're here!

```
# 📡 API Endpoints Overview

---

## 🔐 Authentication

| Method | Endpoint   | Description             |
|--------|------------|-------------------------|
| POST   | /register  | Register a new user     |
| POST   | /login     | Login & get JWT token   |

---

## 📁 File Upload & Processing

| Method | Endpoint      | Description                    |
|--------|---------------|--------------------------------|
| POST   | /uploadfiles  | Upload PDF/image for processing |

---

## 📚 Vectorstore Operations

| Method | Endpoint                  | Description                 |
|--------|---------------------------|-----------------------------|
| POST   | /vectorstore/add-documents | Add processed docs to Qdrant |
| GET    | /vectorstore/get_documents  | Get all uploaded documents    |
| DELETE | /vectorstore/delete_document | Delete a document entry      |

---

## 🔍 Query & Theme Processing

| Method | Endpoint    | Description                 |
|--------|-------------|-----------------------------|
| POST   | /query      | Process query with RAG      |
| POST   | /get_themes | Extract themes from documents |

---
