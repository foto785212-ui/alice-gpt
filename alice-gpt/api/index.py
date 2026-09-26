import os
import re
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

# Подключение к сверхбыстрому шлюзу Groq
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def clean_for_speech(text: str) -> str:
    """Удаляет markdown, ссылки и спецсимволы для чистого произношения колонкой"""
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'[*_#`~>\[\]\(\)]', '', text)
    text = re.sub(r'\n+', ' ', text)
    return text.strip()

@app.api_route("/{path:path}", methods=["GET", "POST"])
@app.api_route("/", methods=["GET", "POST"])
async def yandex_webhook(request: Request, path: str = ""):
    # Ответ на технические проверки
    if request.method == "GET":
        return {"status": "ok", "message": "Alice Groq Webhook is running"}

    req_data = await request.json()
    session = req_data.get("session", {})
    request_obj = req_data.get("request", {})
    user_command = request_obj.get("original_utterance", "").strip()
    is_new_session = session.get("new", False)

    # Приветствие при старте диалога
    if is_new_session or not user_command:
        return {
            "version": req_data.get("version", "1.0"),
            "session": session,
            "response": {
                "text": "Привет! Я на связи через Ламу. О чём спросите?",
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

    # Запрос к передовой модели Llama 3.3 70B (отвечает за 0.3-0.5 сек)
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты голосовой ассистент на Яндекс Станции. "
                        "Отвечай на русском языке кратко, ёмко и понятно на слух (максимум 2-3 предложения). "
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
        print(f"Ошибка Groq: {e}")
        answer_text = "Не удалось связаться с нейросетью. Попробуйте повторить вопрос."

    return {
        "version": req_data.get("version", "1.0"),
        "session": session,
        "response": {
            "text": answer_text,
            "end_session": False
        }
    }
