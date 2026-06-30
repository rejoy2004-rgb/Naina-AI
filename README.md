# 👁️ Naina AI – Eye Wellness & Visual Therapy Assistant

Naina AI is an intelligent eye wellness and visual therapy assistant powered by Gemini AI and Semantic Retrieval-Augmented Generation (RAG).

The system helps users understand eye conditions, visual therapy concepts, binocular vision disorders, eye exercises, screen fatigue, dry eyes, amblyopia, and other eye wellness topics using a knowledge base built from research papers and PDFs.

---

## Features

### 🤖 AI-Powered Assistant

* Gemini 2.5 Flash
* Natural language conversations
* Context-aware responses

### 📚 Semantic RAG

* PDF knowledge base
* ChromaDB vector database
* Semantic search using embeddings
* Retrieves relevant research before answering

### 👁️ Eye Wellness Knowledge

Supports topics such as:

* Amblyopia (Lazy Eye)
* Myopia
* Hyperopia
* Dry Eye Syndrome
* Eye Strain
* Visual Fatigue
* Convergence Insufficiency
* Binocular Vision Disorders
* Vision Therapy
* Eye Exercises
* Screen Fatigue

### 💾 User Features

* User signup and login
* SQLite database
* Conversation history
* Persistent chat memory

---

# Project Structure

```text
naina_chatbot/
│
├── app.py
├── chatbot.py
├── auth.py
├── database.py
│
├── rag/
│   ├── create_vector_db.py
│   └── retrieve.py
│
├── documents/
│   ├── paper1.pdf
│   ├── paper2.pdf
│   └── paper3.pdf
│
├── vector_db/
│
├── .env
├── requirements.txt
└── README.md
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/rejoy2004-rgb/naina-chatbot.git
cd naina-chatbot
```

---

## Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Configure OpenRouter API

Create a `.env` file in the root directory:

```env
OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY
```

Generate an OpenRouter API key from:

https://openrouter.ai/keys

---

# Add Research Papers

Place your PDF files inside:

```text
documents/
```

Example:

```text
documents/
├── Amblyopia.pdf
├── VisualTherapy.pdf
├── DryEye.pdf
```

---

# Create Vector Database

Generate embeddings and build the vector database:

```bash
python rag/create_vector_db.py
```

Expected output:

```text
Loaded 150 pages
Created 500 chunks

Vector DB Created Successfully
```

---

# Run Streamlit Application

Start the application:

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

---

# Example Questions

```text
What is amblyopia?

What does the amblyopia paper say?

Explain convergence insufficiency.

What exercises help improve binocular vision?

What causes digital eye strain?
```

---

# RAG Pipeline

```text
User Question
       ↓
Vector Search
       ↓
ChromaDB
       ↓
Relevant PDF Chunks
       ↓
Gemini 2.5 Flash
       ↓
Final Response
```

---

# Technologies Used

* Python
* Streamlit
* Gemini 2.5 Flash
* ChromaDB
* LangChain
* Sentence Transformers
* SQLite
* PyPDF
* Python Dotenv

---

# Deploying on Streamlit Community Cloud

1. Push your project to GitHub.

2. Login to Streamlit Community Cloud:

https://share.streamlit.io

3. Click:

```text
New App
```

4. Select:

```text
Repository:
rejoy2004-rgb/naina-chatbot

Branch:
main

Main File:
app.py
```

5. Add Secrets:

```toml
OPENROUTER_API_KEY="YOUR_OPENROUTER_API_KEY"
```

6. Click Deploy.

Your application will be available at:

```text
https://your-app-name.streamlit.app
```

---

# Future Improvements

* Source citations
* PDF page references
* Voice assistant
* Image analysis
* Eye exercise recommendations
* Progress tracking
* User dashboards
* Website integration
* Mobile application

---

# Disclaimer

Naina AI is intended for educational and informational purposes only.

It does not diagnose, treat, cure, or prevent any disease. Users should consult qualified eye-care professionals for medical advice, diagnosis, and treatment.

---

# Author

Rejoy Besra

Naina AI – Eye Wellness & Visual Therapy Assistant
