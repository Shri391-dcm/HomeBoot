# HomeBootgit

## Home Appliance AI Support Assistant

A Retrieval-Augmented Generation (RAG) chatbot that answers troubleshooting questions for Whirlpool and GE home appliances using only official public documentation.

---

## Project Overview

The goal of this project is to build an AI-powered support assistant that helps users troubleshoot common appliance issues while providing grounded answers with source citations.

The chatbot will:

- Understand the user's appliance question
- Search the appliance knowledge base
- Retrieve the most relevant information
- Generate a grounded answer
- Provide citations to official documentation
- Refuse or redirect when information is unavailable

---

## Supported Appliances

- Washing Machines
- Refrigerators
- Dishwashers

---

## Supported Manufacturers

- Whirlpool
- GE Appliances

---

## Technology Stack

- Python
- Trafilatura
- BeautifulSoup
- PyMuPDF
- pdfplumber
- BGE-small Embeddings
- ChromaDB
- BM25 Retrieval
- Dense Retrieval
- Cross-Encoder Reranker
- Ollama (Local LLM)
- Streamlit
- GitHub

---

## System Pipeline

Public Support Pages & Manuals

↓

Web Scraping

↓

Data Cleaning & PDF Extraction

↓

Chunking

↓

Embeddings

↓

Vector Database (ChromaDB)

↓

Hybrid Retrieval (BM25 + Dense)

↓

Cross-Encoder Reranking

↓

Local LLM (Ollama)

↓

Grounded Response with Citations

---

## Team Members

| Name | Role | Responsibilities |
|------|------|------------------|
| Divya Kotha | Project Manager | Project planning, GitHub management, evaluation framework, golden evaluation set, metrics, ethics report, documentation |
| Medhasri Kolluru | Data Engineer | Web scraping, robots.txt compliance, HTML/PDF extraction, chunking |
| Sanjana Ghanta | Retrieval Engineer | Embeddings, ChromaDB, BM25, dense retrieval, hybrid retrieval, reranking |
| Manisha Eerlapally | Frontend Engineer | Streamlit UI, chat interface, conversation history, citation display, testing |

---

## Repository Structure

```
HomeBoot/

README.md

reports/

src/

scraper/

data/

docs/
```

---

## Project Status

- [x] Project proposal completed
- [x] GitHub repository created
- [x] Team roles assigned
- [ ] Web scraping
- [ ] Data extraction
- [ ] Chunking
- [ ] Embeddings
- [ ] Vector database
- [ ] Retrieval pipeline
- [ ] Chatbot UI
- [ ] Evaluation
- [ ] Final report