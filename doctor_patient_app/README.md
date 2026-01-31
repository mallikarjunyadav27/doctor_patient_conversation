# Doctor-Patient Real-Time Voice Translation Application

🎤 **Doctor-Patient Interactive Conversation Translator**

A production-ready web application for real-time, two-way speech-to-text transcription and translation between a doctor and patient using **Soniox.ai** API with FastAPI backend and LangChain processing.

---

## 🌟 Features

✅ **Real-Time Transcription** - Stream audio directly from browser microphone  
✅ **Two-Way Translation** - Automatic bidirectional translation between Doctor ↔ Patient languages  
✅ **Speaker Diarization** - Automatic identification and labeling of speakers  
✅ **Three-Box Display** - Simultaneous display of:
   - Original transcript with speaker tags
   - Doctor's view (Doctor language only)
   - Patient's view (Patient language only)
✅ **Real-Time WebSocket** - Low-latency streaming architecture  
✅ **JSON Export** - Save conversations in three separate JSON files  
✅ **Responsive UI** - Works on desktop, tablet, and mobile  
✅ **LangChain Integration** - Token routing and processing pipeline  

---

## 🏗️ Project Structure

```
doctor_patient_app/
├── backend/
│   ├── main.py                  # FastAPI server entry point
│   ├── soniox_ws.py             # Soniox WebSocket client
│   ├── langchain_router.py      # LangChain token processor
│   ├── audio_stream.py          # Audio buffering utilities
│   ├── models.py                # Pydantic data models
│   └── utils.py                 # File I/O utilities
├── frontend/
│   ├── index.html               # Main UI
│   ├── styles.css               # Styling
│   └── app.js                   # Client logic
├── recordings/                  # Saved conversations (auto-created)
├── .env                         # Environment configuration
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Soniox API Key** - Get from [https://dashboard.soniox.com/settings/api-keys](https://dashboard.soniox.com/settings/api-keys)
- **Modern Browser** - Chrome, Firefox, Safari, or Edge (with WebRTC support)

### Installation

1. **Clone or navigate to project**:
   ```bash
   cd doctor_patient_app
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment** - Edit `.env` file:
   ```env
   SONIOX_API_KEY=your_actual_api_key_here
   SONIOX_MODEL=stt-rt-v3
   ```

5. **Run the server**:
   ```bash
   cd backend
   python main.py
   ```

   Or with uvicorn directly:
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Open in browser**:
   ```
   http://localhost:8000
   ```

---

## 💬 Usage

### Step-by-Step Guide

1. **Open Application**
   - Navigate to `http://localhost:8000`
   - UI should load with 3 empty boxes

2. **Select Languages**
   - **Doctor Language**: Choose doctor's preferred language (default: English)
   - **Patient Language**: Choose patient's language (default: Telugu)

3. **Start Conversation**
   - Click **🎙️ Start Conversation** button
   - Grant microphone permission when prompted
   - Timer will start counting

4. **Natural Conversation**
   - Speak naturally - both participants can talk simultaneously
   - System automatically identifies who is speaking (speaker diarization)

5. **Live Display**
   - **Box #1 (🟦 Original)**: Raw transcription with speaker tags
   - **Box #2 (🟩 Doctor)**: Translated to doctor's language
   - **Box #3 (🟨 Patient)**: Translated to patient's language
   - All boxes update in real-time

6. **End Conversation**
   - Click **⛔ Stop Conversation**
   - Microphone stops, connection closes
   - Conversation automatically saves to JSON files

7. **Export**
   - Click **💾 Download JSON** for structured data
   - Click **📄 Export Text** for human-readable format

---

## 🔌 API Endpoints

### WebSocket Endpoint
```
ws://localhost:8000/ws
```

**Request Format** (Initial):
```json
{
  "doctor_lang": "en",
  "patient_lang": "te"
}
```

**Message Format** (Audio): Binary PCM16 chunks (16kHz, mono)

**Response Format**:
```json
{
  "type": "update",
  "tokens": [...],
  "boxes": {
    "original": "text...",
    "doctor": "text...",
    "patient": "text..."
  }
}
```

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve frontend HTML |
| GET | `/health` | Server health check |
| GET | `/recordings` | List saved recordings |

---

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Required - Get from https://dashboard.soniox.com/settings/api-keys
SONIOX_API_KEY=your_api_key_here

# Optional - Current production model
SONIOX_MODEL=stt-rt-v3

# Optional - Server settings
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

### Soniox Features Used

```python
{
    "api_key": "your_key",
    "model": "stt-rt-v3",
    "audio_format": "pcm_s16le",
    "sample_rate": 16000,
    "num_channels": 1,
    
    # Enable these features
    "language_hints": ["en", "te"],
    "enable_speaker_diarization": True,           # Speaker identification
    "enable_endpoint_detection": True,             # Auto pause detection
    "enable_language_identification": True,        # Language detection
    
    # Two-way translation
    "translation": {
        "type": "two_way",
        "language_a": "en",      # Doctor language
        "language_b": "te"       # Patient language
    },
    
    "render": "everything"  # Returns original + all translations
}
```

---

## 📁 Saved Files Format

When you stop a conversation, 3 JSON files are created:

### 1. Original Conversation
**Filename**: `Doc-patient-Orig_Lang_MMDDYYYY_HH_MM.json`

```json
{
  "timestamp": "2026-01-27T10:42:10",
  "type": "original",
  "language": "mixed",
  "entries": [
    {
      "timestamp": "2026-01-27T10:42:10",
      "speaker": "Doctor",
      "text": "How are you feeling today?",
      "language": "original",
      "translation_status": "original"
    }
  ],
  "full_text": "..."
}
```

### 2. Doctor's View
**Filename**: `Doc-patient-EN_MMDDYYYY_HH_MM.json`

```json
{
  "timestamp": "2026-01-27T10:42:10",
  "type": "doctor_view",
  "language": "en",
  "full_text": "..."
}
```

### 3. Patient's View
**Filename**: `Doc-patient-TE_MMDDYYYY_HH_MM.json`

```json
{
  "timestamp": "2026-01-27T10:42:10",
  "type": "patient_view",
  "language": "te",
  "full_text": "..."
}
```

---

## 🌍 Supported Languages

The application supports any language pair that Soniox supports:

- **English** (en)
- **Telugu** (te)
- **Hindi** (hi)
- **Spanish** (es)
- **French** (fr)
- **German** (de)
- And 50+ other languages

Visit [Soniox Docs](https://docs.soniox.com) for complete list.

---

## 🧠 Architecture

### Backend Flow

```
Browser (WebSocket)
    ↓
FastAPI Server
    ↓
Soniox API (WebSocket)
    ↓
Soniox STT Engine
    ↓
Tokens + Translations returned
    ↓
LangChain Router
    ↓
Categorize tokens by:
  - Original (Box 1)
  - Doctor Language (Box 2)
  - Patient Language (Box 3)
    ↓
Send to Browser (WebSocket)
    ↓
UI updates all 3 boxes in real-time
```

### LangChain Integration

The **LangChainRouter** class (`langchain_router.py`) acts as a middleware between Soniox and UI:

```python
- Normalizes Soniox token format
- Routes tokens to correct boxes based on language & status
- Handles speaker identification
- Buffers tokens for export
- Maintains conversation state
```

---

## 🔧 Troubleshooting

### Issue: "API Key Not Configured"
**Solution**: Set `SONIOX_API_KEY` in `.env` file
```env
SONIOX_API_KEY=your_actual_key_here
```

### Issue: Microphone Access Denied
**Solution**: 
- Check browser permissions
- For HTTPS: You need valid SSL certificate
- Try clearing browser cache

### Issue: No Audio Stream
**Solution**:
- Verify microphone is working
- Check browser console (F12) for errors
- Try different microphone device
- Restart browser

### Issue: Poor Recognition Quality
**Solution**:
- Ensure clear speech (not background noise)
- Check microphone quality
- Verify `language_hints` are correct
- Try different language combination

### Issue: WebSocket Connection Fails
**Solution**:
- Ensure server is running: `uvicorn backend.main:app --reload`
- Check firewall allows port 8000
- Verify CORS middleware is enabled
- Check browser DevTools Network tab

### Issue: Conversation Not Saving
**Solution**:
- Ensure `recordings/` directory exists
- Check file permissions
- Verify no special characters in conversation
- Check disk space

---

## 📊 Performance Notes

- **Audio Chunk Size**: 1600 samples (100ms at 16kHz)
- **Latency**: ~500ms-1s from speech to transcription
- **Browser Buffer**: Max 100 chunks (~10 seconds)
- **Concurrent Speakers**: Supported (with diarization)
- **CPU Usage**: ~5-10% during active transcription
- **Memory**: ~50-100MB per session

---

## 🔐 Security & Privacy

⚠️ **Important**:
- Store API key securely (not in git)
- Use HTTPS in production
- Implement authentication for production use
- Consider data retention policies for recordings
- GDPR/HIPAA compliance (if applicable)

---

## 📚 References

- **Soniox Documentation**: https://docs.soniox.com
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **WebSocket API**: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- **LangChain Documentation**: https://python.langchain.com
- **Soniox Language Support**: https://docs.soniox.com/languages

---

## 📝 Example Workflow

```bash
# 1. Setup
cd doctor_patient_app
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
# Edit .env with your SONIOX_API_KEY

# 3. Run
cd backend
python main.py

# 4. Use
# Open http://localhost:8000 in browser
# Click Start, speak, click Stop
# Download JSON or Text export

# 5. Check saved files
ls recordings/
# Output:
# Doc-patient-Orig_Lang_01272026_10_42.json
# Doc-patient-EN_01272026_10_42.json
# Doc-patient-TE_01272026_10_42.json
```

---

## 🚀 Production Deployment

### Recommended Setup

```bash
# Use Gunicorn for production
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app --bind 0.0.0.0:8000

# Or use Docker
docker build -t doctor-patient-translator .
docker run -p 8000:8000 -e SONIOX_API_KEY=your_key doctor-patient-translator
```

### Database Integration

For production, consider adding:
- PostgreSQL for conversation history
- Redis for caching
- S3/Cloud Storage for recordings
- User authentication

---

## 📞 Support & Troubleshooting

1. Check server logs: `tail -f server.log`
2. Browser DevTools (F12):
   - Console for JavaScript errors
   - Network tab for WebSocket activity
3. Check Soniox dashboard for API usage
4. Verify firewall isn't blocking port 8000

---

## 📄 License

[Your License Here]

---

## 👥 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Submit pull request

---

## ✨ Changelog

### v1.0.0 (Initial Release)
- Real-time transcription with Soniox
- Two-way translation
- Speaker diarization
- Three-box display
- JSON export
- Responsive UI

---

**Ready to use!** 🎉

For detailed setup help, visit: https://docs.soniox.com
