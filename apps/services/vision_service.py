import base64
import logging
from typing import Dict, Any
from apps.services.anthropic_client import get_claude_client

logger = logging.getLogger(__name__)

def evaluate_portfolio_image(image_path: str, title: str, description: str) -> Dict[str, Any]:
    """
    Evaluates an art/design portfolio image using Claude 3.5 Sonnet Vision.
    """
    try:
        with open(image_path, "rb") as image_file:
            binary_data = image_file.read()
            base64_encoded = base64.b64encode(binary_data).decode("utf-8")
        
        # Determine media type (very basic fallback to jpeg)
        media_type = "image/jpeg"
        if image_path.lower().endswith('.png'):
            media_type = "image/png"
        elif image_path.lower().endswith('.webp'):
            media_type = "image/webp"

        client = get_claude_client(timeout=60.0)
        
        system_prompt = (
            "Sen xalqaro universitetlarning San'at, Arxitektura va Dizayn yo'nalishlariga qabul "
            "komissiyasi a'zosisan. O'quvchining portfoliosidagi rasmni tahlil qil va o'zbek tilida (Latin) baho ber. "
            "1. Rasmning kompozitsiyasi, ranglar va texnikasini bahola. "
            "2. G'oyaning o'ziga xosligi (originality). "
            "3. Nimalarni yaxshilash kerakligi haqida amaliy maslahat ber. "
            "Javobni quyidagi JSON formatda ber: "
            '{"score": <0-100 son>, "feedback": "<tahliliy matn>"}'
        )

        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_encoded,
                            }
                        },
                        {
                            "type": "text",
                            "text": f"Loyiha nomi: {title}\nTavsifi: {description}\nIltimos, ushbu asarni qabul komissiyasi nuqtai nazaridan baholang."
                        }
                    ]
                }
            ]
        )
        
        raw_text = message.content[0].text.strip()
        import json
        import re
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return {
                "score": int(data.get("score", 0)),
                "feedback": str(data.get("feedback", ""))
            }
        return {"score": 50, "feedback": raw_text}

    except Exception as e:
        logger.error(f"Vision API error: {e}")
        return {"score": 0, "feedback": f"Texnik xatolik yuz berdi: {e}"}
