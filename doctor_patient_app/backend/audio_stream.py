"""
Audio stream helpers for processing browser PCM audio
Handles audio buffering and chunking
"""
import numpy as np
from typing import Optional


class AudioStreamProcessor:
    """Process audio streams from browser"""
    
    SAMPLE_RATE = 16000
    CHANNELS = 1
    CHUNK_SIZE = 1600  # 100ms at 16kHz
    
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.buffer = np.array([], dtype=np.int16)
        self.total_samples = 0
    
    def add_chunk(self, chunk: bytes) -> Optional[bytes]:
        """
        Add audio chunk and return processed chunk if ready
        Returns PCM bytes ready for transcription
        """
        # Convert bytes to numpy array
        audio_data = np.frombuffer(chunk, dtype=np.int16)
        self.buffer = np.append(self.buffer, audio_data)
        self.total_samples += len(audio_data)
        
        # Return chunk if buffer exceeds threshold
        if len(self.buffer) >= self.CHUNK_SIZE:
            output = self.buffer[:self.CHUNK_SIZE].tobytes()
            self.buffer = self.buffer[self.CHUNK_SIZE:]
            return output
        
        return None
    
    def flush(self) -> Optional[bytes]:
        """Return remaining audio in buffer"""
        if len(self.buffer) > 0:
            output = self.buffer.tobytes()
            self.buffer = np.array([], dtype=np.int16)
            return output
        return None
    
    def get_buffer_size(self) -> int:
        """Get current buffer size in samples"""
        return len(self.buffer)
    
    def get_duration(self) -> float:
        """Get duration of audio processed in seconds"""
        return self.total_samples / self.sample_rate
    
    def clear(self):
        """Clear the buffer"""
        self.buffer = np.array([], dtype=np.int16)
        self.total_samples = 0
