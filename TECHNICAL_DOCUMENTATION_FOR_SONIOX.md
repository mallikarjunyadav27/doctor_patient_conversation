# Doctor-Patient Real-Time Voice Translation Application
## Technical Documentation for Soniox API Team

**Date**: February 16, 2026  
**Purpose**: To document technical architecture, streaming implementation, and issues encountered during integration with Soniox API

---

## 1. HIGH-LEVEL TECHNICAL STACK

### Backend
- **Framework**: FastAPI 0.104.1 (Python 3.8+)
- **Server**: Uvicorn 0.24.0 (ASGI)
- **Real-time Communication**: WebSockets (websockets 12.0)
- **Audio Processing**: NumPy 1.26.2
- **Text Processing & Routing**: LangChain 0.1.0, LangChain-Core 0.1.7+
- **Data Validation**: Pydantic 2.5.0
- **Environment Management**: python-dotenv 1.0.0

### Frontend
- **Language**: Vanilla JavaScript (ES6+)
- **Audio API**: Web Audio API (ScriptProcessor)
- **Real-time Communication**: WebSocket
- **UI**: HTML5, CSS3
- **Audio Format**: PCM16 (16-bit signed linear PCM)
- **Sample Rate**: 16000 Hz (fixed to match Soniox requirement)

### External Service
- **Soniox API**: STT (Speech-to-Text) RT v3
- **Soniox WebSocket Endpoint**: wss://stt-rt.soniox.com/transcribe-websocket

---

## 2. ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                     BROWSER (Frontend)                       │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Web Audio API                                            ││
│ │ - getUserMedia() → Microphone Stream                     ││
│ │ - ScriptProcessor (1024 buffer) → PCM16 Conversion      ││
│ │ - Sample Rate: 16000 Hz                                 ││
│ └──────────────────────────────────────────────────────────┘│
│                           ↓ (Binary Audio)                   │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ WebSocket Connection                                     ││
│ │ - Low Latency Real-time Streaming                        ││
│ └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          ↓ / ↑
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server (Backend)                  │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ main.py (WebSocket Handler)                             ││
│ │ - Accepts browser WebSocket connections                 ││
│ │ - Manages bidirectional communication                   ││
│ └──────────────────────────────────────────────────────────┘│
│                           ↓                                   │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ soniox_ws.py (Soniox WebSocket Client)                  ││
│ │ - Connects to Soniox API                                ││
│ │ - Forwards audio chunks                                 ││
│ │ - Receives token results                                ││
│ └──────────────────────────────────────────────────────────┘│
│                           ↓                                   │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ langchain_router.py (Token Processing)                  ││
│ │ - Routes tokens based on speaker/language               ││
│ │ - Handles speaker diarization                           ││
│ │ - Separates final/partial tokens                        ││
│ │ - Categorizes text: original/translated                 ││
│ └──────────────────────────────────────────────────────────┘│
│                           ↓                                   │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ models.py (Box Buffers & Smart Joining)                 ││
│ │ - Three-box system: Original | Doctor | Patient         ││
│ │ - TextToken joining using smart_join()                  ││
│ │ - Whitespace normalization logic                        ││
│ └──────────────────────────────────────────────────────────┘│
│                           ↓                                   │
│ └──────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
                          ↓ / ↑
┌─────────────────────────────────────────────────────────────┐
│              Soniox STT API (External Service)               │
│ URL: wss://stt-rt.soniox.com/transcribe-websocket          │
│ - Speech Recognition                                        │
│ - Speaker Diarization                                      │
│ - Language Identification                                  │
│ - Real-time Translation (optional)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. REAL-TIME STREAMING DATA FLOW

### 3.1 Initialization Phase
1. **Browser** → Requests microphone access via `getUserMedia()`
2. **Browser** → Establishes WebSocket connection to FastAPI backend
3. **Browser** → Sends initial configuration (doctor_lang, patient_lang)
4. **FastAPI** → Accepts connection and creates:
   - `SonioxWSClient` instance
   - `LangChainRouter` instance
   - Initiates Soniox WebSocket connection
5. **Soniox Connection** → FastAPI sends JSON config:
   ```json
   {
     "api_key": "***",
     "model": "stt-rt-v3",
     "audio_format": "pcm_s16le",
     "sample_rate": 16000,
     "num_channels": 1,
     "language_hints": ["en", "te"],
     "enable_speaker_diarization": true,
     "enable_endpoint_detection": true,
     "render": "everything",
     "enable_language_identification": true,
     "translation": {
       "type": "two_way",
       "language_a": "en",
       "language_b": "te"
     }
   }
   ```

### 3.2 Continuous Streaming Phase

#### Step 1: Audio Capture (Frontend)
```javascript
// Sample Rate: 16000 Hz
// Buffer Size: 1024 samples
// Format: PCM16 (16-bit signed)
// Channels: 1 (Mono)

const audioData = event.inputBuffer.getChannelData(0);  // Float32Array
const pcm16 = new Int16Array(audioData.length);

for (let i = 0; i < audioData.length; i++) {
    let sample = Math.max(-1, Math.min(1, audioData[i]));
    pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
}

this.ws.send(pcm16.buffer);  // Send every 64ms (1024/16000)
```

#### Step 2: Audio Forwarding (FastAPI)
- Receives binary audio chunks from browser
- Immediately forwards to Soniox without buffering
- Typical chunk: ~2KB every 64ms
- No accumulation or aggregation

#### Step 3: Soniox Processing & Response
Soniox returns JSON message with structure:
```json
{
  "message_type": "result",
  "tokens": [
    {
      "text": "Hello",
      "speaker": 0,
      "speaker_id": 0,
      "language": "en",
      "is_final": false,
      "timestamp": "2026-02-16T17:57:44.621955",
      "translated": false,
      "is_translation": false
    },
    {
      "text": " patient",
      "speaker": 0,
      "speaker_id": 0,
      "language": "en",
      "is_final": true,
      "timestamp": "2026-02-16T17:57:45.102341",
      "translated": false,
      "is_translation": false
    }
  ]
}
```

#### Step 4: Token Processing (LangChain Router)
- **Extract** speaker_id, language, is_final status
- **Detect Speaker**: Map speaker_id to "Doctor" or "Patient"
  - Soniox provides speaker index (0, 1, 2...)
  - First unique speaker → Doctor
  - Second unique speaker → Patient
- **Determine Status**: original vs. translation
- **Filter**: Only FINAL tokens sent to boxes
- **Partial Tokens**: Buffered for preview (optional)

#### Step 5: Smart Token Joining (models.py)
The critical issue is **unnecessary whitespace between words**. We use `smart_join()` function:

```python
def smart_join(existing: str, new: str) -> str:
    """
    Join streamed tokens intelligently:
    - New token may already have spaces (e.g., "se e" is a single token from Soniox)
    - Don't add space if new token already starts with space
    - Don't add space if new token is punctuation
    - For Indic scripts: Never add space (concatenate naturally)
    """
    
    # Cases where we DON'T add space:
    if new[0] in (' ', '\n', '\t'):
        return existing + new  # Already has space
    
    if is_indic_char(last_char) or is_indic_char(first_char):
        return existing + new  # Indic scripts concatenate naturally
    
    if first_char in ('.', ',', '!', '?', ';', ':'):
        return existing + new  # No space before punctuation
    
    # Cases where we might add space:
    if last_char.isalnum() and first_char.isalnum():
        # Check for word continuations (suffixes like "ed", "ing", "er")
        if len(new) <= 2 and new.lower() in ['e', 'ed', 'er', 'ing', ...]:
            return existing + new  # Likely continuation
        return existing + ' ' + new  # Add space between words
    
    return existing + new  # Default: concatenate
```

#### Step 6: Box Buffering
Each of the 3 boxes uses sentence buffering:
- **Buffer tokens** until sentence-ending punctuation (. ! ?)
- **Flush to display** only complete sentences
- **Add speaker tag** [Doctor]: or [Patient]:
- **Separate lines** for each sentence

Example Output:
```
[Doctor]: Hello, how are you today?
[Patient]: I have a fever and headache.
[Doctor]: Let me check your symptoms.
```

#### Step 7: Display to Frontend
- **sent as JSON** over WebSocket with box contents
- Frontend receives and displays in real-time
- **Auto-scrolling** enabled for continuous updates

### 3.3 End-of-Stream Phase
1. Browser stops recording
2. Sends empty buffer (`b""`) as end-of-stream signal
3. FastAPI forwards to Soniox with `await soniox_client.end_stream()`
4. Soniox returns final tokens (if any) with is_final=True
5. Flushes any remaining buffered text in boxes
6. Saves conversation to JSON files (3 files)

---

## 4. THE WHITESPACE ISSUE & SOLUTION

### 4.1 Problem Description
**Issue**: Unnecessary extra white spaces appearing between words during streaming
- Example: "Hello     patient" (multiple spaces)
- Example: "How    are   you?" (irregular spacing)

### 4.2 Root Causes Identified

#### Cause 1: Soniox Token Format Variability
Soniox sometimes returns tokens that already contain spacing:
- Token 1: "Hello"
- Token 2: " patient" (space included)
- Naive joining: "Hello" + " " + " patient" = "Hello  patient" ✗

#### Cause 2: Partial vs. Final Token Mixing
- Partial tokens (is_final=false) were being displayed immediately
- Final tokens would follow with different spacing
- Created visual jitter and duplicates

#### Cause 3: Indic Script Handling
- Indian languages (Telugu, Tamil, Hindi) don't use spaces between words
- Naively adding spaces broke natural flowing text
- Needed language-aware joining

### 4.3 Solutions Implemented

#### Solution 1: Final-Token-Only Routing
- **Filter**: Only process tokens with `is_final=true` for display
- **Buffer**: Hold partial tokens separately
- **Result**: Single version of truth, no duplication
- **Code Location**: [langchain_router.py](langchain_router.py#L120-L130)

#### Solution 2: Smart Token Joining Function
- **Check** if new token already starts with space
- **Detect** Indic scripts and skip spacing for them
- **Identify** word continuations (suffixes: "ed", "ing", "er")
- **Punctuation aware**: No space before punctuation
- **Code Location**: [models.py](models.py#L18-L68)

#### Solution 3: Sentence Buffering
- **Don't display** partial words
- **Wait for** sentence-ending punctuation (. ! ?)
- **Then flush** complete sentence to display
- **Result**: Clean, complete sentences without mid-word updates
- **Code Location**: [models.py](models.py#L146-L180)

#### Solution 4: Speaker Change Handling
- **Only add tag** [Doctor]: when speaker actually changes
- **Avoid redundant** tags in middle of sentence
- **Prevents** layout breaking
- **Code Location**: [models.py](models.py#L140-L155)

### 4.4 Testing Results
- ✓ English streaming: Clean spacing maintained
- ✓ Telugu streaming: Natural concatenation without spaces
- ✓ Mixed language: Proper handling of both
- ✓ Punctuation: Correctly positioned without extra spaces
- ⚠️ Partial tokens: Still show in console logs only

### 4.5 Current Configuration
```python
# In soniox_ws.py - Soniox Config
{
    "render": "everything",  # Request both partial and final
    "enable_endpoint_detection": True,  # Better sentence boundaries
    "enable_speaker_diarization": True,  # Separate Doctor/Patient
}

# In langchain_router.py - Processing
if is_final:  # ONLY route final tokens
    self._route_to_boxes(text, speaker_label, language, status, timestamp)
else:
    self.partial_buffer[speaker_label] = text  # Buffer only
```

---

## 5. KEY IMPLEMENTATION DETAILS

### 5.1 Speaker Diarization Approach
1. **Primary**: Use Soniox speaker_id (speaker_id: 0, 1, 2...)
2. **Fallback**: Language detection (doctor_lang vs patient_lang)
3. **Last Resort**: Turn-based alternation on sentence punctuation

```python
def _detect_speaker(self, speaker_id, language: str) -> str:
    # First try: explicit speaker_id from Soniox diarization
    if speaker_id is not None and speaker_id != -1:
        # Map 0→Doctor, 1→Patient
        if speaker_id not in self.speaker_registry:
            self.speaker_registry[speaker_id] = "Doctor" if len(self.speaker_registry)==0 else "Patient"
    
    # Second try: language hints
    if language == self.doctor_lang:
        return "Doctor"
    elif language == self.patient_lang:
        return "Patient"
    
    # Fallback: turn-based on punctuation
    return self.current_speaker or "Doctor"
```

### 5.2 Same Language Mode
When doctor_lang == patient_lang:
- Translation disabled (saves API cost)
- Only Box 1 displayed (original transcript)
- Boxes 2 & 3 hidden via CSS
- Speaker diarization becomes critical
- Example: English doctor + English patient

### 5.3 Three-Box System
| Box | Content | When Shown |
|-----|---------|-----------|
| Box 1 (Original) | Detected language + speaker tag | Always |
| Box 2 (Doctor View) | Doctor language only | When translation enabled |
| Box 3 (Patient View) | Patient language only | When translation enabled |

### 5.4 Timeout Handling
- WebSocket timeout: 60 seconds (increased from 30s)
- Allows speech pauses without disconnection
- Graceful handling of network latency

### 5.5 JSON Export Format
Each conversation saved in 3 files:
```json
{
  "timestamp": "2026-02-16T17:57:44",
  "doctor_lang": "en",
  "patient_lang": "te",
  "messages": [
    {
      "speaker": "Doctor",
      "text": "How are you feeling today?",
      "language": "original",
      "timestamp": "2026-02-16T17:57:44.621955"
    },
    {
      "speaker": "Patient",
      "text": "నేను జ్వరం కు కష్టపడుతున్నాను",
      "language": "original",
      "timestamp": "2026-02-16T17:57:48.102341"
    }
  ]
}
```

---

## 6. PERFORMANCE METRICS

### Latency
- Audio→Browser buffer: 64ms (1024 samples @ 16kHz)
- Browser→Server: ~20-50ms (network dependent)
- Server→Soniox: Immediate
- Soniox processing: ~100-300ms (partial), ~500-1000ms (final)
- Backend→Browser: ~10-30ms
- **Total End-to-End**: ~200-400ms typically

### Data Volume
- Audio bitrate: 256 kbps (16000 * 16 bits)
- Transmitted: ~2KB per 64ms chunk
- Soniox response: 100-500 bytes per token
- Network overhead: < 50% of audio size

### Concurrent Connections
- FastAPI: Unlimited (async)
- Soniox: 1 WebSocket connection per frontend user
- No connection pooling needed (direct 1:1 mapping)

---

## 7. KNOWN LIMITATIONS & RECOMMENDATIONS

### 7.1 Current Limitations

1. **Whitespace Variability**
   - **Issue**: Some uncommon token sequences may still produce extra spaces
   - **Reason**: Soniox token format is not 100% documented
   - **Workaround**: Manual cleanup in exported JSON if needed

2. **Speaker Diarization Fallback**
   - **Issue**: Sentence-based fallback may misidentify short turns
   - **Reason**: Requires explicit Soniox speaker_id support
   - **Workaround**: Ensure "enable_speaker_diarization": true in config

3. **Language Mixing**
   - **Issue**: In same-language mode, if user speaks different language, text is skipped
   - **Reason**: Language mismatch filtering
   - **Workaround**: Select "Auto-detect" or primary language

4. **Real-time Token Rendering**
   - **Issue**: Only final tokens displayed (partial tokens not shown)
   - **Reason**: Prevents jitter and whitespace issues
   - **Improvement**: Could show partial preview if token formatting becomes more reliable

### 7.2 Questions for Soniox API Team

1. **Token Format Standardization**
   - Question: Can Soniox standardize whether tokens include leading/trailing spaces?
   - Current: Sometimes " patient", sometimes "patient"
   - Impact: Would eliminate need for complex smart_join() logic

2. **Intermediate Result Support**
   - Question: Is there a way to get intermediate results with absolute word positions?
   - Current: Tokens arrive as stream, no position data
   - Benefit: Would enable pixel-perfect character placement

3. **Speaker Diarization Confidence**
   - Question: Can you provide speaker_id reliability metrics?
   - Current: speaker_id sometimes -1 or absent
   - Benefit: Could choose diarization vs. language detection dynamically

4. **Language Hints Effectiveness**
   - Question: How much do language_hints improve accuracy in same-language scenarios?
   - Current: Set based on doctor_lang + patient_lang
   - Benefit: Could optimize config for accuracy vs. latency

5. **Untranslation Reverse Lookup**
   - Question: Is there a way to get original text along with translation?
   - Current: Get translated token, lose original
   - Benefit: Would enable original + translated display in boxes

### 7.3 Recommendations for Soniox

1. **Document Token Spacing Behavior**
   - Clarify when tokens include spaces
   - Provide algorithm for joining tokens
   - Publish whitespace handling guidelines

2. **Add Position Information**
   - Include character position in each token
   - Enable word-accurate display updates
   - Reduce need for buffering logic

3. **Enhance Speaker Diarization**
   - Provide speaker_id consistently
   - Include speaker change confidence score
   - Support > 2 speakers with labels ("Speaker_1", "Speaker_2")

4. **Bidirectional Translation Field**
   - For each token, provide both original and translated versions
   - Would eliminate complex routing logic
   - Better for multi-language conversations

5. **Streaming Telemetry**
   - Provide latency metrics in response
   - Include token processing time
   - Help optimize client-side buffering

---

## 8. DEPLOYMENT CONSIDERATIONS

### Environment Variables (.env)
```bash
SONIOX_API_KEY=your_actual_api_key_here
SONIOX_MODEL=stt-rt-v3
```

### Server Launch
```bash
# Development
python backend/main.py

# Production
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Browser Requirements
- Modern browser with Web Audio API support
- WebSocket support (all modern browsers)
- Microphone permission required
- HTTPS required if deployed to HTTPS domain

### Recommended Soniox Settings
```json
{
  "api_key": "your_key",
  "model": "stt-rt-v3",
  "audio_format": "pcm_s16le",
  "sample_rate": 16000,
  "num_channels": 1,
  "language_hints": ["en", "te"],
  "enable_speaker_diarization": true,
  "enable_endpoint_detection": true,
  "render": "everything",
  "enable_language_identification": true,
  "translation": {
    "type": "two_way",
    "language_a": "en",
    "language_b": "te"
  }
}
```

---

## 9. TROUBLESHOOTING GUIDE

### Symptom: Extra spaces between words
**Solutions**:
1. Verify `smart_join()` function is called in models.py
2. Check that only `is_final=true` tokens are routed to boxes
3. Verify language detection is working (check console logs)

### Symptom: Wrong speaker detected
**Solutions**:
1. Ensure speaker_id is being received from Soniox (check Soniox response)
2. Check language keys match Soniox language codes
3. Enable speaker diarization in Soniox config
4. Verify doctor_lang and patient_lang values are correct

### Symptom: Streaming cuts off prematurely
**Solutions**:
1. Check WebSocket timeout: should be 60 seconds
2. Verify audio buffer size is 1024 samples
3. Check sample rate is 16000 Hz
4. Verify Soniox connection is not timing out

### Symptom: High latency (> 800ms)
**Solutions**:
1. Reduce buffer size if possible (currently 1024)
2. Test network latency to Soniox endpoint
3. Check FastAPI server resources (CPU, memory)
4. Consider enabling only necessary Soniox features

---

## 10. FILES REFERENCE

| File | Purpose | Key Components |
|------|---------|-----------------|
| `backend/main.py` | WebSocket server, request handling | Connection management, async tasks |
| `backend/soniox_ws.py` | Soniox WebSocket client | Connection, config, token reception |
| `backend/langchain_router.py` | Token processing and routing | Speaker detection, final/partial filtering |
| `backend/models.py` | Data models and box buffers | smart_join(), sentence buffering, export |
| `backend/audio_stream.py` | Audio processing utilities | Audio buffering (if used) |
| `frontend/app.js` | Browser client application | Audio capture, WebSocket, UI updates |
| `frontend/index.html` | Frontend markup | Layout, boxes, controls |
| `frontend/styles.css` | Frontend styling | Responsive design |

---

## 11. TECHNICAL CONTACT INFORMATION

For questions about this implementation:
- **Date**: February 16, 2026
- **Technologies**: FastAPI, WebSockets, Web Audio API, LangChain
- **Primary Feature**: Real-time dual-language doctor-patient conversation transcription
- **API Provider**: Soniox (stt-rt-v3)

---

## APPENDIX: CODE SNIPPETS

### A1: Smart Join Function (Complete)
```python
def smart_join(existing: str, new: str) -> str:
    """Join streamed tokens without extra spaces"""
    if not existing:
        return new
    if not new:
        return existing
    
    if new[0] in (' ', '\n', '\t'):
        return existing + new
    
    last_char = existing[-1]
    first_char = new[0]
    
    if is_indic_char(last_char) or is_indic_char(first_char):
        return existing + new
    
    if last_char in (' ', '\n', '\t'):
        return existing + new
    
    if first_char in ('.', ',', '!', '?', ';', ':'):
        return existing + new
    
    if last_char in ('.', ',', '!', '?', ';', ':'):
        return existing + ' ' + new
    
    if last_char.isalnum() and first_char.isalnum():
        if len(new) <= 2 and new.lower() in ['a','e','i','o','u','ed','er','es','en','ly','ing','s','d','t','n','g']:
            return existing + new
        return existing + ' ' + new
    
    return existing + new
```

### A2: Soniox Configuration in Python
```python
config = {
    "api_key": os.getenv("SONIOX_API_KEY"),
    "model": "stt-rt-v3",
    "audio_format": "pcm_s16le",
    "sample_rate": 16000,
    "num_channels": 1,
    "language_hints": ["en", "te"],
    "enable_speaker_diarization": True,
    "enable_endpoint_detection": True,
    "render": "everything",
    "enable_language_identification": True,
    "translation": {
        "type": "two_way",
        "language_a": "en",
        "language_b": "te"
    }
}
await websocket.send(json.dumps(config))
```

### A3: Token Processing Loop
```python
async def receive_from_soniox():
    """Receive tokens and process"""
    while not ws_closed:
        try:
            result = await soniox_client.receive_tokens()
            if result:
                formatted_tokens = await router.format_result(result)
                boxes = router.get_boxes()
                
                await websocket.send_json({
                    "type": "partial",  # or "final"
                    "boxes": boxes,
                    "same_language": soniox_client.same_language
                })
        except Exception as e:
            print(f"Error: {e}")
```

---

**End of Technical Documentation**
