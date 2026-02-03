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
        
        # Track speakers for diarization fallback
        self.speaker_registry = {}  # Map speaker_id to label
        self.last_detected_speaker_id = None
        self.speaker_id_counter = 0
        
        # For turn-based detection when speaker_id unavailable
        self.sentence_count = 0  # Count sentences to alternate speakers
        self.last_sentence_had_punctuation = False
        
        if self.same_language:
            print(f"✓ LangChain Router: Same language mode ({doctor_lang})")
            print(f"   Using speaker diarization to distinguish Doctor/Patient")
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
        # NOTE: Soniox provides 'speaker' key, not 'speaker_id'
        speaker_id = token.get("speaker") or token.get("speaker_id")
        language = token.get("language") or token.get("detected_language", "unknown")
        is_final = token.get("is_final", False)
        
        # DEBUG: Log full token structure to understand Soniox format
        if is_final and text and text != "<end>":
            print(f"     DEBUG TOKEN KEYS: {list(token.keys())}")
            print(f"     DEBUG: speaker={speaker_id}, language={language}, text='{text[:40]}'...")
        
        # IMPROVED SPEAKER DETECTION
        speaker_label = self._detect_speaker(speaker_id, language)
        
        # Log speaker assignment on change
        if speaker_label != self.current_speaker:
            print(f"     🔄 SPEAKER CHANGE: {self.current_speaker} → {speaker_label}")
            self.current_speaker = speaker_label
        
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
            # Final token - send to boxes with current speaker
            self._route_to_boxes(text, speaker_label, language, translation_status, timestamp)
            
            # Check if this sentence ends, and prepare for speaker switch
            self.check_speaker_change(text)
            
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
        
        # If same language mode:
        # - ONLY add if speech language matches configured language
        # - Skip any detected different language (e.g., if patient speaks Telugu but we selected English)
        if self.same_language:
            # In same-language mode, only add to Box 1 if language matches config
            if speaker == "Doctor" and language == self.doctor_lang:
                self.boxes.add_to_original(speaker, text, timestamp)
            elif speaker == "Patient" and language == self.patient_lang:
                self.boxes.add_to_original(speaker, text, timestamp)
            # Skip any speech in different language
            return
        
        # Translation mode: Add to all appropriate boxes
        # Box 1: Original transcript (spoken language + speaker tag)
        self.boxes.add_to_original(speaker, text, timestamp, language)
        
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
    def _detect_speaker(self, speaker_id, language: str) -> str:
        """
        Detect speaker label from speaker_id and language
        Falls back to turn-based detection when speaker_id unavailable
        """
        # First priority: Use explicit speaker_id if provided (speaker diarization)
        if speaker_id is not None and speaker_id != -1:
            # Register speaker if not seen before
            if speaker_id not in self.speaker_registry:
                # Map first speaker to Doctor, second to Patient
                if len(self.speaker_registry) == 0:
                    self.speaker_registry[speaker_id] = "Doctor"
                    print(f"     🎤 Speaker {speaker_id} detected → Doctor (DIARIZATION)")
                elif len(self.speaker_registry) == 1:
                    self.speaker_registry[speaker_id] = "Patient"
                    print(f"     🎤 Speaker {speaker_id} detected → Patient (DIARIZATION)")
                else:
                    label = f"Speaker{speaker_id}"
                    self.speaker_registry[speaker_id] = label
                    print(f"     🎤 Speaker {speaker_id} detected → {label} (DIARIZATION)")
            
            return self.speaker_registry[speaker_id]
        
        # Second priority: Use language detection (translation mode only)
        if not self.same_language and language and language != "unknown":
            if language == self.doctor_lang:
                return "Doctor"
            elif language == self.patient_lang:
                return "Patient"
        
        # FALLBACK: Turn-based detection for same-language mode
        # Since Soniox speaker diarization might not work in same-language mode,
        # we alternate speakers on sentence boundaries (endings with . ! ?)
        if self.current_speaker is None:
            # First speaker is always Doctor
            self.current_speaker = "Doctor"
            self.sentence_count = 1
            return "Doctor"
        
        # Keep current speaker until we see a full sentence (ending with punctuation)
        return self.current_speaker
    
    def check_speaker_change(self, text: str) -> str:
        """
        Check if text ends with sentence-ending punctuation
        If yes, prepare to switch speaker on next token
        """
        if not text:
            return self.current_speaker
        
        # Check if text ends with sentence-ending punctuation
        has_ending_punct = text.rstrip().endswith(('.', '!', '?'))
        
        if has_ending_punct and self.current_speaker:
            # Switch speaker on next turn
            if self.current_speaker == "Doctor":
                next_speaker = "Patient"
            else:
                next_speaker = "Doctor"
            
            self.sentence_count += 1
            print(f"     🔄 Sentence end detected (#{self.sentence_count}): {self.current_speaker} → {next_speaker}")
            self.current_speaker = next_speaker
        
        return self.current_speaker