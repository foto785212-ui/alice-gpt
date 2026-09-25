import os
import re
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

# Клиент OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def clean_for_speech(text: str) -> str:
    """Удаление markdown и спецсимволов для чистого голосового ответа"""
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'[*_#`~>\[\]\(\)]', '', text)
    text = re.sub(r'\n+', ' ', text)
    return text.strip()

# Принимаем любые пути и методы (GET и POST), чтобы никогда не возникало 404
@app.api_route("/{path:path}", methods=["GET", "POST"])
@app.api_route("/", methods=["GET", "POST"])
async def yandex_webhook(request: Request, path: str = ""):
    # Ответ на проверку доступности браузером или пингом
    if request.method == "GET":
        return {"status": "ok", "message": "Alice GPT Webhook is running"}

    req_data = await request.json()
    
    session = req_data.get("session", {})
    request_obj = req_data.get("request", {})
    user_command = request_obj.get("original_utterance", "").strip()
    is_new_session = session.get("new", False)

    # Приветствие при старте сессии
    if is_new_session or not user_command:
        return {
            "version": req_data.get("version", "1.0"),
            "session": session,
            "response": {
                "text": "Привет! Я на связи с чатом джи пи ти. О чём спросите?",
                "end_session": False
            }
        }

    # Выход по ключевым словам
    if user_command.lower() in ["стоп", "выход", "хватит", "пока"]:
        return {
            "version": req_data.get("version", "1.0"),
            "session": session,
            "response": {
                "text": "До встречи!",
                "end_session": True
            }
        }

    # Запрос к ChatGPT
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты голосовой ассистент на Яндекс Станции. "
                        "Отвечай кратко, ёмко и понятно на слух (не более 2-3 предложений). "
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
        answer_text = "Не удалось связаться с нейросетью. Попробуйте повторить вопрос."

    return {
        "version": req_data.get("version", "1.0"),
        "session": session,
        "response": {
            "text": answer_text,
            "end_session": False
        }
    }
