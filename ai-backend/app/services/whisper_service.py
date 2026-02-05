"""
Whisper Transcription Service for Viva Voce System

This service handles audio-to-text transcription using Groq's Whisper API.
Groq provides free, fast Whisper transcription that's perfect for our use case.

Why Groq Whisper?
- FREE tier available (same as our LLM calls)
- Faster than OpenAI's Whisper (Groq's speed advantage)
- Same API format we're already using
- Supports multiple audio formats
"""

import httpx
import base64
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from app.core.config import settings


class TranscriptionStatus(Enum):
    """Status of transcription attempt"""
    SUCCESS = "success"
    AUDIO_TOO_SHORT = "audio_too_short"
    AUDIO_TOO_LONG = "audio_too_long"
    INVALID_FORMAT = "invalid_format"
    API_ERROR = "api_error"
    NO_SPEECH_DETECTED = "no_speech_detected"


@dataclass
class TranscriptionResult:
    """Result of audio transcription"""
    status: TranscriptionStatus
    text: Optional[str] = None
    duration_seconds: Optional[float] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    error_message: Optional[str] = None


class WhisperService:
    """
    Handles audio transcription for Viva Voce oral examinations.
    
    Flow:
    1. Frontend records student's verbal explanation
    2. Audio blob sent to backend
    3. This service transcribes to text
    4. Text passed to semantic verification
    """
    
    # Groq Whisper endpoint
    WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    # Constraints
    MIN_DURATION_SECONDS = 1.0
    MAX_DURATION_SECONDS = 120.0  # 2 minutes max for explanation
    
    # Supported formats
    SUPPORTED_FORMATS = {"mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "ogg"}
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.webm",
        language: str = "en"
    ) -> TranscriptionResult:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_data: Raw audio bytes from frontend
            filename: Original filename (for format detection)
            language: Expected language code (default: English)
            
        Returns:
            TranscriptionResult with text or error
        """
        # Validate format from filename
        extension = filename.split(".")[-1].lower() if "." in filename else "webm"
        if extension not in self.SUPPORTED_FORMATS:
            return TranscriptionResult(
                status=TranscriptionStatus.INVALID_FORMAT,
                error_message=f"Unsupported format: {extension}. Use: {self.SUPPORTED_FORMATS}"
            )
        
        # Check minimum size (rough estimate - 1KB per second for compressed audio)
        if len(audio_data) < 1000:
            return TranscriptionResult(
                status=TranscriptionStatus.AUDIO_TOO_SHORT,
                error_message="Audio too short. Please record at least 1 second."
            )
        
        # Check maximum size (rough estimate - 100KB per second for high quality)
        max_size = int(self.MAX_DURATION_SECONDS * 100 * 1024)
        if len(audio_data) > max_size:
            return TranscriptionResult(
                status=TranscriptionStatus.AUDIO_TOO_LONG,
                error_message=f"Audio too long. Maximum {self.MAX_DURATION_SECONDS} seconds."
            )
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Prepare multipart form data
                files = {
                    "file": (filename, audio_data, f"audio/{extension}")
                }
                data = {
                    "model": "whisper-large-v3",  # Groq's Whisper model
                    "language": language,
                    "response_format": "verbose_json"  # Get detailed response
                }
                headers = {
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                response = await client.post(
                    self.WHISPER_URL,
                    files=files,
                    data=data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    text = result.get("text", "").strip()
                    
                    # Check for empty transcription
                    if not text:
                        return TranscriptionResult(
                            status=TranscriptionStatus.NO_SPEECH_DETECTED,
                            error_message="No speech detected in audio."
                        )
                    
                    return TranscriptionResult(
                        status=TranscriptionStatus.SUCCESS,
                        text=text,
                        duration_seconds=result.get("duration"),
                        language=result.get("language", language),
                        confidence=self._calculate_confidence(result)
                    )
                else:
                    error_detail = response.json().get("error", {}).get("message", response.text)
                    return TranscriptionResult(
                        status=TranscriptionStatus.API_ERROR,
                        error_message=f"Transcription failed: {error_detail}"
                    )
                    
        except httpx.TimeoutException:
            return TranscriptionResult(
                status=TranscriptionStatus.API_ERROR,
                error_message="Transcription timed out. Please try again."
            )
        except Exception as e:
            return TranscriptionResult(
                status=TranscriptionStatus.API_ERROR,
                error_message=f"Transcription error: {str(e)}"
            )
    
    def _calculate_confidence(self, result: dict) -> float:
        """
        Calculate overall confidence from Whisper response.
        Whisper doesn't provide direct confidence, so we estimate from segments.
        """
        segments = result.get("segments", [])
        if not segments:
            return 0.8  # Default confidence if no segments
        
        # Average of segment-level metrics (if available)
        # Whisper segments have 'no_speech_prob' - lower is better
        no_speech_probs = [s.get("no_speech_prob", 0) for s in segments]
        avg_no_speech = sum(no_speech_probs) / len(no_speech_probs)
        
        # Convert to confidence (invert no_speech probability)
        return round(1.0 - avg_no_speech, 2)
    
    async def transcribe_base64(
        self,
        base64_audio: str,
        filename: str = "audio.webm",
        language: str = "en"
    ) -> TranscriptionResult:
        """
        Convenience method for base64-encoded audio.
        Frontend might send audio as base64 string.
        """
        try:
            # Remove data URL prefix if present
            if "," in base64_audio:
                base64_audio = base64_audio.split(",")[1]
            
            audio_bytes = base64.b64decode(base64_audio)
            return await self.transcribe_audio(audio_bytes, filename, language)
        except Exception as e:
            return TranscriptionResult(
                status=TranscriptionStatus.INVALID_FORMAT,
                error_message=f"Invalid base64 audio: {str(e)}"
            )


# Singleton instance
whisper_service = WhisperService()
