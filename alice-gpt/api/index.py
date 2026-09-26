import os
import re
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

def clean_for_speech(text: str) -> str:
    """Очистка текста от markdown для голосового ответа"""
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'[*_#`~>\[\]\(\)]', '', text)
    text = re.sub(r'\n+', ' ', text)
    return text.strip()

@app.api_route("/{path:path}", methods=["GET", "POST"])
@app.api_route("/", methods=["GET", "POST"])
async def yandex_webhook(request: Request, path: str = ""):
    # Проверка работы через браузер
    if request.method == "GET":
        return {"status": "ok", "message": "Alice Groq Webhook is running"}

    # Безопасное чтение JSON-запроса от Яндекса
    try:
        req_data = await request.json()
    except Exception:
        req_data = {}

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

    # Получаем ключ (поддерживаем оба варианта названия переменной)
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {
            "version": req_data.get("version", "1.0"),
            "session": session,
            "response": {
                "text": "Ошибка: ключ API не найден в переменных Vercel. Добавьте GROQ_API_KEY в настройках проекта.",
                "end_session": False
            }
        }

    # Обращение к Groq
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
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
        print(f"Ошибка вызова модели: {e}")
        answer_text = f"Ошибка от Groq: {str(e)[:120]}"

    return {
        "version": req_data.get("version", "1.0"),
        "session": session,
        "response": {
            "text": answer_text,
            "end_session": False
        }
    }
