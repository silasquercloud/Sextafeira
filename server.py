import os
import json
import uuid
import requests

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

AGNES_KEY = os.getenv("AGNES_KEY")

AGNES_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
MODEL = "agnes-2.5-flash"

MEMORY_FILE = "memory.json"


# =========================
# MEMÓRIA
# =========================

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


memory = load_memory()


def get_user(user_id):
    if user_id not in memory:
        memory[user_id] = {
            "history": [],
            "memories": []
        }

    return memory[user_id]


# =========================
# PERSONALIDADE
# =========================

SYSTEM_PROMPT = """
Você é Sexta Feira, uma assistente pessoal de inteligência artificial.

Seu nome é Sexta Feira.

Nunca diga que seu nome é Agnes.
Nunca diga que você é Agnes.
Nunca mencione o provedor usado nos bastidores.

Você deve conversar naturalmente como uma assistente pessoal.

Seja inteligente, direta, amigável e útil.

Você possui memória. Use as informações fornecidas em
"MEMÓRIAS DO USUÁRIO" quando forem relevantes.

Não invente memórias.

Você está sendo executada dentro de um aplicativo chamado Sexta Feira.
"""


# =========================
# MODELO
# =========================

class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None


# =========================
# CHAT
# =========================

@app.post("/api/chat")
def chat(request: ChatRequest):

    if not AGNES_KEY:
        return {
            "error": "AGNES_KEY não configurada no Render."
        }

    user_id = request.user_id or str(uuid.uuid4())

    user = get_user(user_id)

    memories = user["memories"]

    memory_text = "\n".join(
        f"- {item}"
        for item in memories
    )

    if not memory_text:
        memory_text = "Nenhuma memória registrada."

    system = SYSTEM_PROMPT

    system += "\n\nMEMÓRIAS DO USUÁRIO:\n"
    system += memory_text

    messages = [
        {
            "role": "system",
            "content": system
        }
    ]

    messages.extend(
        user["history"][-20:]
    )

    messages.append({
        "role": "user",
        "content": request.message
    })

    try:

        response = requests.post(
            AGNES_URL,
            headers={
                "Authorization": f"Bearer {AGNES_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048
            },
            timeout=90
        )

        data = response.json()

        if response.status_code != 200:

            print("AGNES ERROR:", data)

            return {
                "error": "Erro ao consultar a inteligência artificial."
            }

        answer = data["choices"][0]["message"]["content"]

        # Salva conversa
        user["history"].append({
            "role": "user",
            "content": request.message
        })

        user["history"].append({
            "role": "assistant",
            "content": answer
        })

        user["history"] = user["history"][-20:]

        save_memory(memory)

        return {
            "user_id": user_id,
            "answer": answer
        }

    except Exception as e:

        print("ERROR:", e)

        return {
            "error": "Não consegui conectar à inteligência artificial."
        }


# =========================
# MEMÓRIA
# =========================

@app.get("/api/memory/{user_id}")
def get_memory(user_id: str):

    user = get_user(user_id)

    return {
        "memories": user["memories"]
    }


@app.delete("/api/memory/{user_id}")
def clear_memory(user_id: str):

    user = get_user(user_id)

    user["memories"] = []
    user["history"] = []

    save_memory(memory)

    return {
        "success": True
    }


# =========================
# SITE
# =========================

@app.get("/")
def home():
    return FileResponse("index.html")


@app.get("/style.css")
def css():
    return FileResponse("style.css")


@app.get("/app.js")
def javascript():
    return FileResponse("app.js")


# =========================
# RENDER
# =========================

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.environ.get("PORT", 10000)
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
