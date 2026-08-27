"""
AI client service with robust JSON extraction and offline mock mode.
Supports OpenRouter API (OpenAI-compatible format).
Target Audience: 9th-11th grade high school students in Uzbekistan.
"""
import os
import re
import json
import logging
from typing import Any, Dict, List, Optional, Union
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = getattr(settings, 'ANTHROPIC_MODEL', 'nvidia/nemotron-3.5-lightning:free')
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def extract_json_from_response(raw_text: Any) -> Union[Dict[str, Any], List[Any]]:
    """
    Extracts and parses JSON from raw LLM responses.
    Handles:
    - Already parsed dict/list objects
    - Pure JSON strings
    - Markdown fenced blocks (```json ... ``` or ``` ... ```)
    - Responses with leading or trailing conversational text
    - Trailing commas before closing brackets
    """
    if isinstance(raw_text, (dict, list)):
        return raw_text

    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("Bo'sh yoki yaroqsiz javob matni berildi.")

    text = raw_text.strip()

    # 1. Direct parse attempt
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Extract from markdown code fence ```json ... ``` or ``` ... ```
    fence_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    matches = re.findall(fence_pattern, text, re.IGNORECASE)
    for match in matches:
        candidate = match.strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Try cleaning trailing commas
            cleaned = re.sub(r',\s*([\]}])', r'\1', candidate)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                continue

    # 3. Use JSONDecoder.raw_decode to find valid JSON dict/list starting anywhere in text
    decoder = json.JSONDecoder()
    for i in range(len(text)):
        if text[i] in ('{', '['):
            try:
                obj, _ = decoder.raw_decode(text[i:])
                if isinstance(obj, (dict, list)):
                    return obj
            except Exception:
                pass

    # 3. Locate outermost JSON structure ({ ... } or [ ... ])
    start_brace = text.find('{')
    start_bracket = text.find('[')

    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        start_idx = start_brace
        end_idx = text.rfind('}')
        if end_idx > start_idx:
            candidate = text[start_idx:end_idx + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                cleaned = re.sub(r',\s*([\]}])', r'\1', candidate)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass
    elif start_bracket != -1:
        start_idx = start_bracket
        end_idx = text.rfind(']')
        if end_idx > start_idx:
            candidate = text[start_idx:end_idx + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                cleaned = re.sub(r',\s*([\]}])', r'\1', candidate)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass

    # Last resort: try every { and [ position in the text
    for i, ch in enumerate(text):
        if ch in ('{', '['):
            close = '}' if ch == '{' else ']'
            end_idx = text.rfind(close)
            if end_idx > i:
                candidate = text[i:end_idx + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    cleaned = re.sub(r',\s*([\]}])', r'\1', candidate)
                    try:
                        return json.loads(cleaned)
                    except json.JSONDecodeError:
                        continue

    raise ValueError(f"Matndan yaroqli JSON ajratib olinmadi:\n{text[:200]}...")


class ClaudeClient:
    """
    AI client using OpenRouter API (OpenAI-compatible format).
    Default model: nvidia/nemotron-3.5-lightning:free
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, timeout: float = 12.0):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY', '') or getattr(settings, 'ANTHROPIC_API_KEY', '')
        self.model = model or getattr(settings, 'ANTHROPIC_MODEL', DEFAULT_MODEL)
        self.timeout = timeout

    def is_mock(self) -> bool:
        return False

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = 'text',
        max_tokens: int = 2048
    ) -> Union[str, Dict[str, Any], List[Any]]:
        import httpx

        # For JSON responses, prepend a strict JSON-only instruction so that
        # "thinking" style models don't output reasoning prose before the JSON.
        effective_system = system_prompt
        if response_format == 'json':
            effective_system = (
                "CRITICAL INSTRUCTION: Respond with ONLY raw valid JSON. "
                "Do NOT write any thinking, reasoning, explanation, or prose. "
                "Do NOT use markdown code fences. "
                "Your entire response must start with '{' or '[' and end with '}' or ']'.\n\n"
            ) + system_prompt

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Study Abroad Platform",
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": effective_system},
                {"role": "user", "content": user_prompt},
            ]
        }

        try:
            response = httpx.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            raw_text = data['choices'][0]['message']['content']

            if response_format == 'json':
                return extract_json_from_response(raw_text)
            return raw_text
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API HTTP Error {e.response.status_code}: {e.response.text}")
            raise RuntimeError(f"OpenRouter API xatosi: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"OpenRouter API murojaatida xatolik: {e}")
            raise


class MockClaudeClient(ClaudeClient):
    """
    Deterministic offline mock client for development, testing, and offline environments.
    Inspects prompts to return context-appropriate, schema-valid Uzbek responses.
    """
    def is_mock(self) -> bool:
        return True

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = 'text',
        max_tokens: int = 2048
    ) -> Union[str, Dict[str, Any], List[Any]]:
        logger.info("MockClaudeClient: Offline mock javobi generatsiya qilinmoqda.")
        prompt_lower = (system_prompt + " " + user_prompt).lower()

        if response_format == 'json':
            # 1. Study Plan Intent
            if any(k in prompt_lower for k in ["study_plan", "o'quv rejasi", "o'quv rejasini", "rejasi", "study plan"]):
                return {
                    "title": "Xalqaro Grantlar Uchun Shaxsiy O'quv Rejasi",
                    "summary": "9-11 sinf o'quvchisi uchun xalqaro grantlar va universitetlarga tayyorgarlik bo'yicha haftalik amaliy reja.",
                    "total_weeks": 12,
                    "weekly_hours": 10,
                    "weakest_skill": "grammar",
                    "weakest_skill_strategy": "Har kuni 20 daqiqa grammatika qoidalarini amaliy testlar va misollar orqali mustahkamlash.",
                    "weekly_schedule": [
                        {
                            "week": 1,
                            "focus": "Grammar Foundation & Reading Strategies",
                            "goals": ["Tense system & complex sentences", "Skimming and scanning techniques"],
                            "daily_hours": 1.5,
                            "milestone": "1-haftalik testdan 75+ ball olish"
                        },
                        {
                            "week": 2,
                            "focus": "Essay Structure & Academic Vocabulary",
                            "goals": ["Paragraph development", "50 ta yangi akademik so'z yodlash"],
                            "daily_hours": 1.5,
                            "milestone": "Birinchi to'liq inshoni yozish"
                        }
                    ],
                    "milestones": [
                        {"title": "Boshlang'ich grammatika bazasi", "target_week": 4, "description": "Asosiy grammatik xatolarni 50% ga kamaytirish."},
                        {"title": "Akademik insho loyihasi", "target_week": 8, "description": "Global UGRAD/DAAD talablariga mos motivatsion insho tayyorlash."},
                        {"title": "Yakuniy tayyorgarlik darajasi", "target_week": 12, "description": "Tayyorgarlik ko'rsatkichini 85+ ballga yetkazish."}
                    ],
                    "daily_routine_tips": [
                        "Ertalab 15 daqiqa ingliz tilida maqola o'qing.",
                        "Kechqurun 2 ta kunlik vazifani to'liq bajaring va AI tushuntirishini tahlil qiling.",
                        "Yangi so'zlarni kontekstda gap tuzib mustahkamlang."
                    ],
                    "motivational_advice": "Har kungi kichik intizom katta xalqaro grantlarning kalitidir. AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."
                }

            # 2. Diagnostic Grading Intent
            if any(k in prompt_lower for k in ["diagnostic", "diagnostika", "baseline", "5 skills", "grade this diagnostic"]):
                return {
                    "scores": {
                        "reading": 75,
                        "grammar": 70,
                        "writing": 68,
                        "listening": 65,
                        "speaking": 62
                    },
                    "overall_ready_score": 68,
                    "weakest_skill": "speaking",
                    "feedback": {
                        "reading": "Matnlarni tushunish va asosiy g'oyani ilg'ash qobiliyati yaxshi shakllangan.",
                        "grammar": "Murakkab grammatik zamonlar va shart mayllarini qo'llashda aniqlikni oshirish lozim.",
                        "writing": "Insho strukturasi tushunarli, dalillarni boyitish ustida ishlash tavsiya etiladi.",
                        "listening": "Akademik suhbatlar va podcastlarni muntazam tinglash ko'nikmani oshiradi.",
                        "speaking": "Intervyu savollariga to'liq va ravon javob berish amaliyotini kuchaytiring."
                    },
                    "summary_uz": "Boshlang'ich natija mustahkam poydevorga ega. Grammatika va insho yozish ko'nikmalarini har kuni mashq qilish tavsiya etiladi."
                }

            # 3. Task Grading Intent
            if any(k in prompt_lower for k in ["grade_task", "baholash", "vazifa turi", "task score", "evaluate task", "topshiriq"]):
                return {
                    "score": 100,
                    "completed": True,
                    "ai_feedback": "Ajoyib! Javobingiz to'g'ri va mantiqan asoslangan. Ushbu qoidani amaliyotda to'g'ri qo'llay olishingiz grant insholarida akademik aniqlikni ta'minlaydi. Present Perfect zamonining o'tgan zamondagi natijasi to'g'ri ko'rsatilgan."
                }

            # 4. Daily Task Generation Intent
            if any(k in prompt_lower for k in ["tasks", "kunlik vazifa", "grammar_drill", "reading_comprehension"]):
                return {
                    "tasks": [
                        {
                            "task_type": "grammar_drill",
                            "content": {
                                "title": "Grammar Drill: Conditional Sentences",
                                "skill": "grammar",
                                "instruction": "To'g'ri javobni tanlang va qisqacha izohlang.",
                                "question": "If Aziz ________ (apply) for the Global UGRAD exchange program earlier, he would have secured the full sponsorship.",
                                "options": [
                                    {"key": "A", "text": "applied"},
                                    {"key": "B", "text": "had applied"},
                                    {"key": "C", "text": "has applied"},
                                    {"key": "D", "text": "would apply"}
                                ],
                                "correct_option": "B",
                                "explanation": "Third Conditional o'tgan zamondagi amalga oshmagan shartni ifodalaydi: If + Past Perfect (had applied), ... would have + V3."
                            }
                        },
                        {
                            "task_type": "reading_comprehension",
                            "content": {
                                "title": "Reading Comprehension: Statement of Purpose Structure",
                                "skill": "reading",
                                "passage": "An effective Statement of Purpose (SOP) for international undergraduate grants must articulate a coherent narrative. Rather than merely listing academic accolades, strong applicants connect their past leadership projects in Uzbekistan with their future vision.",
                                "question": "What distinguishes a compelling Statement of Purpose according to the text?",
                                "options": [
                                    {"key": "A", "text": "Listing awards without narrative context."},
                                    {"key": "B", "text": "Connecting past leadership experiences with a clear future vision and community impact."},
                                    {"key": "C", "text": "Focusing solely on foreign travel."},
                                    {"key": "D", "text": "Only submitting test scores."}
                                ],
                                "correct_option": "B",
                                "explanation": "Matnda kuchli arizachilar o'tmishdagi yetakchilik tajribalarini kelajak rejalari va vataniga hissa qo'shish bilan bog'lashi ta'kidlangan."
                            }
                        }
                    ]
                }

            # Generic JSON fallback
            return {
                "status": "success",
                "message": "Mock Claude JSON response",
                "scores": {"reading": 75, "grammar": 70, "writing": 68, "listening": 65, "speaking": 62},
                "overall_ready_score": 68,
                "weakest_skill": "speaking",
                "data": {}
            }

        # Text response format for AI Mentor Chat
        # Check if student is asking about unverified programs or fake grants
        verified_programs = ["global ugrad", "daad", "chevening", "türkiye bursları", "turkiye burslari", "el-yurt umidi"]
        
        # Check for unverified program trigger keywords
        unverified_keywords = ["fake", "noma'lum", "soxta", "unverified", "mars scholarship", "random grant", "super grant"]
        if any(bad_kw in user_prompt.lower() for bad_kw in unverified_keywords):
            return "Men bu haqda tasdiqlangan ma'lumotga ega emasman. AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."
        
        # If user asks about a specific program not in verified database
        if any(word in user_prompt.lower() for word in ["grant", "dastur", "program", "scholarship"]):
            mentions_verified = any(prog in user_prompt.lower() for prog in verified_programs)
            mentions_system_verified = any(prog in system_prompt.lower() for prog in verified_programs)
            # If user asks about a specific named scholarship not in verified programs
            if not mentions_verified and ("haqida" in user_prompt.lower() or "talablari" in user_prompt.lower() or "qanday" in user_prompt.lower()) and any(w in user_prompt.lower() for w in ["universitet", "grant", "burs", "scholarship"]):
                # If specific foreign program name mentioned that isn't recognized
                words = user_prompt.split()
                if len(words) > 2 and any(cap.istitle() for cap in words if cap not in ["Men", "Salom", "Qanday", "Qachon", "Assalomu", "Alaykum"]):
                    if not any(prog in user_prompt.lower() for prog in verified_programs):
                        return "Men bu haqda tasdiqlangan ma'lumotga ega emasman. AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."

        return (
            "Assalomu alaykum! Men sizning xalqaro ta'lim bo'yicha AI mentoringizman. "
            "Sizga o'qish rejalari, tasdiqlangan grant talablari va kunlik vazifalar bo'yicha yo'l-yo'riq beraman. "
            "Eslatib o'taman, barcha takliflarimiz yo'naltiruvchi xarakterga ega. "
            "AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."
        )


def get_claude_client(api_key: Optional[str] = None) -> ClaudeClient:
    """
    Factory returning ClaudeClient or MockClaudeClient depending on API key configuration.
    """
    key = api_key or os.getenv('ANTHROPIC_API_KEY', '') or getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not key or key.strip().lower() in ('mock', 'test', 'offline', 'none', ''):
        return MockClaudeClient()
    return ClaudeClient(api_key=key)


def call_claude(
    system_prompt: str,
    user_prompt: str,
    response_format: str = 'text',
    max_tokens: int = 2048
) -> Union[str, Dict[str, Any], List[Any]]:
    """
    Central helper facade to invoke Claude API or Mock fallback.
    """
    client = get_claude_client()
    return client.call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format=response_format,
        max_tokens=max_tokens
    )
