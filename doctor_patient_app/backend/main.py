"""
FastAPI Backend for Doctor-Patient Real-Time Voice Translation
WebSocket server for handling audio streaming and real-time transcription
"""
import os
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from io import BytesIO

from soniox_ws import SonioxWSClient
from langchain_router import LangChainRouter
from audio_stream import AudioStreamProcessor
from utils import RecordingManager
from database import get_db

load_dotenv()

# Azure storage setup
AZURE_AVAILABLE = False
try:
    from azure_storage import AzureStorageManager
    
    def get_storage_manager():
        return AzureStorageManager()
    
    AZURE_AVAILABLE = True
    print("✅ Azure Storage configured")
except Exception as e:
    print(f"⚠️ Azure Storage not available: {e}")
    
    def get_storage_manager():
        return None

app = FastAPI(title="Doctor-Patient Real-Time Translator")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files - use absolute path relative to this script
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
recordings_path = os.path.join(os.path.dirname(__file__), "recordings")
try:
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    app.mount("/recordings", StaticFiles(directory=recordings_path), name="recordings")
except Exception as e:
    print(f"⚠️ Static files not mounted: {e}")


@app.get("/")
async def get_root():
    """Serve frontend"""
    try:
        index_path = os.path.join(frontend_path, "index.html")
        return FileResponse(index_path)
    except:
        return {"message": "Welcome to Doctor-Patient Translator API"}


@app.get("/medical-summary")
async def get_medical_summary():
    """Serve medical summary generator page"""
    try:
        summary_path = os.path.join(frontend_path, "medical_summary.html")
        return FileResponse(summary_path)
    except:
        return {"message": "Medical summary page not found"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "api_key_configured": bool(os.getenv("SONIOX_API_KEY")),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time transcription
    
    Flow:
    1. Browser connects and sends audio chunks
    2. Chunks are forwarded to Soniox API
    3. Soniox returns tokens (original + translations)
    4. LangChain router processes and categorizes tokens
    5. Updates sent back to browser in real-time
    6. On disconnect, conversation is saved to JSON
    """
    await websocket.accept()
    
    soniox_client = None
    router = None
    audio_processor = None
    doctor_lang = "en"
    patient_lang = "te"
    doctor_name = ""
    patient_id = None
    patient_name = ""
    ws_closed = False  # Flag to track WebSocket closure
    soniox_task = None  # Task handle for clean cancellation
    
    try:
        # Wait for initial config
        init_data = await websocket.receive_json()
        doctor_lang = init_data.get("doctor_lang", "en")
        patient_lang = init_data.get("patient_lang", "te")
        doctor_name = init_data.get("doctor_name", "Doctor")
        patient_id = init_data.get("patient_id")
        patient_name = init_data.get("patient_name", "Patient")
        
        # Initialize components
        soniox_client = SonioxWSClient()
        router = LangChainRouter(doctor_lang, patient_lang)
        audio_processor = AudioStreamProcessor()
        
        # Connect to Soniox
        await soniox_client.connect(doctor_lang, patient_lang)
        
        # Send connection confirmation
        await websocket.send_json({
            "status": "connected",
            "message": "Ready to receive audio",
            "languages": {
                "doctor": doctor_lang,
                "patient": patient_lang
            }
        })
        
        print(f"✓ WebSocket client connected (Doctor: {doctor_lang}, Patient: {patient_lang})")
        
        # Create tasks for receiving from browser and Soniox
        async def receive_from_browser():
            """Receive audio chunks from browser and forward to Soniox"""
            nonlocal ws_closed
            chunk_count = 0
            total_bytes = 0
            try:
                while True:
                    # Receive audio chunk from browser
                    data = await websocket.receive_bytes()
                    
                    if not data:
                        print("ℹ️ Received empty buffer from browser - sending end-of-stream to Soniox")
                        # End-of-stream signal
                        await soniox_client.end_stream()
                        break
                    
                    chunk_count += 1
                    total_bytes += len(data)
                    
                    # Log every 10 chunks to avoid spam
                    if chunk_count % 10 == 0:
                        print(f"   🔊 Received {chunk_count} audio chunks ({total_bytes} bytes total, chunk size: {len(data)})")
                    
                    # Process and send to Soniox
                    await soniox_client.send_audio(data)
            
            except WebSocketDisconnect:
                print("Browser disconnected - closing Soniox stream")
                ws_closed = True
                await soniox_client.end_stream()
            except Exception as e:
                print(f"Error receiving from browser: {e}")
                ws_closed = True
                try:
                    await soniox_client.end_stream()
                except:
                    pass
        
        async def receive_from_soniox():
            """Receive tokens from Soniox and send to browser"""
            nonlocal ws_closed
            try:
                message_count = 0
                while not ws_closed:  # Check if WebSocket is closed
                    try:
                        result = await soniox_client.receive_tokens()
                        
                        if result is None:
                            # Shorter sleep for faster responsiveness
                            await asyncio.sleep(0.001)
                            continue
                        
                        # Check again before processing
                        if ws_closed:
                            break
                        
                        message_count += 1
                        
                        # Get tokens - don't rely on message_type (it's unreliable in real-time mode)
                        tokens_list = result.get("tokens", [])
                        
                        if not tokens_list:
                            # This is normal - heartbeat message
                            if message_count % 10 == 0:
                                print(f"   📡 Soniox heartbeat (still listening...)")
                            await asyncio.sleep(0.001)
                            continue
                        
                        print(f"🔄 [{message_count}] Received {len(tokens_list)} token(s) from Soniox")
                        
                        # Process EACH token individually (partial AND final)
                        for token in tokens_list:
                            # Check if closed before processing each token
                            if ws_closed:
                                break
                            
                            is_final = token.get("is_final", False)
                            text = token.get("text", "")
                            
                            if not text:
                                continue
                            
                            # Route token to boxes (both partial and final)
                            await router.process_token(token)
                            
                            # Get updated boxes
                            boxes = router.get_boxes()
                            
                            # DEBUG: Log box contents periodically
                            if is_final:
                                print(f"   📦 Boxes state - Original: {len(boxes.get('original', ''))} chars, Doctor: {len(boxes.get('doctor', ''))} chars, Patient: {len(boxes.get('patient', ''))} chars")
                                if boxes.get('original'):
                                    print(f"      Original preview: {boxes['original'][:100]}")
                            
                            # Send to browser immediately (don't wait for is_final)
                            if not ws_closed:  # Final check before sending
                                try:
                                    token_type = "🔵 FINAL" if is_final else "⚫ PARTIAL"
                                    print(f"   {token_type}: {text[:60]}")
                                    
                                    await websocket.send_json({
                                        "type": "final" if is_final else "partial",
                                        "text": text,
                                        "is_final": is_final,
                                        "boxes": boxes,
                                        "same_language": router.same_language
                                    })
                                except Exception as e:
                                    print(f"   ❌ Error sending to browser: {e}")
                                    ws_closed = True
                                    break
                    
                    except asyncio.TimeoutError:
                        # Faster loop, don't sleep long
                        await asyncio.sleep(0.001)
                    except Exception as inner_e:
                        print(f"   ❌ Error processing token: {inner_e}")
                        await asyncio.sleep(0.01)
            
            except Exception as e:
                print(f"❌ Error in receive_from_soniox: {e}")
                ws_closed = True
                import traceback
                traceback.print_exc()
        
        # Run both tasks concurrently
        browser_task = asyncio.create_task(receive_from_browser())
        soniox_task = asyncio.create_task(receive_from_soniox())
        
        try:
            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [browser_task, soniox_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Mark as closed and cancel pending tasks
            ws_closed = True
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Task error: {e}")
        
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    
    finally:
        # Close Soniox connection
        if soniox_client:
            await soniox_client.close()
        
        # Save conversation if there's content
        if router and router.boxes.original.strip():
            try:
                original, doctor, patient = router.get_box_content()
                entries = router.get_all_entries()
                
                files = RecordingManager.save_conversation(
                    original=original,
                    doctor_text=doctor,
                    patient_text=patient,
                    entries=entries,
                    doctor_lang=doctor_lang,
                    patient_lang=patient_lang
                )
                
                # Save to database if doctor and patient info are provided
                if doctor_name and patient_id:
                    try:
                        db = get_db()
                        db.save_conversation(
                            doctor_name=doctor_name,
                            patient_id=patient_id,
                            patient_name=patient_name,
                            conversation_data={
                                'doctor_lang': doctor_lang,
                                'patient_lang': patient_lang
                            },
                            file_path=files[0] if files else ""
                        )
                    except Exception as db_error:
                        print(f"Warning: Could not save to database: {db_error}")
                
                print(f"✓ Conversation saved:")
                print(f"  - {files[0]}")
                print(f"  - {files[1]}")
                print(f"  - {files[2]}")
                
                # Send save confirmation to browser WITH the conversation text
                try:
                    await websocket.send_json({
                        "type": "saved",
                        "files": files,
                        "message": "Conversation saved successfully",
                        "conversation_text": original,  # Send the formatted text with speaker tags
                        "doctor_text": doctor,
                        "patient_text": patient
                    })
                    print(f"📤 Sent conversation text to browser ({len(original)} chars)")
                except Exception as send_error:
                    print(f"⚠️ Could not send to browser (already closed): {send_error}")
            
            except Exception as e:
                print(f"Error saving conversation: {e}")
        
        print("✓ WebSocket connection closed")


@app.get("/recordings")
async def list_recordings():
    """List all saved recordings"""
    recordings = RecordingManager.list_recordings()
    return {
        "count": len(recordings),
        "recordings": recordings
    }


@app.get("/api/get_latest_recording")
async def get_latest_recording():
    """Get the most recent recording file content"""
    try:
        import os
        import json
        from pathlib import Path
        
        recordings_dir = Path("backend/recordings")
        if not recordings_dir.exists():
            return {
                "success": False,
                "error": "Recordings directory not found"
            }
        
        # Find the most recent Orig_Lang file
        orig_files = sorted(recordings_dir.glob("Doc-patient-Orig_Lang_*.json"), 
                          key=os.path.getmtime, reverse=True)
        
        if not orig_files:
            return {
                "success": False,
                "error": "No recordings found"
            }
        
        latest_file = orig_files[0]
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruct the conversation text with speaker tags
        conversation_text = ""
        current_speaker = None
        sentence_buffer = ""
        
        for entry in data.get('entries', []):
            speaker = entry.get('speaker', 'Unknown')
            text = entry.get('text', '')
            
            # Add speaker tag when speaker changes
            if speaker != current_speaker:
                # Flush previous speaker's buffer
                if sentence_buffer and current_speaker:
                    conversation_text += f"[{current_speaker}]: {sentence_buffer}\n"
                    sentence_buffer = ""
                current_speaker = speaker
            
            # Add text to buffer
            sentence_buffer += text
            
            # If sentence ends, flush it
            if text and text[-1] in '.!?':
                conversation_text += f"[{speaker}]: {sentence_buffer}\n"
                sentence_buffer = ""
        
        # Flush any remaining buffer
        if sentence_buffer and current_speaker:
            conversation_text += f"[{current_speaker}]: {sentence_buffer}\n"
        
        print(f"📁 Retrieved latest recording: {latest_file.name}")
        print(f"   Text length: {len(conversation_text)} characters")
        print(f"   Preview: {conversation_text[:200]}")
        
        return {
            "success": True,
            "text": conversation_text,
            "filename": latest_file.name,
            "language": data.get('language', 'unknown'),
            "timestamp": data.get('timestamp', '')
        }
        
    except Exception as e:
        print(f"❌ Error retrieving recording: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/search_doctors")
async def search_doctors(q: str = ""):
    """
    Search for doctors by first_name and last_name from pces_users table.
    Returns matching doctors based on partial input.
    """
    try:
        db = get_db()
        doctors = db.search_doctors(q)
        return {
            "success": True,
            "doctors": doctors
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/search_patients")
async def search_patients(q: str = ""):
    """
    Search for patients by first_name and last_name from patient table.
    Returns matching patients based on partial input.
    """
    try:
        db = get_db()
        patients = db.search_patients(q)
        return {
            "success": True,
            "patients": patients
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Pydantic models for post-recording endpoints
class TranscriptEntry(BaseModel):
    role: str
    text: str
    start: Optional[str] = None
    end: Optional[str] = None


class ConversationPayload(BaseModel):
    transcript: str
    doctor_name: str
    patient_name: str
    patient_id: Optional[Any] = None
    doctor_lang: str
    patient_lang: str
    duration: str
    session_date: str


class PDFPayload(BaseModel):
    pdf_type: str  # "conversation", "patient_summary", "research"
    metadata: Dict[str, Any]
    transcript: Optional[List[Dict[str, str]]] = None
    raw_transcript: Optional[str] = None
    summary: Optional[str] = None
    conclusion: Optional[str] = None
    patient_problem: Optional[str] = None


@app.post("/api/transcribe_doctor_patient_conversation")
async def transcribe_doctor_patient_conversation(payload: ConversationPayload):
    """
    Post-recording endpoint: Accepts Soniox transcript and generates summary/conclusion.
    
    NOTE: This does NOT perform speech-to-text or diarization.
    Soniox output is treated as ground truth.
    
    Returns:
        conversation_data with transcript, summary, conclusion, language info
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage, SystemMessage
        
        print(f"📥 Processing conversation for {payload.doctor_name} and {payload.patient_name}")
        
        # Parse transcript (simple parsing - in production, use Soniox structured data)
        transcript_entries = []
        lines = payload.transcript.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse [Doctor]: text or [Patient]: text format
            if line.startswith('[Doctor]:'):
                transcript_entries.append({
                    "role": "Doctor",
                    "text": line.replace('[Doctor]:', '').strip(),
                    "start": None,
                    "end": None
                })
            elif line.startswith('[Patient]:'):
                transcript_entries.append({
                    "role": "Patient",
                    "text": line.replace('[Patient]:', '').strip(),
                    "start": None,
                    "end": None
                })
        
        # Generate clinical summary using LLM (optimized prompts)
        model_name = os.getenv("llm_model_name", "gpt-4.1-mini")
        llm = ChatOpenAI(model=model_name, temperature=0.3, max_tokens=300)
        print(f"🤖 Using OpenAI model: {model_name}")
        
        # Single optimized prompt - reduces API calls from 2 to 1
        combined_prompt = f"""Summarize this doctor-patient conversation in two sections:

SUMMARY: Chief complaint, symptoms, history, medications, findings.
CONCLUSION: Assessment, treatment plan, follow-up, tests needed.

Conversation:
{payload.transcript}"""

        response = llm.invoke([
            SystemMessage(content="Medical assistant."),
            HumanMessage(content=combined_prompt)
        ])
        
        # Parse response into summary and conclusion
        content = response.content
        if "CONCLUSION:" in content:
            parts = content.split("CONCLUSION:", 1)
            clinical_summary = parts[0].replace("SUMMARY:", "").strip()
            conclusion = parts[1].strip()
        else:
            # Fallback if parsing fails
            clinical_summary = content
            conclusion = "Follow up as discussed."
        
        # Build response
        conversation_data = {
            "transcript": transcript_entries,
            "raw_transcript": payload.transcript,
            "summary": clinical_summary,
            "conclusion": conclusion,
            "language": payload.patient_lang,
            "translated": payload.doctor_lang != payload.patient_lang
        }
        
        print(f"✅ Conversation processed successfully")
        
        return {
            "success": True,
            "conversation_data": conversation_data
        }
        
    except Exception as e:
        print(f"❌ Error processing conversation: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/generate_medical_summary")
async def generate_medical_summary(request: dict):
    """
    Generate medical summary and recommendations from conversation text.
    Simpler endpoint for the summary generator UI.
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage, SystemMessage
        
        conversation_text = request.get("conversation_text", "")
        
        print(f"📥 Medical summary generation request")
        print(f"   Conversation length: {len(conversation_text)} characters")
        
        if not conversation_text.strip():
            return {
                "success": False,
                "error": "No conversation text provided"
            }
        
        # Generate clinical summary and conclusion using LLM
        model_name = os.getenv("llm_model_name", "gpt-4o-mini")
        llm = ChatOpenAI(model=model_name, temperature=0.3, max_tokens=800)
        print(f"🤖 Using OpenAI model: {model_name}")
        
        # Combined prompt for efficiency
        combined_prompt = f"""Analyze this doctor-patient conversation and provide two sections:

MEDICAL SUMMARY:
- Chief complaint and presenting symptoms
- Medical history and relevant background
- Current medications (if mentioned)
- Physical examination findings (if any)
- Vital signs or test results (if mentioned)

CONCLUSION & RECOMMENDATIONS:
- Clinical assessment and diagnosis
- Treatment plan and medications prescribed
- Follow-up instructions and timeline
- Additional tests or referrals needed
- Patient education and precautions

Conversation:
{conversation_text}

Provide clear, structured medical documentation."""

        response = llm.invoke([
            SystemMessage(content="You are a medical documentation assistant. Provide clear, accurate clinical summaries."),
            HumanMessage(content=combined_prompt)
        ])
        
        # Parse response into summary and conclusion
        content = response.content
        if "CONCLUSION & RECOMMENDATIONS:" in content or "CONCLUSION AND RECOMMENDATIONS:" in content:
            parts = content.split("CONCLUSION")
            summary = parts[0].replace("MEDICAL SUMMARY:", "").strip()
            conclusion = "CONCLUSION" + parts[1] if len(parts) > 1 else ""
            conclusion = conclusion.replace("& RECOMMENDATIONS:", "").replace("AND RECOMMENDATIONS:", "").strip()
        else:
            # Fallback: split roughly in half
            lines = content.split('\n')
            mid = len(lines) // 2
            summary = '\n'.join(lines[:mid]).replace("MEDICAL SUMMARY:", "").strip()
            conclusion = '\n'.join(lines[mid:]).strip()
        
        print(f"✅ Medical summary generated successfully")
        
        return {
            "success": True,
            "summary": summary,
            "conclusion": conclusion
        }
        
    except Exception as e:
        print(f"❌ Error generating medical summary: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/translate_to_english")
async def translate_to_english(request: dict):
    """
    Translate non-English conversation text to English using OpenAI.
    Preserves speaker tags [Doctor]: and [Patient]:
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage, SystemMessage
        
        text = request.get("text", "")
        source_language = request.get("source_language", "unknown")
        
        print(f"📥 Translation request received:")
        print(f"   Source language: {source_language}")
        print(f"   Text length: {len(text)} characters")
        print(f"   Text preview (first 300 chars): {text[:300]}")
        print(f"   Text preview (last 300 chars): {text[-300:]}")
        
        if not text.strip():
            print("❌ No text provided for translation")
            return {
                "success": False,
                "error": "No text provided for translation"
            }
        
        print(f"🌐 Translating from {source_language} to English...")
        
        # Use OpenAI to translate
        model_name = os.getenv("llm_model_name", "gpt-4o-mini")
        llm = ChatOpenAI(model=model_name, temperature=0.1, max_tokens=2000)
        
        translation_prompt = f"""Translate the following medical conversation to English. 
Preserve the speaker labels [Doctor]: and [Patient]: exactly as they appear.
Maintain the conversation structure and format.

Original conversation:
{text}

Provide ONLY the English translation, maintaining the exact same format with [Doctor]: and [Patient]: labels."""

        response = llm.invoke([
            SystemMessage(content="You are a medical translator. Translate accurately while preserving medical terminology."),
            HumanMessage(content=translation_prompt)
        ])
        
        translated_text = response.content.strip()
        
        print(f"✅ Translation complete ({len(translated_text)} characters)")
        print(f"📤 Translated text preview (first 300 chars): {translated_text[:300]}")
        print(f"📤 Full translated text:\n{translated_text}")
        
        return {
            "success": True,
            "translated_text": translated_text,
            "source_language": source_language,
            "target_language": "en"
        }
        
    except Exception as e:
        print(f"❌ Translation error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/generate_pdf")
async def generate_pdf(payload: PDFPayload):
    """
    Generate PDF and upload to Azure Blob Storage.
    
    Supports three PDF types:
    - conversation: Full conversation transcript
    - patient_summary: Patient summary with clinical notes
    - research: Medical research notes
    """
    if not AZURE_AVAILABLE:
        return {
            "success": False,
            "error": "Azure storage not configured"
        }
    
    try:
        print(f"🔍 Generating PDF: type={payload.pdf_type}")
        print(f"   Metadata: {payload.metadata}")
        print(f"   Has transcript: {bool(payload.transcript)}")
        print(f"   Has raw_transcript: {bool(payload.raw_transcript)}")
        print(f"   Has summary: {bool(payload.summary)}")
        print(f"   Has conclusion: {bool(payload.conclusion)}")
        
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        from reportlab.lib.colors import HexColor
        from datetime import datetime
        import os
        
        # Create PDF in memory
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        subtitle_style = ParagraphStyle(
            'SubTitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=HexColor('#666666'),
            spaceAfter=15,
            alignment=TA_LEFT
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#0066cc'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            spaceAfter=6
        )
        
        story = []
        
        # Add logo and header
        logo_path = os.path.join(os.path.dirname(__file__), 'hospital_logo.png')
        if os.path.exists(logo_path):
            try:
                logo_img = Image(logo_path, width=1.5*inch, height=0.6*inch)
                story.append(logo_img)
                story.append(Spacer(1, 0.2*inch))
            except Exception as e:
                print(f"Warning: Could not add logo: {e}")
        
        # Generate based on PDF type
        if payload.pdf_type == "conversation":
            # Full Conversation PDF
            story.append(Paragraph("Doctor-Patient Conversation Transcript", title_style))
            story.append(Paragraph("Voice Diarization & AI-Powered Transcription", subtitle_style))
            
            # Metadata section
            session_date = payload.metadata.get('session_date', 'N/A')
            if session_date != 'N/A':
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(session_date.replace('Z', '+00:00'))
                    session_date = dt.strftime("%B %d, %Y at %I:%M %p")
                except:
                    pass
                    
            story.append(Paragraph(f"<b>Doctor:</b> {payload.metadata.get('doctor_name', 'N/A')}", normal_style))
            story.append(Paragraph(f"<b>Patient:</b> {payload.metadata.get('patient_name', 'N/A')}", normal_style))
            story.append(Paragraph(f"<b>Session Date:</b> {session_date}", normal_style))
            story.append(Paragraph(f"<b>Duration:</b> {payload.metadata.get('duration', 'N/A')}", normal_style))
            
            # Add language info if available
            doctor_lang = payload.metadata.get('doctor_lang', '')
            patient_lang = payload.metadata.get('patient_lang', '')
            if doctor_lang or patient_lang:
                langs = f"Doctor: {doctor_lang.upper() if doctor_lang else 'N/A'} | Patient: {patient_lang.upper() if patient_lang else 'N/A'}"
                story.append(Paragraph(f"<b>Languages:</b> {langs}", normal_style))
            
            story.append(Spacer(1, 0.2*inch))
            
            # Transcript section
            story.append(Paragraph("Complete Transcript", heading_style))
            if payload.transcript:
                for entry in payload.transcript:
                    speaker = entry.get('role', 'Unknown')
                    text = entry.get('text', '').strip()
                    if text:
                        # Escape XML characters
                        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(f"<b>{speaker}:</b> {text}", normal_style))
                        story.append(Spacer(1, 0.08*inch))
            elif payload.raw_transcript:
                transcript = payload.raw_transcript.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                transcript = transcript.replace('\n', '<br/>')
                story.append(Paragraph(transcript, normal_style))
            
            # Medical Summary section (if provided)
            if payload.summary:
                story.append(Spacer(1, 0.3*inch))
                story.append(Paragraph("Medical Summary", heading_style))
                summary = payload.summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                summary = summary.replace('\n', '<br/>')
                story.append(Paragraph(summary, normal_style))
            
            # Conclusion & Recommendations section (if provided)
            if payload.conclusion:
                story.append(Spacer(1, 0.3*inch))
                story.append(Paragraph("Conclusion & Recommendations", heading_style))
                conclusion = payload.conclusion.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                conclusion = conclusion.replace('\n', '<br/>')
                story.append(Paragraph(conclusion, normal_style))
            
        elif payload.pdf_type == "patient_summary":
            # Patient Summary PDF
            story.append(Paragraph("Patient Medical Summary", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Metadata
            story.append(Paragraph(f"<b>Patient:</b> {payload.metadata.get('patient_name', 'N/A')}", normal_style))
            story.append(Paragraph(f"<b>Doctor:</b> {payload.metadata.get('doctor_name', 'N/A')}", normal_style))
            story.append(Paragraph(f"<b>Date:</b> {payload.metadata.get('session_date', 'N/A')}", normal_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Clinical Summary
            story.append(Paragraph("Clinical Summary:", heading_style))
            story.append(Paragraph(payload.summary.replace('\n', '<br/>') if payload.summary else "N/A", normal_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Conclusion
            story.append(Paragraph("Conclusion & Follow-up:", heading_style))
            story.append(Paragraph(payload.conclusion.replace('\n', '<br/>') if payload.conclusion else "N/A", normal_style))
            
        elif payload.pdf_type == "research":
            # Research Notes PDF
            story.append(Paragraph("Medical Research Notes", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Metadata
            story.append(Paragraph(f"<b>Patient Problem:</b> {payload.patient_problem or 'N/A'}", normal_style))
            story.append(Paragraph(f"<b>Doctor:</b> {payload.metadata.get('doctor_name', 'N/A')}", normal_style))
            story.append(Paragraph(f"<b>Date:</b> {payload.metadata.get('session_date', 'N/A')}", normal_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Research content
            story.append(Paragraph("Clinical Summary:", heading_style))
            story.append(Paragraph(payload.summary.replace('\n', '<br/>') if payload.summary else "N/A", normal_style))
            story.append(Spacer(1, 0.2*inch))
            
            story.append(Paragraph("Recommendations:", heading_style))
            story.append(Paragraph(payload.conclusion.replace('\n', '<br/>') if payload.conclusion else "N/A", normal_style))
        
        # Build PDF
        doc.build(story)
        pdf_content = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        print(f"✅ PDF built successfully: {len(pdf_content)} bytes")
        
        if len(pdf_content) < 100:
            raise Exception(f"PDF generation produced invalid file ({len(pdf_content)} bytes)")
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        patient_name = payload.metadata.get('patient_name', 'Patient').replace(' ', '_')
        filename = f"{payload.pdf_type}_{patient_name}_{timestamp}.pdf"
        
        # Upload to Azure
        storage_manager = get_storage_manager()
        blob_url = None
        
        if payload.pdf_type == "research":
            blob_url = storage_manager.upload_research_pdf(
                pdf_content, 
                filename, 
                payload.patient_problem,
                payload.metadata
            )
        elif payload.pdf_type == "patient_summary":
            patient_data = {
                'patient_name': payload.metadata.get('patient_name'),
                'patient_id': payload.metadata.get('patient_id'),
                'doctor_name': payload.metadata.get('doctor_name'),
                'session_date': payload.metadata.get('session_date')
            }
            blob_url = storage_manager.upload_patient_summary_pdf(
                pdf_content,
                filename,
                patient_data,
                payload.metadata
            )
        elif payload.pdf_type == "conversation":
            conversation_data = {
                'doctor_name': payload.metadata.get('doctor_name'),
                'patient_name': payload.metadata.get('patient_name'),
                'duration': payload.metadata.get('duration'),
                'session_date': payload.metadata.get('session_date')
            }
            blob_url = storage_manager.upload_conversation_pdf(
                pdf_content,
                filename,
                conversation_data,
                payload.metadata
            )
        
        if not blob_url:
            raise Exception("Azure upload failed")
        
        print(f"✅ PDF uploaded to Azure: {blob_url}")
        
        # Also save locally for download
        local_dir = os.path.join(os.path.dirname(__file__), "recordings")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)
        
        with open(local_path, 'wb') as f:
            f.write(pdf_content)
        
        print(f"✅ PDF saved locally: {local_path}")
        
        return {
            "success": True,
            "blob_url": blob_url,
            "filename": filename,
            "local_path": f"/recordings/{filename}"
        }
        
    except Exception as e:
        print(f"❌ PDF generation error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    
    # Check for API key
    if not os.getenv("SONIOX_API_KEY"):
        print("⚠️ WARNING: SONIOX_API_KEY not set in environment!")
        print("Set it in .env file or environment variables")
    
    print("🚀 Starting Doctor-Patient Translator Server...")
    print("📍 Server running at http://localhost:8000")
    print("🌐 WebSocket endpoint: ws://localhost:8000/ws")
    print("📡 Health check: http://localhost:8000/health")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
