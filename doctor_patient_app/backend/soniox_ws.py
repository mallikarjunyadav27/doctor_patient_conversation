"""
Soniox WebSocket client for real-time transcription
Handles connection, config, and token streaming
"""
import os
import json
import asyncio
import websockets
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

WS_URL = "wss://stt-rt.soniox.com/transcribe-websocket"

class SonioxWSClient:
    """WebSocket client for Soniox STT API"""
    
    def __init__(self):
        self.ws = None
        self.api_key = os.getenv("SONIOX_API_KEY", "")
        self.model = os.getenv("SONIOX_MODEL", "stt-rt-v3")
        self.doctor_lang = "en"
        self.patient_lang = "te"
        self.config_sent = False
        self.connected = False
    
    async def connect(self, doctor_lang: str = "en", patient_lang: str = "te"):
        """Initialize WebSocket connection to Soniox"""
        if not self.api_key:
            raise ValueError("SONIOX_API_KEY not set in environment")
        
        # Validate: Languages must be different (Soniox requirement)
        if doctor_lang == patient_lang:
            raise ValueError(f"Doctor and Patient languages must be different. Got: {doctor_lang} and {patient_lang}")
        
        # Debug: Show API key status (masked for security)
        key_preview = f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "***"
        print(f"🔑 Soniox API Key: {key_preview} (length: {len(self.api_key)})")
        print(f"📡 Model: {self.model}")
        print(f"🗣️  Languages: Doctor={doctor_lang}, Patient={patient_lang}")
        
        self.doctor_lang = doctor_lang
        self.patient_lang = patient_lang
        
        try:
            # Build URL with query parameters (Soniox expects params, not JSON config)
            url = f"{WS_URL}?apikey={self.api_key}&model={self.model}"
            print(f"🔗 Connecting to: {WS_URL}?apikey=****&model={self.model}")
            
            self.ws = await websockets.connect(url, max_size=8 * 1024 * 1024)
            self.connected = True
            
            # Send initial config as JSON after connection
            config = self._build_config()
            config_json = json.dumps(config)
            print(f"📤 Sending config JSON ({len(config_json)} bytes)...")
            await self.ws.send(config_json)
            self.config_sent = True
            
            print(f"✓ Connected to Soniox API")
        except Exception as e:
            print(f"❌ Connection error: {e}")
            raise
    
    def _build_config(self) -> Dict[str, Any]:
        """Build Soniox config JSON"""
        config = {
            "api_key": self.api_key,
            "model": self.model,
            "audio_format": "pcm_s16le",
            "sample_rate": 16000,
            "num_channels": 1,
            "language_hints": [self.doctor_lang, self.patient_lang],
            "enable_speaker_diarization": True,
            "enable_endpoint_detection": True,
            "render": "everything",  # Returns all forms (original + translations)
            "translation": {
                "type": "two_way",
                "language_a": self.doctor_lang,
                "language_b": self.patient_lang
            },
            "enable_language_identification": True,
        }
        print(f"📋 Soniox Config: {json.dumps(config, indent=2)}")
        return config
    
    async def send_audio(self, chunk: bytes):
        """Send audio chunk to Soniox"""
        if not self.connected or not self.ws:
            raise RuntimeError("Not connected to Soniox")
        
        try:
            await self.ws.send(chunk)
        except websockets.exceptions.ConnectionClosed:
            print("Soniox connection closed unexpectedly")
            self.connected = False
            raise
    
    async def receive_tokens(self) -> Optional[Dict[str, Any]]:
        """Receive tokens from Soniox"""
        if not self.ws or not self.connected:
            return None
        
        try:
            msg = await asyncio.wait_for(self.ws.recv(), timeout=30.0)
            if msg:
                data = json.loads(msg)
                
                # Debug: Show what we received
                msg_type = data.get('message_type', 'unknown')
                error_code = data.get('error_code')
                error_msg = data.get('error_message')
                tokens = data.get('tokens', [])
                
                print(f"DEBUG Soniox: type={msg_type}, error_code={error_code}, tokens={len(tokens) if isinstance(tokens, list) else 'N/A'}")
                
                if error_code:
                    print(f"⚠️  Soniox Error: Code={error_code}, Message={error_msg}")
                
                return data
        except asyncio.TimeoutError:
            # No message received but connection still active
            return None
        except websockets.exceptions.ConnectionClosed:
            print("ERROR: Soniox connection closed")
            self.connected = False
            return None
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to decode JSON from Soniox: {e}")
            return None
        except Exception as e:
            print(f"ERROR in receive_tokens: {e}")
            return None
        
        return None
    
    async def end_stream(self):
        """Send end-of-stream marker"""
        if self.ws and self.connected:
            try:
                print("📤 Sending end-of-stream marker to Soniox...")
                await self.ws.send(b"")
                print("✓ Sent end-of-stream marker")
                # Give Soniox time to process
                await asyncio.sleep(0.5)
            except websockets.exceptions.ConnectionClosed:
                print("ERROR: Soniox already disconnected")
            except Exception as e:
                print(f"ERROR sending end-of-stream: {e}")
    
    async def close(self):
        """Close WebSocket connection"""
        await self.end_stream()
        if self.ws:
            try:
                await self.ws.close()
                self.connected = False
            except Exception as e:
                print(f"Error closing connection: {e}")
