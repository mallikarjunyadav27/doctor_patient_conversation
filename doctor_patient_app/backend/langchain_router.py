"""
LangChain-inspired router for formatting and routing transcription tokens
Handles logic for separating Doctor/Patient views and translations
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import re
from models import BoxBuffers


class LangChainRouter:
    """
    Routes and formats tokens based on language and speaker
    Acts as a normalizer/processor between Soniox events and UI updates
    """
    
    def __init__(self, doctor_lang: str = "en", patient_lang: str = "en"):
        self.doctor_lang = doctor_lang
        self.patient_lang = patient_lang
        self.boxes = BoxBuffers()
        self.partial_buffer = {}  # Buffer for partial tokens by speaker
        self.current_speaker = None
        self.speaker_changed = False
        # Check if same language (optimization)
        self.same_language = (doctor_lang == patient_lang)
        if self.same_language:
            print(f"✓ LangChain Router: Same language mode ({doctor_lang})")
        else:
            print(f"✓ LangChain Router: Translation mode ({doctor_lang} ↔ {patient_lang})")
    
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
        
        # Ensure text is a string (not object or list)
        if not isinstance(text, str):
            text = str(text)
        
        # Clean up text - remove artifacts
        text = text.replace("<end>", "").strip()
        
        # Remove timestamp patterns like "{o}: 2026-02-01T17:57:44.621955"
        text = re.sub(r'\{[^}]*\}:\s*\d{4}-\d{2}-\d{2}T[\d:\.]+', '', text).strip()
        
        if not text:
            return None
        
        # Get speaker info from token
        speaker_id = token.get("speaker_id", 0)
        language = token.get("language") or token.get("detected_language", "unknown")
        is_final = token.get("is_final", False)
        
        # SMART SPEAKER DETECTION: Map speaker to Doctor or Patient based on language
        if self.same_language:
            # In same language mode, use speaker_id to distinguish
            if speaker_id == 0:
                speaker_label = "Doctor"
            elif speaker_id == 1:
                speaker_label = "Patient"
            else:
                speaker_label = f"Speaker {speaker_id}"
        else:
            # In translation mode, detect speaker by language
            if language == self.doctor_lang:
                speaker_label = "Doctor"
            elif language == self.patient_lang:
                speaker_label = "Patient"
            else:
                # Fallback to speaker_id
                speaker_label = f"Speaker {speaker_id}"
        
        # Determine translation status
        translated = token.get("translated", False)
        is_translation = token.get("is_translation", False)
        
        if translated or is_translation:
            translation_status = "translation"
        else:
            translation_status = "original"
        
        timestamp = token.get("timestamp") or datetime.now().isoformat()
        
        # Create formatted token with speaker label
        formatted_token = {
            "text": text,
            "speaker": speaker_label,
            "language": language,
            "translation_status": translation_status,
            "timestamp": timestamp,
            "is_final": is_final
        }
        
        timestamp = token.get("timestamp") or datetime.now().isoformat()
        
        # ===== CRITICAL FIX: Only route FINAL tokens to boxes =====
        if is_final:
            # Final token - send to boxes
            self.current_speaker = speaker_label
            self._route_to_boxes(text, speaker_label, language, translation_status, timestamp)
            
            # Clear partial buffer for this speaker after final token
            if speaker_label in self.partial_buffer:
                del self.partial_buffer[speaker_label]
            
            print(f"     ✓ [{speaker_label}] {translation_status} (FINAL): {text[:60]}")
        else:
            # Partial token - buffer only, DON'T route to boxes
            self.partial_buffer[speaker_label] = text
            print(f"     ⌚ [{speaker_label}] {translation_status} (partial): {text[:60]}...")
        
        return {
            "speaker": speaker_label,
            "text": text,
            "language": language,
            "is_final": is_final,
            "translation_status": translation_status,
            "partial_buffer": self.partial_buffer.copy() if not is_final else {}
        }
    
    def _route_to_boxes(
        self, 
        text: str, 
        speaker: str,
        language: str,
        status: str,
        timestamp: str
    ):
        """Route token to appropriate boxes - ONLY for FINAL tokens"""
        
        # Box 1: Original transcript (spoken language + speaker tag)
        self.boxes.add_to_original(speaker, text, timestamp)
        
        # If same language, don't populate Box 2 and Box 3 (save translation cost)
        if self.same_language:
            return
        
        # Box 2: Doctor's view (in doctor language)
        # Add if:
        # - Text is in doctor language (original doctor speech)
        # - OR text is a translation TO doctor language (translated patient speech)
        if language == self.doctor_lang or status == "translation":
            self.boxes.add_to_doctor(speaker, text, timestamp, language=language)
        
        # Box 3: Patient's view (in patient language)
        # Add if:
        # - Text is in patient language (original patient speech)
        # - OR text is a translation TO patient language (translated doctor speech)
        if language == self.patient_lang or status == "translation":
            self.boxes.add_to_patient(speaker, text, timestamp, language=language)
    
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
