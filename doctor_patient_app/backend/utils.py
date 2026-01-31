"""
Utility functions for file I/O, JSON handling, and data persistence
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class RecordingManager:
    """Manage recording files and metadata"""
    
    RECORDINGS_DIR = Path("recordings")
    
    @classmethod
    def ensure_dir(cls):
        """Ensure recordings directory exists"""
        cls.RECORDINGS_DIR.mkdir(exist_ok=True, parents=True)
    
    @classmethod
    def save_conversation(
        cls, 
        original: str, 
        doctor_text: str, 
        patient_text: str,
        entries: List[Dict[str, Any]],
        doctor_lang: str = "en",
        patient_lang: str = "te"
    ) -> tuple:
        """
        Save conversation to three separate JSON files
        Returns: (original_file, doctor_file, patient_file)
        """
        cls.ensure_dir()
        
        timestamp = datetime.now().strftime("%m%d%Y_%H_%M")
        
        # Prepare data
        original_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "original",
            "language": "mixed",
            "entries": entries,
            "full_text": original
        }
        
        doctor_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "doctor_view",
            "language": doctor_lang,
            "full_text": doctor_text
        }
        
        patient_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "patient_view",
            "language": patient_lang,
            "full_text": patient_text
        }
        
        # Create filenames
        original_file = f"Doc-patient-Orig_Lang_{timestamp}.json"
        doctor_file = f"Doc-patient-{doctor_lang.upper()}_{timestamp}.json"
        patient_file = f"Doc-patient-{patient_lang.upper()}_{timestamp}.json"
        
        # Save files
        original_path = cls.RECORDINGS_DIR / original_file
        doctor_path = cls.RECORDINGS_DIR / doctor_file
        patient_path = cls.RECORDINGS_DIR / patient_file
        
        with open(original_path, "w", encoding="utf-8") as f:
            json.dump(original_data, f, ensure_ascii=False, indent=2)
        
        with open(doctor_path, "w", encoding="utf-8") as f:
            json.dump(doctor_data, f, ensure_ascii=False, indent=2)
        
        with open(patient_path, "w", encoding="utf-8") as f:
            json.dump(patient_data, f, ensure_ascii=False, indent=2)
        
        return str(original_path), str(doctor_path), str(patient_path)
    
    @classmethod
    def load_recording(cls, filename: str) -> Optional[Dict[str, Any]]:
        """Load recording by filename"""
        filepath = cls.RECORDINGS_DIR / filename
        
        if not filepath.exists():
            return None
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @classmethod
    def list_recordings(cls) -> list:
        """List all saved recordings"""
        cls.ensure_dir()
        return sorted([f.name for f in cls.RECORDINGS_DIR.glob("Doc-patient-*.json")])


def format_timestamp() -> str:
    """Get formatted timestamp"""
    return datetime.now().isoformat()
