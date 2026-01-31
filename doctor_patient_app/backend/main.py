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
from dotenv import load_dotenv

from soniox_ws import SonioxWSClient
from langchain_router import LangChainRouter
from audio_stream import AudioStreamProcessor
from utils import RecordingManager

load_dotenv()

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
try:
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
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
    
    try:
        # Wait for initial config
        init_data = await websocket.receive_json()
        doctor_lang = init_data.get("doctor_lang", "en")
        patient_lang = init_data.get("patient_lang", "te")
        
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
                await soniox_client.end_stream()
            except Exception as e:
                print(f"Error receiving from browser: {e}")
                try:
                    await soniox_client.end_stream()
                except:
                    pass
        
        async def receive_from_soniox():
            """Receive tokens from Soniox and send to browser"""
            try:
                message_count = 0
                while True:
                    try:
                        result = await soniox_client.receive_tokens()
                        
                        if result is None:
                            await asyncio.sleep(0.01)
                            continue
                        
                        message_count += 1
                        
                        # Get tokens - don't rely on message_type (it's unreliable in real-time mode)
                        tokens_list = result.get("tokens", [])
                        
                        if not tokens_list:
                            # This is normal - heartbeat message
                            if message_count % 5 == 0:
                                print(f"   📡 Soniox heartbeat (still listening...)")
                            await asyncio.sleep(0.01)
                            continue
                        
                        print(f"🔄 [{message_count}] Received {len(tokens_list)} token(s) from Soniox")
                        
                        # Process EACH token individually (partial AND final)
                        for token in tokens_list:
                            is_final = token.get("is_final", False)
                            text = token.get("text", "")
                            
                            if not text:
                                continue
                            
                            # Route token to boxes (both partial and final)
                            await router.process_token(token)
                            
                            # Get updated boxes
                            boxes = router.get_boxes()
                            
                            # Send to browser immediately (don't wait for is_final)
                            try:
                                token_type = "🔵 FINAL" if is_final else "⚫ PARTIAL"
                                print(f"   {token_type}: {text[:60]}")
                                
                                await websocket.send_json({
                                    "type": "final" if is_final else "partial",
                                    "text": text,
                                    "is_final": is_final,
                                    "boxes": boxes
                                })
                            except Exception as e:
                                print(f"   ❌ Error sending to browser: {e}")
                                break
                    
                    except asyncio.TimeoutError:
                        await asyncio.sleep(0.01)
                    except Exception as inner_e:
                        print(f"   ❌ Error processing token: {inner_e}")
                        await asyncio.sleep(0.01)
            
            except Exception as e:
                print(f"❌ Error in receive_from_soniox: {e}")
                import traceback
                traceback.print_exc()
        
        # Run both tasks concurrently - use gather so both run until one errors
        try:
            await asyncio.gather(
                receive_from_browser(),
                receive_from_soniox(),
                return_exceptions=False
            )
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
                
                print(f"✓ Conversation saved:")
                print(f"  - {files[0]}")
                print(f"  - {files[1]}")
                print(f"  - {files[2]}")
                
                # Send save confirmation to browser
                try:
                    await websocket.send_json({
                        "type": "saved",
                        "files": files,
                        "message": "Conversation saved successfully"
                    })
                except:
                    pass
            
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
