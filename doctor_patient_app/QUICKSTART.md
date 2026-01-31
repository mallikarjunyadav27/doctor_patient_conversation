# ⚡ QUICK START GUIDE

## 🎯 5-Minute Setup

### For Windows

```bash
# 1. Navigate to project
cd doctor_patient_app

# 2. Edit .env file - Add your Soniox API Key
# Open .env in notepad and replace:
# SONIOX_API_KEY=your_soniox_api_key_here

# 3. Run startup script
start.bat

# 4. Open browser
http://localhost:8000
```

### For Linux/macOS

```bash
# 1. Navigate to project
cd doctor_patient_app

# 2. Edit .env file
nano .env
# Add your Soniox API Key

# 3. Run startup script
chmod +x start.sh
./start.sh

# 4. Open browser
http://localhost:8000
```

### Manual Setup (If scripts don't work)

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure .env with your API key
# Edit .env file

# 4. Run backend
cd backend
python main.py

# 5. Open browser
http://localhost:8000
```

---

## 📋 What You Need

1. **Soniox API Key**
   - Get from: https://dashboard.soniox.com/settings/api-keys
   - Add to `.env` file

2. **Python 3.8+**
   - Download from: https://www.python.org
   - Verify: `python --version`

3. **Modern Browser**
   - Chrome, Firefox, Safari, or Edge
   - With microphone permission

---

## ✅ Verification

### Check if server is running
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok","api_key_configured":true}
```

### Check if Soniox is configured
- Server startup should show: `✓ Connected to Soniox API`
- If not, verify `SONIOX_API_KEY` in `.env`

---

## 🎤 Using the App

1. **Select Languages**
   - Doctor: English (default)
   - Patient: Telugu (default)

2. **Click "🎙️ Start Conversation"**
   - Allow microphone access
   - Timer starts counting

3. **Speak Naturally**
   - Both can talk simultaneously
   - Watch 3 boxes update in real-time

4. **Click "⛔ Stop Conversation"**
   - Stops recording
   - Saves 3 JSON files

5. **Export**
   - Download as JSON or Text

---

## 📁 File Structure

```
doctor_patient_app/
├── backend/           # FastAPI server
│   ├── main.py       # Entry point
│   ├── soniox_ws.py  # Soniox integration
│   └── ...
├── frontend/         # Web UI
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── recordings/       # Auto-saves here
├── .env             # Configuration ⭐ EDIT THIS
├── requirements.txt # Dependencies
├── start.bat        # Windows launcher
├── start.sh         # Linux/Mac launcher
└── README.md        # Full documentation
```

---

## 🔧 Troubleshooting

### "SONIOX_API_KEY not found"
→ Edit `.env` file and add your API key

### "Microphone access denied"
→ Check browser permissions, refresh page

### "Server not running"
→ Make sure you're in `doctor_patient_app` directory
→ Run `python backend/main.py` directly

### "WebSocket connection failed"
→ Check if server is running on port 8000
→ Try: `curl http://localhost:8000/health`

### "No audio stream"
→ Test microphone with system settings
→ Try different browser
→ Check browser console (F12)

---

## 📊 System Requirements

| Requirement | Minimum | Recommended |
|-----------|---------|------------|
| Python | 3.8 | 3.10+ |
| RAM | 2GB | 4GB+ |
| CPU | 2 cores | 4 cores |
| Disk | 500MB | 1GB |
| Internet | 5 Mbps | 10 Mbps |

---

## 🌐 Access Points

- **Frontend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/ws

---

## 📚 For More Help

1. **Full README**: See `README.md`
2. **Soniox Docs**: https://docs.soniox.com
3. **FastAPI Help**: https://fastapi.tiangolo.com
4. **Check Logs**: Server prints detailed messages

---

## 🚀 You're Ready!

```
1. Add API key to .env
2. Run start.bat (Windows) or start.sh (Linux/Mac)
3. Open http://localhost:8000
4. Click Start and speak!
```

**Enjoy real-time voice translation!** 🎤✨
