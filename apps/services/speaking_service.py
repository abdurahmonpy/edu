"""
Service for processing voice-based speaking practice sessions.
"""
import logging
import random
from typing import Dict, Any, Tuple
from django.conf import settings
from .anthropic_client import get_claude_client

logger = logging.getLogger(__name__)

# Basic IELTS Part 2 Prompts for MVP
PART2_PROMPTS = [
    "Describe a book that had a major influence on you. You should say: what the book is, how you found out about it, what it is about, and explain why it had such a major influence on you.",
    "Describe a difficult challenge you faced and how you overcame it. You should say: what the challenge was, when you faced it, what you did to overcome it, and explain how you felt afterwards.",
    "Describe an important decision you made recently. You should say: what the decision was, why you had to make it, who helped you make it, and explain whether you think it was the right decision.",
    "Describe a memorable journey you have taken. You should say: where you went, how you travelled, who you went with, and explain why this journey was so memorable.",
]

def get_random_part2_prompt() -> str:
    """Return a random IELTS Part 2 cue card prompt."""
    return random.choice(PART2_PROMPTS)

def transcribe_audio(audio_file) -> str:
    """
    Stub for Speech-to-Text (STT) transcription.
    In a real implementation, this would send `audio_file` to OpenAI Whisper API or similar.
    Since we don't have OPENAI_API_KEY confirmed in the env, we return a mock transcript.
    """
    logger.info("Transcribing audio (mock STT)...")
    return "Well, the book that really influenced me was Atomic Habits by James Clear. I found out about it through a friend who recommended it to me when I was struggling with procrastination. Basically, it's about how tiny changes can lead to remarkable results. It had a huge influence on me because it shifted my mindset from focusing on big goals to focusing on systems and daily habits. I realized that getting 1 percent better every day is the key to long-term success."

def evaluate_speaking(transcript: str, prompt_text: str, speak_time_seconds: int) -> Tuple[float, str]:
    """
    Evaluates the transcript using the Claude API based on IELTS criteria.
    Returns (band_score, ai_feedback).
    """
    if not transcript or not transcript.strip():
        return 0.0, "Kechirasiz, sizning ovozingiz (yoki matningiz) tushunarsiz. Iltimos, qaytadan urinib ko'ring."

    client = get_claude_client()
    
    system_prompt = """
You are an expert IELTS Speaking examiner evaluating a student's Part 2 response.
You will be provided with the prompt (cue card) and the transcript of the student's recorded audio.
Keep in mind this is an automated STT transcript, so punctuation might be auto-generated or missing.

Evaluate the response based on the following criteria (out of 9.0):
1. Fluency and Coherence (judged from length, completeness, and structure in the text)
2. Lexical Resource (vocabulary range and accuracy)
3. Grammatical Range and Accuracy
NOTE: You cannot evaluate Pronunciation accurately without audio, so do not invent pronunciation flaws.

Return a JSON object with this exact structure:
{
  "band_score": 6.5,
  "feedback": "Detailed feedback covering strengths and areas for improvement, written in clear Uzbek."
}
"""

    user_prompt = f"""
Prompt / Cue Card: {prompt_text}

Student Transcript ({speak_time_seconds} seconds spoken):
"{transcript}"
"""
    
    try:
        response_json = client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format='json'
        )
        band_score = float(response_json.get('band_score', 0.0))
        feedback = str(response_json.get('feedback', 'Baholashda xatolik yuz berdi.'))
        return band_score, feedback
    except Exception as e:
        logger.error(f"Error evaluating speaking: {e}")
        return 0.0, f"Xatolik: {str(e)}"
