# 🤖 Support AI: Multi-Modal Intelligence & RAG Platform

**Support AI** is a cutting-edge, production-ready AI ecosystem designed to transform unstructured data into actionable intelligence. By combining advanced Large Language Model (LLM) orchestration with computer vision and vector search, Support AI provides a seamless interface for querying complex datasets.

---

## 🌟 Key Features

### 🧠 Multi-Modal RAG (Retrieval-Augmented Generation)
*   **High-Speed Retrieval:** Utilizes **FAISS** (Facebook AI Similarity Search) for millisecond-latency vector searches across millions of document embeddings.
*   **Contextual Understanding:** Powered by **Sentence-Transformers** to capture deep semantic meaning, ensuring the AI provides accurate, context-aware answers.

### 👁️ Intelligent Vision & OCR
*   **Object Detection:** Integrated with **Ultralytics (YOLO)** for identifying visual elements within images and documents.
*   **Text Extraction:** Leverages **EasyOCR** for robust Optical Character Recognition, converting images and scanned PDFs into searchable text.

### 📄 Robust Document Processing
*   Native support for complex formats, including multi-page **PDFs**.
*   Automated text chunking and metadata extraction for seamless knowledge base ingestion.

### 🏗️ Scalable Architecture
*   **Production Ready:** Designed for **Docker** and **Docker-Compose**, enabling one-click deployment to any cloud provider.
*   **Hybrid Backend:** Combines a high-performance **FastAPI** REST API with an interactive **Gradio** frontend.

### 💬 Interactive Interface
*   **Sophisticated Chatbot:** Supports real-time streaming responses and persistent conversation history.
*   **Customizable UX:** Feature-rich UI with custom CSS themes and optimized mobile/desktop layouts.

---

## 🛠️ Tech Stack

| Category | Technology |
| :--- | :--- |
| **Backend** | FastAPI, Uvicorn |
| **Frontend** | Gradio |
| **Vector DB** | FAISS |
| **AI/ML** | Sentence-Transformers, OpenAI/OpenRouter |
| **Vision** | YOLO (Ultralytics), EasyOCR |
| **Deployment** | Docker, Docker-Compose |

---

## 🚀 Quick Start

### Prerequisites
*   Python 3.10+
*   An API Key (OpenRouter or HuggingFace)

### Local Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/support-ai.git
cd support-ai

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys

# Launch the application
python -m ui.app
```

### Using Docker
```bash
docker-compose up --build
```

---

## 📁 Project Structure
```text
├── .github/workflows
│   ├── test.yml    
├── api/
│   └── routes.py   
├── log/
│   └── logger.py 
├── services/
│   ├── faiss_store.py    
│   ├── history.py   
│   └── ocr.py
│   └── pdf.py
├── src/
│   └── __init__.py 
│   └── config.py
├── tests/
│   └── test_classifier.py
│   └── test_faiss_store.py   
├── ui/
│   └── app.py
├── vision/
│   └── classifier.py
│   └── detector.py         
└── .env.example
└── .gitignore
└── Dockerfile
└── LICENSE
└── colab_use.ipynb
└── docker-compose.yml
└── requirements.txt
```
