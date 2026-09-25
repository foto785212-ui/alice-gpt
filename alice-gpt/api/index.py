import os
import re
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

# Открытый бесплатный шлюз (не требует регистрации и VPN)
client = OpenAI(
    api_key="dummy",
    base_url="https://text.pollinations.ai/openai"
)

def clean_for_speech(text: str) -> str:
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'[*_#`~>\[\]\(\)]', '', text)
    text = re.sub(r'\n+', ' ', text)
    return text.strip()

@app.api_route("/{path:path}", methods=["GET", "POST"])
@app.api_route("/", methods=["GET", "POST"])
async def yandex_webhook(request: Request, path: str = ""):
    if request.method == "GET":
        return {"status": "ok", "message": "Alice GPT Webhook is running"}

    req_data = await request.json()
    session = req_data.get("session", {})
    request_obj = req_data.get("request", {})
    user_command = request_obj.get("original_utterance", "").strip()
    is_new_session = session.get("new", False)

    if is_new_session or not user_command:
        return {
            "version": req_data.get("version", "1.0"),
            "session": session,
            "response": {
                "text": "Привет! Я голосовой помощник на базе нейросети. О чём хотите поговорить?",
                "end_session": False
            }
        }

    if user_command.lower() in ["стоп", "выход", "хватит", "пока"]:
        return {
            "version": req_data.get("version", "1.0"),
            "session": session,
            "response": {
                "text": "До встречи!",
                "end_session": True
            }
        }

    try:
        completion = client.chat.completions.create(
            model="openai",  # Использует базовую модель GPT бесплатно
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты голосовой ассистент на Яндекс Станции. "
                        "Отвечай на русском языке кратко, ёмко и понятно на слух (не более 2-3 предложений). "
                        "Не используй списки, markdown, спецсимволы и ссылки."
                    )
                },
                {"role": "user", "content": user_command}
            ],
            max_tokens=150,
            temperature=0.7
        )
        answer = completion.choices[0].message.content
        answer_text = clean_for_speech(answer)
    except Exception as e:
        answer_text = "Не удалось связаться с нейросетью. Попробуйте еще раз."

    return {
        "version": req_data.get("version", "1.0"),
        "session": session,
        "response": {
            "text": answer_text,
            "end_session": False
        }
    }
