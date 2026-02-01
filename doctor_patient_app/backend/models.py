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
    Join streamed tokens safely:
    - Preserve Indic grapheme clusters
    - Preserve English word spacing
    """
    if not existing:
        return new

    if not new:
        return existing

    last_char = existing[-1]
    first_char = new[0]

    # Indic scripts → NEVER add space
    if is_indic_char(last_char) or is_indic_char(first_char):
        return existing + new

    # English / Latin scripts
    if last_char.isalnum() and first_char.isalnum():
        return existing + " " + new

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

        self.entries: List[Dict] = []

    # -------- Box 1 --------
    def add_to_original(self, speaker: str, text: str, timestamp: str):
        if speaker != self._last_original_speaker:
            if self.original:
                self.original += "\n"
            self.original += f"[{speaker}]: "
            self._last_original_speaker = speaker

        self.original = smart_join(self.original, text)

        self.entries.append({
            "timestamp": timestamp,
            "speaker": speaker,
            "text": text,
            "language": "original",
            "translation_status": "original"
        })

    # -------- Box 2 --------
    def add_to_doctor(self, speaker: str, text: str, timestamp: str, language: str):
        if speaker != self._last_doctor_speaker:
            if self.doctor:
                self.doctor += "\n"
            self.doctor += f"[{speaker}]: "
            self._last_doctor_speaker = speaker

        self.doctor = smart_join(self.doctor, text)

        self.entries.append({
            "timestamp": timestamp,
            "speaker": speaker,
            "text": text,
            "language": language,
            "translation_status": "doctor"
        })

    # -------- Box 3 --------
    def add_to_patient(self, speaker: str, text: str, timestamp: str, language: str):
        if speaker != self._last_patient_speaker:
            if self.patient:
                self.patient += "\n"
            self.patient += f"[{speaker}]: "
            self._last_patient_speaker = speaker

        self.patient = smart_join(self.patient, text)

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
        self.entries.clear()
