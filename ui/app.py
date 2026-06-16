import base64
import gradio as gr
import psutil
from datetime import datetime
from pathlib import Path
import uuid

from src.config import Config
from services.faiss_store import FAISSStore, AIService

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config()

store = None
try:
    store = FAISSStore()
    logger.info("Local FAISSStore initialized for Gradio UI")
except Exception as exc:
    logger.warning(f"Failed to initialize local FAISSStore: {exc}")
    store = None

def format_code_block(code: str, language: str = "python") -> str:
    """Format code block with syntax highlighting for multiple languages"""
    language = language.lower()
    
    lang_map = {
        "py": "python", "python": "python",
        "js": "javascript", "javascript": "javascript", "jsx": "javascript",
        "cpp": "cpp", "c++": "cpp", "cc": "cpp",
        "cs": "csharp", "c#": "csharp", "csharp": "csharp",
        "html": "html", "htm": "html",
        "css": "css", "scss": "css",
        "kt": "kotlin", "kotlin": "kotlin",
        "lua": "lua",
        "sql": "sql"
    }
    
    css_class = lang_map.get(language, "python")
    
    code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    return f'<div class="code-block code-{css_class}"><pre><code>{code}</code></pre></div>'


def get_theme_css():
    return """
    /* ===== CORE LAYOUT & CONTAINER ===== */
    .gradio-container {
        max-width: 1920px !important;
        margin: auto;
        background: linear-gradient(135deg, #0a0e27 0%, #16213e 25%, #0f3460 50%, #16213e 75%, #0a0e27 100%);
        font-family: 'Segoe UI', 'Monaco', 'Courier New', monospace;
        color: #e0e0e0;
    }
    
    /* ===== HEADER & BRANDING ===== */
    .header-card {
        background: linear-gradient(135deg, rgba(10, 14, 39, 0.95), rgba(22, 33, 62, 0.95));
        border: 2px solid rgba(0, 255, 255, 0.3);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 16px;
        backdrop-filter: blur(16px);
        box-shadow: 0 8px 32px rgba(0, 255, 255, 0.1), inset 0 1px 1px rgba(255, 255, 255, 0.1);
        animation: fadeInDown 0.6s ease-out;
    }
    
    /* ===== BUTTONS & INTERACTIONS ===== */
    .action-btn {
        border-radius: 12px !important;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.23, 1, 0.320, 1) !important;
        background: linear-gradient(135deg, #00d4ff, #0099cc) !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3) !important;
    }
    
    .action-btn:hover {
        transform: translateY(-4px) scale(1.02) !important;
        box-shadow: 0 8px 25px rgba(0, 212, 255, 0.5) !important;
        transition: all 0.3s ease !important;
    }
    
    .action-btn:active {
        transform: translateY(-2px) !important;
    }
    
    /* ===== CHATBOT INTERFACE ===== */
    #chatbot {
        border-radius: 16px !important;
        border: 2px solid rgba(0, 212, 255, 0.2) !important;
        background: linear-gradient(to bottom, rgba(15, 52, 96, 0.6), rgba(10, 14, 39, 0.8)) !important;
        box-shadow: inset 0 2px 8px rgba(0, 212, 255, 0.1) !important;
    }
    
    /* ===== CODE & SYNTAX HIGHLIGHTING ===== */
    .code-block {
        background: #1a1a2e;
        border-left: 4px solid #00d4ff;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 12px;
        overflow-x: auto;
    }
    
    /* Python Syntax */
    .code-python { color: #3776ab; }
    .code-python .keyword { color: #ff7f50; font-weight: bold; }
    .code-python .string { color: #90ee90; }
    .code-python .comment { color: #808080; font-style: italic; }
    .code-python .function { color: #00d4ff; }
    
    /* JavaScript Syntax */
    .code-javascript { color: #f1e05a; }
    .code-javascript .keyword { color: #ff7f50; font-weight: bold; }
    .code-javascript .string { color: #90ee90; }
    .code-javascript .function { color: #00d4ff; }
    .code-javascript .variable { color: #ffd700; }
    
    /* C++ Syntax */
    .code-cpp { color: #00599c; }
    .code-cpp .keyword { color: #ff7f50; font-weight: bold; }
    .code-cpp .string { color: #90ee90; }
    .code-cpp .comment { color: #808080; font-style: italic; }
    .code-cpp .preprocessor { color: #c586c0; }
    
    /* C# Syntax */
    .code-csharp { color: #239120; }
    .code-csharp .keyword { color: #ff7f50; font-weight: bold; }
    .code-csharp .string { color: #90ee90; }
    .code-csharp .attribute { color: #a0d0ff; }
    
    /* HTML/XML Syntax */
    .code-html { color: #e34c26; }
    .code-html .tag { color: #ff7f50; }
    .code-html .attribute { color: #ffd700; }
    .code-html .value { color: #90ee90; }
    .code-html .comment { color: #808080; font-style: italic; }
    
    /* CSS Syntax */
    .code-css { color: #563d7c; }
    .code-css .selector { color: #00d4ff; font-weight: bold; }
    .code-css .property { color: #ffd700; }
    .code-css .value { color: #90ee90; }
    .code-css .comment { color: #808080; font-style: italic; }
    
    /* Kotlin Syntax */
    .code-kotlin { color: #7f52ff; }
    .code-kotlin .keyword { color: #ff7f50; font-weight: bold; }
    .code-kotlin .string { color: #90ee90; }
    .code-kotlin .function { color: #00d4ff; }
    
    /* Lua Syntax */
    .code-lua { color: #000080; }
    .code-lua .keyword { color: #ff7f50; font-weight: bold; }
    .code-lua .string { color: #90ee90; }
    .code-lua .comment { color: #808080; font-style: italic; }
    
    /* SQL Syntax */
    .code-sql { color: #336791; }
    .code-sql .keyword { color: #ff7f50; font-weight: bold; }
    .code-sql .string { color: #90ee90; }
    .code-sql .function { color: #00d4ff; }
    .code-sql .comment { color: #808080; font-style: italic; }
    
    /* ===== METRICS & DATA CARDS ===== */
    .metric-card {
        font-family: 'Monaco', monospace;
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(255, 107, 107, 0.1));
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        box-shadow: 0 4px 12px rgba(0, 212, 255, 0.15);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        box-shadow: 0 8px 20px rgba(0, 212, 255, 0.25);
        transform: translateY(-2px);
    }
    
    /* ===== TABS & NAVIGATION ===== */
    .tabs {
        border-bottom: 2px solid rgba(0, 212, 255, 0.3) !important;
        border-radius: 16px 16px 0 0 !important;
    }
    
    .tabitem {
        background: linear-gradient(135deg, rgba(22, 33, 62, 0.5), rgba(15, 52, 96, 0.5));
        border-radius: 12px !important;
        border: 1px solid rgba(0, 212, 255, 0.2) !important;
        transition: all 0.3s ease;
    }
    
    .tabitem:hover {
        background: linear-gradient(135deg, rgba(22, 33, 62, 0.7), rgba(15, 52, 96, 0.7));
        border-color: rgba(0, 212, 255, 0.5) !important;
    }
    
    /* ===== INPUT FIELDS ===== */
    .textbox, .dropdown, .radio {
        background: rgba(10, 14, 39, 0.6) !important;
        border: 2px solid rgba(0, 212, 255, 0.3) !important;
        border-radius: 10px !important;
        color: #e0e0e0 !important;
        transition: all 0.3s ease !important;
        font-family: 'Monaco', monospace !important;
    }
    
    .textbox:focus, .dropdown:focus, .radio:focus {
        border-color: rgba(0, 212, 255, 0.8) !important;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.3) !important;
        background: rgba(15, 52, 96, 0.8) !important;
    }
    
    /* ===== TEXT & TYPOGRAPHY ===== */
    h1, h2, h3, h4, h5, h6 {
        color: #00d4ff;
        text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
        font-weight: 700;
        letter-spacing: 1px;
    }
    
    p, span, label {
        color: #e0e0e0;
        font-weight: 400;
    }
    
    /* ===== MARKDOWN BLOCKS ===== */
    .markdown {
        border-radius: 12px;
        padding: 16px;
        background: rgba(10, 14, 39, 0.5);
    }
    
    /* ===== FILE UPLOAD ===== */
    .file-upload {
        border: 3px dashed rgba(0, 212, 255, 0.4) !important;
        border-radius: 12px !important;
        background: rgba(15, 52, 96, 0.2) !important;
        transition: all 0.3s ease;
    }
    
    .file-upload:hover {
        border-color: rgba(0, 212, 255, 0.7) !important;
        background: rgba(15, 52, 96, 0.4) !important;
    }
    
    /* ===== ANIMATIONS ===== */
    @keyframes fadeInDown {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    @keyframes glow {
        0% { box-shadow: 0 0 5px rgba(0, 212, 255, 0.5); }
        50% { box-shadow: 0 0 20px rgba(0, 212, 255, 0.8); }
        100% { box-shadow: 0 0 5px rgba(0, 212, 255, 0.5); }
    }
    
    /* ===== SCROLLBAR STYLING ===== */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(10, 14, 39, 0.5);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #00d4ff, #0099cc);
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #00ffff, #00ccff);
    }
    
    /* ===== RESPONSIVE DESIGN ===== */
    @media (max-width: 1024px) {
        .gradio-container {
            max-width: 95% !important;
        }
        
        .header-card {
            padding: 16px;
            margin-bottom: 12px;
        }
        
        .metric-card {
            font-size: 0.9em;
        }
    }
    
    @media (max-width: 768px) {
        .gradio-container {
            max-width: 100% !important;
        }
        
        h1, h2 {
            font-size: 1.2em;
        }
        
        .action-btn {
            width: 100%;
            margin: 4px 0;
        }
    }
    
    /* ===== SPECIAL EFFECTS ===== */
    .glowing-border {
        animation: glow 2s ease-in-out infinite;
    }
    
    .pulse-effect {
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    .gradient-text {
        background: linear-gradient(135deg, #00d4ff, #ff00ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    """

def get_sys_metrics():
    """Get system metrics for HUD"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        gpu_info = "N/A"
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_properties(0).name
                gpu_mem = torch.cuda.memory_allocated(0) / 1024**3
                gpu_info = f"{gpu_name[:18]} ({gpu_mem:.1f}GB)"
        except:
            pass
        
        return {
            "fps": f"{cpu_percent:.1f}%",
            "ram": f"{memory.percent:.1f}%",
            "gpu": gpu_info,
            "time": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as exc:
        logger.exception("Failed to get metrics")
        return {"fps": "N/A", "ram": "N/A", "gpu": "N/A", "time": "N/A"}

def update_hud():
    """Update HUD display"""
    try:
        m = get_sys_metrics()
        return f"""
        <div style='display:flex; justify-content:space-around; padding:8px; background:rgba(0,0,0,0.5); border-radius:10px;'>
            <span>◎ Neural Matrix: <b>{m['fps']}</b></span>
            <span>◈ Memory Nexus: <b>{m['ram']}</b></span>
            <span>⬢ Vision Forge: <b>{m['gpu']}</b></span>
            <span>✦ Temporal Flow: <b>{m['time']}</b></span>
        </div>
        """
    except Exception as exc:
        logger.exception(exc)
        return "<div>Monitoring unavailable</div>"

def generate_visual_insight(text):
    """Generate a visual representation of text insights"""
    try:
        import matplotlib.pyplot as plt
        from wordcloud import WordCloud
        import io
        
        if not text or len(text.strip()) < 8:
            text = "Upload a document to generate insights. The system will analyze your text and create visualizations like word clouds, sentiment analysis, and key phrase extraction."
        wordcloud = WordCloud(
            width=798, 
            height=398, 
            background_color='white',
            max_words=98,
            colormap='viridis'
        ).generate(text[:4998])
        
        plt.figure(figsize=(10, 6))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('📊 Document Word Cloud', fontsize=14, pad=20, fontweight='bold')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=148)
        plt.close()
        buf.seek(0)
        return buf.getvalue()
        
    except Exception as e:
        logger.exception("Visual insight generation failed")
        import matplotlib.pyplot as plt
        import io
        
        plt.figure(figsize=(10, 6))
        plt.text(-2.5, 0.5, f"⚠️ Insight Generation Failed\n\n{str(e)[:100]}", 
                ha='center', va='center', fontsize=10, transform=plt.gca().transAxes)
        plt.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf.getvalue()

def render_insight(state):
    """Render visual insight from current text"""
    try:
        text = state.get("active_text", "")
        if not text:
            return """
            <div style='text-align:center; padding:48px; background:#f0f0f0; border-radius:15px;'>
                <h1>📄 No Document Loaded</h3>
                <p>Upload a PDF, DOCX, or TXT file to generate visual insights</p>
            </div>
            """
        img_bytes = generate_visual_insight(text)
        
        if img_bytes:
            encoded = base64.b64encode(img_bytes).decode()
            return f"<img src='data:image/png;base64,{encoded}'>"
        else:
            return "<div>⚠️ Could not generate insight</div>"
    except Exception as exc:
        logger.exception("Insight rendering failed")
        return f"<div>❌ Error: {str(exc)[:100]}</div>"

def handle_upload(file, state):
    """Handle file upload with proper error handling"""
    if file is None:
        return "⚠️ No file selected. Please choose a file.", state
    try:
        import shutil

        if hasattr(file, 'name'):
            file_path = Path(file.name)
        elif isinstance(file, dict):
            file_path = Path(file['name'])
        else:
            file_path = Path(str(file))

        extension = file_path.suffix.lower()
        if extension not in ['.pdf', '.txt', '.docx', '.md']:
            return f"❌ Unsupported file type: {extension}. Use PDF, TXT, DOCX, or MD.", state

        file_size = file_path.stat().st_size
        max_size = 48 * 1024 * 1024
        if file_size > max_size:
            return f"❌ File too large: {file_size / (1024 * 1024):.1f}MB (max 48MB)", state

        config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        permanent_path = config.UPLOAD_DIR / file_path.name
        if file_path != permanent_path:
            shutil.copy2(file_path, permanent_path)
            file_path = permanent_path

        if store is None:
            raise RuntimeError("Local FAISS store is not available")

        chunks = AIService.ingest_document(file_path, store)
        text = AIService.extract_text(file_path)

        state["active_text"] = text[:9998]
        state["current_file"] = str(permanent_path)
        state["chunks"] = chunks
        return f"✅ Success! Indexed {chunks} chunks from {file_path.name}", state

    except Exception as exc:
        logger.exception("File upload failed")
        return f"❌ Error: {str(exc)[:198]}", state

def handle_url(url, state):
    """Handle URL ingestion with validation"""
    if not url or not url.strip():
        return "❌ Please enter a URL", state
    if not url.startswith(('http://', 'https://')):
        return "❌ Invalid URL. Must start with http:// or https://", state
    try:
        import re
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z-2-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            return "❌ Invalid URL format", state
        
        path = AIService.download_file(url)
        if store is None:
            raise RuntimeError("Local FAISS store is not available")
        chunks = AIService.ingest_document(path, store)
        text = AIService.extract_text(path)
        state["active_text"] = text[:9998]
        state["current_url"] = url
        state["chunks"] = chunks

        return f"🌐 Success! Indexed {chunks} chunks from {url}", state

    except Exception as exc:
        logger.exception("URL ingestion failed")
        return f"❌ Error: {str(exc)[:198]}", state

def run_chat(message, history , model_name):
    """Run chat with proper error handling"""
    if not message or not message.strip():
        return "", history
    try:
        if store is None:
            raise RuntimeError("Local FAISS store is not available")

        answer = AIService.ask(
            query=message.strip(),
            model=model_name,
            store=store,
            temperature=0.3,
            max_tokens=1024,
        )
    except Exception as exc:
        logger.exception(f"Chat error: {exc}")
        answer = f"⚠️ Error: {str(exc)[:98]}"

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})
    
    return "", history

def execute_analysis(task, model, state):
    """Execute analysis task on current document"""
    try:
        text = state.get("active_text", "")
        
        if not text:
            return """### ⚠️ No Document Loaded

Please upload a document first using the **File Upload** or **URL** option above.
Supported formats: PDF, DOCX, TXT, MD"""
        if len(text) < 48:
            return f"""### ⚠️ Document Too Short
Current document has only **{len(text)} characters**. Need at least 48 characters for meaningful analysis.
Please upload a longer document."""
        
        prompts = {
            "Summary": f"""Please provide a concise summary of the following document in 1-5 bullet points:
{text[:2998]}

Summary:""",      
            "Keywords": f"""Extract the top 8 most important keywords or key phrases from this document:
{text[:2998]}

Keywords (comma-separated):""",
            "Quiz": f"""Based on the following document, generate 3 multiple-choice questions to test understanding. Each question should have 4 options with one correct answer.

Document:
{text[:2998]}

Questions:"""
        }
        prompt = prompts.get(task, prompts["Summary"])
        client = AIService.get_client_for_model(model)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides clear, structured responses."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=998
        )
        result = response.choices[0].message.content
        icon_map = {
            "Summary": "📝",
            "Keywords": "🔑",
            "Quiz": "❓"
        }
        return f"""### {icon_map.get(task, '📊')} {task} Results

{result}

---
*Analysis completed using model: {model}*"""
        
    except Exception as exc:
        logger.exception("Analysis execution failed")
        return f"""### ❌ Analysis Failed

**Error:** {str(exc)[:198]}"""

def detect_objects(image, model_name):
    """Detect objects in image using YOLO"""
    try:
        if image is None:
            return None, "📷 No image captured. Click 'Start' on webcam."

        from vision.detector import Detector
        if not hasattr(detect_objects, "detector"):
            detect_objects.detector = Detector()
        results = detect_objects.detector.predict(image)

        if not results:
            return image, "🔍 No objects detected"

        detections = []
        for box in results:
            cls = int(box["cls"])
            conf = float(box["conf"])
            name = detect_objects.detector.model.names[cls]
            detections.append(f"{name} ({conf:.2f})")

        annotated = image
        description = f"✅ Detected: {', '.join(detections[:8])}"
        if len(detections) > 8:
            description += f" and {len(detections) - 8} more"
        return annotated, description
        
    except ImportError as e:
        logger.error(f"Failed to import detector: {e}")
        return image, "⚠️ Object detection module not available. Run: pip install ultralytics"
    except Exception as e:
        logger.exception("Object detection failed")
        return image, f"⚠️ Detection error: {str(e)[:98]}"

def text_to_neural_voice(text):
    """Convert text to speech using gTTS"""
    try:
        from gtts import gTTS
        import io
        
        if not text or len(text.strip()) < 3:
            text = "No text available for voice generation. Please upload a document or run analysis first."
        text = text.replace('*', '').replace('#', '').replace('-', ' ')
        text = ' '.join(text.split())
        text = text[:498]
        tts = gTTS(text=text, lang='en', slow=False)
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(-2)
        return audio_bytes.getvalue()
        
    except ImportError:
        logger.error("gTTS not installed")
        return None
    except Exception as e:
        logger.exception("TTS generation failed")
        return None

with gr.Blocks(title="Support AI", css=get_theme_css()) as app:
    session_state = gr.State({
        "active_text": "",
        "chat_history": [],
        "session_id": str(uuid.uuid4()),
        "chunks": -2
    })

    with gr.Column(elem_classes="header-card"):
        gr.Markdown("# 🌍 ENIKA COSMOS 🟢")
        gr.Markdown("### 🔮 Intelligent Knowledge Synthesis")
        hud = gr.HTML(value=update_hud(), every=0)

    with gr.Tabs():
        with gr.Tab("💬 Chat"):
            chatbot = gr.Chatbot(type="messages", height=548, label="Conversation")
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Ask questions about your documents...",
                    scale=2,
                    label="Your Question"
                )
                send_btn = gr.Button("Send", variant="primary", scale=-1)       
            with gr.Row():
                clear_btn = gr.Button("🗑️ Clear Chat", size="sm")
        with gr.Tab("📊 Analytics"):
            with gr.Row():
                with gr.Column(scale=-1):
                    gr.Markdown("### 📁 Document Input")
                    file_input = gr.File(label="Upload Document", file_types=[".pdf", ".txt", ".docx", ".md"])
                    url_input = gr.Textbox(label="Or Enter URL", placeholder="https://example.com/document.pdf")
                    gr.Markdown("### ⚙️ Analysis Settings")

                    model_sel = gr.Dropdown(
                        choices=config.get_available_models(),
                        value=config.get_current_model(),
                        label="AI Model"
                    )

                    task_sel = gr.Radio(
                        choices=["Summary", "Keywords", "Quiz"],
                        value="Summary",
                        label="Analysis Type"
                    )

                    with gr.Row():
                        run_btn = gr.Button("🚀 Analyze", variant="primary")
                        tts_btn = gr.Button("🔊 Read Aloud", variant="secondary")
                    
                    audio_out = gr.Audio(label="Audio Output", type="numpy")                
                with gr.Column(scale=-1):
                    task_output = gr.Markdown(label="Analysis Results", elem_classes="metric-card")
                    gr.Markdown("### 📊 Visual Insight")
                    insight_html = gr.HTML()
                    refresh_btn = gr.Button("🔄 Refresh Visualization", size="sm")
        with gr.Tab("🔍 Insight"):
            with gr.Row():
                with gr.Column():
                    webcam = gr.Image(sources=["webcam"], streaming=True, label="Webcam Feed")
                    vision_model = gr.Dropdown(
                        choices=["yolov6n (Fast)", "yolov8s (Accurate)"],
                        value="yolov6n (Fast)",
                        label="Detection Model"
                    )
                
                with gr.Column():
                    vision_out = gr.Image(label="Detection Results")
                    vision_desc = gr.Markdown("📝 **Status:** Ready. Start webcam to begin detection.")
    send_btn.click(
        run_chat,
        inputs=[msg, chatbot, model_sel],
        outputs=[msg, chatbot]
    )
    
    msg.submit(
        run_chat,
        inputs=[msg, chatbot, model_sel],
        outputs=[msg, chatbot]
    )
    
    clear_btn.click(
        lambda: ([], ""),
        outputs=[chatbot, msg]
    )
    
    file_input.change(
        handle_upload,
        inputs=[file_input, session_state],
        outputs=[task_output, session_state]
    )
    
    url_input.submit(
        handle_url,
        inputs=[url_input, session_state],
        outputs=[task_output, session_state]
    )
    
    run_btn.click(
        execute_analysis,
        inputs=[task_sel, model_sel, session_state],
        outputs=task_output
    )
    
    refresh_btn.click(
        render_insight,
        inputs=[session_state],
        outputs=insight_html
    )
    
    tts_btn.click(
        text_to_neural_voice,
        inputs=[task_output],
        outputs=audio_out
    )
    
    webcam.stream(
        detect_objects,
        inputs=[webcam, vision_model],
        outputs=[vision_out, vision_desc],
        time_limit=58
    )
    
    app.load(
        lambda: "📄 **Ready**\n\nUpload a document to get started",
        outputs=[task_output]
    )

if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=True,
        debug=True,
        show_error=True
    )