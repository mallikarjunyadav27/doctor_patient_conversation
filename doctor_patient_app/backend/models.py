# backend/models.py

from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import unicodedata

# =========================
# Helper functions
# =========================

def is_indic_char(ch: str) -> bool:
    """Check if character belongs to Indic Unicode blocks"""
    if not ch:
        return False
    block = unicodedata.name(ch, "")
    return any(x in block for x in [
        "TELUGU", "DEVANAGARI", "TAMIL", "KANNADA",
        "MALAYALAM", "BENGALI", "GURMUKHI", "ORIYA"
    ])

def smart_join(existing: str, new: str) -> str:
    """
    Join streamed Soniox tokens verbatim.

    Soniox real-time tokens already carry their own spacing (typically a leading
    space on each new word, no space before punctuation, and no spaces for Indic
    scripts). The correct behavior — as shown in Soniox's own reference loop
    (`"".join(token.text)`) — is to concatenate token text as-is. Any heuristic
    re-spacing here is what previously produced fragmented output (e.g. "se e").
    """
    if not existing:
        return new
    if not new:
        return existing
    return existing + new


# =========================
# Data models
# =========================

class ConversationEntry(BaseModel):
    timestamp: str
    speaker: str
    text: str
    language: str
    translation_status: str


# =========================
# Three-box buffer
# =========================

class BoxBuffers:
    """
    Maintains 3 UI boxes:
    1. Original
    2. Doctor language
    3. Patient language
    """

    def __init__(self):
        self.original = ""
        self.doctor = ""
        self.patient = ""

        self._last_original_speaker = None
        self._last_doctor_speaker = None
        self._last_patient_speaker = None
        
        # Buffers for building complete sentences
        self._original_sentence_buffer = ""
        self._doctor_sentence_buffer = ""
        self._patient_sentence_buffer = ""
        
        # Track current speaker per box to know when to add tags
        self._original_current_speaker = None
        self._doctor_current_speaker = None
        self._patient_current_speaker = None

        self.entries: List[Dict] = []

    # -------- Box 1 --------
    def add_to_original(self, speaker: str, text: str, timestamp: str, language: str = None):
        """Buffer tokens and display only complete sentences (ends with . ! ?)"""
        if not text or not speaker:
            return
        
        # Add speaker tag only when speaker changes
        if speaker != self._original_current_speaker:
            # If buffer has content, flush it first (speaker changed mid-sentence)
            if self._original_sentence_buffer and self._original_current_speaker:
                self.original += f"[{self._original_current_speaker}]: {self._original_sentence_buffer.strip()}\n"
                self._original_sentence_buffer = ""
            # New speaker starts
            self._original_current_speaker = speaker
        
        # Add token to buffer
        self._original_sentence_buffer = smart_join(self._original_sentence_buffer, text)
        
        # Only flush when sentence is complete (ends with . ! ?)
        if self._original_sentence_buffer and self._original_sentence_buffer[-1] in '.!?':
            # Sentence complete - display full sentence
            self.original += f"[{speaker}]: {self._original_sentence_buffer.strip()}\n"
            self._original_sentence_buffer = ""

        self.entries.append({
            "timestamp": timestamp,
            "speaker": speaker,
            "text": text,
            "language": "original",
            "translation_status": "original"
        })

    # -------- Box 2 --------
    def add_to_doctor(self, speaker: str, text: str, timestamp: str, language: str):
        """Buffer tokens and display only complete sentences (ends with . ! ?)"""
        if not text or not speaker:
            return
        
        # Add speaker tag only when speaker changes
        if speaker != self._doctor_current_speaker:
            # If buffer has content, flush it first (speaker changed mid-sentence)
            if self._doctor_sentence_buffer and self._doctor_current_speaker:
                self.doctor += f"[{self._doctor_current_speaker}]: {self._doctor_sentence_buffer.strip()}\n"
                self._doctor_sentence_buffer = ""
            # New speaker starts
            self._doctor_current_speaker = speaker
        
        # Add token to buffer
        self._doctor_sentence_buffer = smart_join(self._doctor_sentence_buffer, text)
        
        # Only flush when sentence is complete (ends with . ! ?)
        if self._doctor_sentence_buffer and self._doctor_sentence_buffer[-1] in '.!?':
            # Sentence complete - display full sentence
            self.doctor += f"[{speaker}]: {self._doctor_sentence_buffer.strip()}\n"
            self._doctor_sentence_buffer = ""

        self.entries.append({
            "timestamp": timestamp,
            "speaker": speaker,
            "text": text,
            "language": language,
            "translation_status": "doctor"
        })

    # -------- Box 3 --------
    def add_to_patient(self, speaker: str, text: str, timestamp: str, language: str):
        """Buffer tokens and display only complete sentences (ends with . ! ?)"""
        if not text or not speaker:
            return
        
        # Add speaker tag only when speaker changes
        if speaker != self._patient_current_speaker:
            # If buffer has content, flush it first (speaker changed mid-sentence)
            if self._patient_sentence_buffer and self._patient_current_speaker:
                self.patient += f"[{self._patient_current_speaker}]: {self._patient_sentence_buffer.strip()}\n"
                self._patient_sentence_buffer = ""
            # New speaker starts
            self._patient_current_speaker = speaker
        
        # Add token to buffer
        self._patient_sentence_buffer = smart_join(self._patient_sentence_buffer, text)
        
        # Only flush when sentence is complete (ends with . ! ?)
        if self._patient_sentence_buffer and self._patient_sentence_buffer[-1] in '.!?':
            # Sentence complete - display full sentence
            self.patient += f"[{speaker}]: {self._patient_sentence_buffer.strip()}\n"
            self._patient_sentence_buffer = ""

        self.entries.append({
            "timestamp": timestamp,
            "speaker": speaker,
            "text": text,
            "language": language,
            "translation_status": "patient"
        })

    # -------- Helpers --------
    def to_dict(self) -> Dict[str, str]:
        return {
            "original": self.original or "",
            "doctor": self.doctor or "",
            "patient": self.patient or "",
        }

    def reset(self):
        self.original = ""
        self.doctor = ""
        self.patient = ""
        self._last_original_speaker = None
        self._last_doctor_speaker = None
        self._last_patient_speaker = None
        self._original_sentence_buffer = ""
        self._doctor_sentence_buffer = ""
        self._patient_sentence_buffer = ""
        self._original_current_speaker = None
        self._doctor_current_speaker = None
        self._patient_current_speaker = None
        self.entries.clear()
