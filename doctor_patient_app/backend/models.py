"""
Pydantic models for type safety and validation
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class TokenData(BaseModel):
    """Transcription token from Soniox"""
    text: str
    is_final: bool
    speaker: Optional[str] = None
    language: Optional[str] = None
    translation_status: str = "none"
    source_language: Optional[str] = None


class ConversationEntry(BaseModel):
    """Single conversation entry for storage"""
    timestamp: str
    speaker: str
    text: str
    language: str
    translation_status: str = "none"


class BoxBuffers:
    """Three-box display for doctor-patient conversation"""
    
    def __init__(self):
        self.original = ""          # Box 1: original with speaker tags
        self.doctor_lang = ""       # Box 2: Doctor language
        self.patient_lang = ""      # Box 3: Patient language
        self._last_speaker = None
        self.entries = []           # Store all entries for JSON export
    
    def add_to_original(self, speaker: Optional[str], text: str, timestamp: str = None):
        """Add to original box with speaker tag"""
        if not text:
            return
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        if speaker and speaker != self._last_speaker:
            self.original += f"\n[{speaker}]: "
            self._last_speaker = speaker
        
        self.original += text
        
        # Store entry for export
        if speaker:
            self.entries.append({
                "timestamp": timestamp,
                "speaker": speaker,
                "text": text,
                "language": "original",
                "translation_status": "original"
            })
    
    def add_to_doctor(self, text: str, timestamp: str = None):
        """Add to doctor's language view"""
        if not text:
            return
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        self.doctor_lang += text
    
    def add_to_patient(self, text: str, timestamp: str = None):
        """Add to patient's language view"""
        if not text:
            return
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        self.patient_lang += text
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for UI"""
        return {
            "original": self.original[-2000:] or "[Waiting for speech...]",
            "doctor": self.doctor_lang[-2000:] or "[Waiting for speech...]",
            "patient": self.patient_lang[-2000:] or "[Waiting for speech...]",
        }
    
    def reset(self):
        """Reset all buffers"""
        self.original = ""
        self.doctor_lang = ""
        self.patient_lang = ""
        self._last_speaker = None
        self.entries = []


class RecordingMetadata(BaseModel):
    """Metadata for saved recordings"""
    filename: str
    duration: float
    doctor_language: str
    patient_language: str
    timestamp: str
    total_entries: int
