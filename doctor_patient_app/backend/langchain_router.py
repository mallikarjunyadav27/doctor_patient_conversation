"""
LangChain-inspired router for formatting and routing transcription tokens
Handles logic for separating Doctor/Patient views and translations
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from models import BoxBuffers


class LangChainRouter:
    """
    Routes and formats tokens based on language and speaker
    Acts as a normalizer/processor between Soniox events and UI updates
    """
    
    def __init__(self, doctor_lang: str = "en", patient_lang: str = "te"):
        self.doctor_lang = doctor_lang
        self.patient_lang = patient_lang
        self.boxes = BoxBuffers()
        self.token_buffer = []
    
    async def process_token(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single token and return formatted version
        Routes to appropriate boxes
        """
        if not token:
            return None
        
        # Extract token fields - Soniox format
        text = token.get("text") or token.get("utterance", "")
        if not text:
            return None
        
        # Get speaker info from token
        speaker_id = token.get("speaker_id")
        speaker = token.get("speaker") or f"Speaker {speaker_id}" if speaker_id else "Unknown"
        
        # Get language and translation info
        language = token.get("language") or token.get("detected_language", "unknown")
        is_final = token.get("is_final", False)
        translated = token.get("translated", False)
        
        # Determine translation status
        if translated:
            translation_status = "translation"
        elif token.get("is_translation"):
            translation_status = "translation"
        else:
            translation_status = "original"
        
        timestamp = token.get("timestamp") or datetime.now().isoformat()
        
        # Create formatted token
        formatted_token = {
            "text": text,
            "speaker": speaker,
            "language": language,
            "translation_status": translation_status,
            "timestamp": timestamp,
            "is_final": is_final
        }
        
        print(f"     Token: text='{text[:50]}...', lang={language}, status={translation_status}, speaker={speaker}")
        
        # Route to boxes based on content type
        self._route_to_boxes(text, speaker, language, translation_status, timestamp)
        
        return formatted_token
    
    def _route_to_boxes(
        self, 
        text: str, 
        speaker: str,
        language: str,
        status: str,
        timestamp: str
    ):
        """Route token to appropriate boxes"""
        
        # Box 1: Original transcript (spoken language + speaker tag)
        if status in ("none", "original"):
            self.boxes.add_to_original(speaker, text, timestamp)
        
        # Box 2: Doctor's view (in doctor language)
        # Include:
        # - Original doctor speech
        # - Translation of patient speech to doctor language
        if language == self.doctor_lang:
            if status in ("original", "translation", "none"):
                self.boxes.add_to_doctor(text, timestamp)
        
        # Box 3: Patient's view (in patient language)
        # Include:
        # - Original patient speech
        # - Translation of doctor speech to patient language
        if language == self.patient_lang:
            if status in ("original", "translation", "none"):
                self.boxes.add_to_patient(text, timestamp)
    
    async def format_result(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Format Soniox result for frontend display
        Process all tokens in result
        """
        # Check for errors first
        error_code = result.get("error_code")
        if error_code:
            print(f"   ❌ ERROR from Soniox: code={error_code}, msg={result.get('error_message', 'unknown')}")
            return []
        
        # Handle different message types from Soniox
        message_type = result.get("message_type", "")
        tokens = []
        
        if message_type == "result":
            # Standard result with tokens array
            tokens = result.get("tokens", [])
        elif message_type == "response":
            # Alternative format
            tokens = result.get("response", {}).get("tokens", [])
        elif "tokens" in result:
            # Direct tokens array (Soniox might not include message_type)
            tokens = result.get("tokens", [])
        
        formatted_tokens = []
        
        if not tokens:
            print(f"   DEBUG: No tokens found in result. Message type: {message_type}, Keys: {list(result.keys())}")
            return formatted_tokens
        
        print(f"   DEBUG: Processing {len(tokens)} tokens from message_type: {message_type}")
        
        for token in tokens:
            formatted = await self.process_token(token)
            if formatted:
                formatted_tokens.append(formatted)
        
        return formatted_tokens
    
    def get_boxes(self) -> Dict[str, str]:
        """Get current state of all three boxes"""
        return self.boxes.to_dict()
    
    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Get all conversation entries for export"""
        return self.boxes.entries
    
    def get_box_content(self) -> tuple:
        """Get raw box content for export"""
        return (
            self.boxes.original,
            self.boxes.doctor_lang,
            self.boxes.patient_lang
        )
    
    def reset(self):
        """Reset router state"""
        self.boxes.reset()
        self.token_buffer = []
    
    def set_languages(self, doctor_lang: str, patient_lang: str):
        """Update language settings"""
        self.doctor_lang = doctor_lang
        self.patient_lang = patient_lang
