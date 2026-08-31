import os
import json
import uuid
import base64
import requests

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel


app = FastAPI()

# ============================================================
# CONFIGURAÇÃO
# ============================================================

AGNES_KEY = os.getenv("AGNES_KEY")

BASE_URL = "https://apihub.agnes-ai.com"

CHAT_URL = f"{BASE_URL}/v1/chat/completions"
IMAGE_URL = f"{BASE_URL}/v1/images/generations"
VIDEO_URL = f"{BASE_URL}/v1/videos"

CHAT_MODEL = "agnes-2.5-flash"
IMAGE_MODEL = "agnes-image-2.1-flash"
VIDEO_MODEL = "agnes-video-v2.0"

MEMORY_FILE = "memory.json"

MAX_HISTORY = 30
MAX_MEMORIES = 100


# ============================================================
# PERSONALIDADE
# ============================================================

SYSTEM_PROMPT = """
Você é Sexta Feira, uma assistente pessoal de inteligência artificial.

Seu nome é Sexta Feira.

Nunca diga que seu nome é Agnes.
Nunca diga que você é Agnes.
Agnes é apenas o provedor de IA utilizado nos bastidores.

Você deve conversar naturalmente como uma assistente pessoal.

Seja inteligente, direta, amigável e útil.

Você possui memória. Use as memórias do usuário quando forem
relevantes para a conversa.

Não invente memórias.

Você pode:
- conversar
- pesquisar informações
- analisar imagens
- ajudar a criar prompts
- gerar imagens
- ajudar com vídeos
- explicar assuntos
- escrever textos
- programar

Quando receber resultados de pesquisa, diferencie informações
encontradas na internet do seu conhecimento geral.
"""


# ============================================================
# MEMÓRIA
# ============================================================

def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return {}

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return {}


def save_memory(memory):

    with open(
        MEMORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            memory,
            file,
            ensure_ascii=False,
            indent=2
        )


memory = load_memory()


def get_user(user_id):

    if user_id not in memory:

        memory[user_id] = {
            "history": [],
            "memories": []
        }

    return memory[user_id]


# ============================================================
# MODELOS DE REQUEST
# ============================================================

class ChatRequest(BaseModel):

    message: str
    user_id: str | None = None


class GenerateRequest(BaseModel):

    prompt: str
    user_id: str | None = None


class VideoRequest(BaseModel):

    prompt: str
    user_id: str | None = None
    width: int = 1152
    height: int = 768
    num_frames: int = 121
    frame_rate: int = 24


# ============================================================
# MEMÓRIA AUTOMÁTICA SIMPLES
# ============================================================

def learn_from_message(user_id, message):

    user = get_user(user_id)

    text = message.lower()

    triggers = [
        "meu nome é",
        "eu me chamo",
        "eu gosto de",
        "eu não gosto de",
        "eu prefiro",
        "meu celular é",
        "meu telefone é",
        "lembre que",
        "guarde que",
        "anote que"
    ]

    if not any(
        trigger in text
        for trigger in triggers
    ):
        return

    if message not in user["memories"]:

        user["memories"].append(message)

        user["memories"] = (
            user["memories"][-MAX_MEMORIES:]
        )

        save_memory(memory)


# ============================================================
# PESQUISA
# ============================================================

def search_web(query):

    try:

        response = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 0
            },
            timeout=15
        )

        data = response.json()

        results = []

        abstract = data.get(
            "AbstractText"
        )

        if abstract:

            results.append(
                abstract
            )

        for item in data.get(
            "RelatedTopics",
            []
        )[:6]:

            if isinstance(item, dict):

                text = item.get("Text")

                if text:
                    results.append(text)

        if not results:

            return "Nenhum resultado encontrado."

        return "\n\n".join(
            results[:6]
        )

    except Exception as error:

        print(
            "SEARCH ERROR:",
            error
        )

        return (
            "Não consegui realizar "
            "a pesquisa agora."
        )


# ============================================================
# CHAT COM AGNES
# ============================================================

def ask_agnes(
    user_id,
    message,
    web_result=None
):

    user = get_user(user_id)

    memories = user["memories"]

    if memories:

        memory_text = "\n".join(
            f"- {item}"
            for item in memories
        )

    else:

        memory_text = (
            "Nenhuma memória registrada."
        )

    system = SYSTEM_PROMPT

    system += (
        "\n\nMEMÓRIAS DO USUÁRIO:\n"
        + memory_text
    )

    messages = [
        {
            "role": "system",
            "content": system
        }
    ]

    messages.extend(
        user["history"][-MAX_HISTORY:]
    )

    if web_result:

        messages.append({
            "role": "system",
            "content":
                "RESULTADOS DA PESQUISA:\n\n"
                + web_result
        })

    messages.append({
        "role": "user",
        "content": message
    })

    response = requests.post(

        CHAT_URL,

        headers={
            "Authorization":
                f"Bearer {AGNES_KEY}",

            "Content-Type":
                "application/json"
        },

        json={

            "model":
                CHAT_MODEL,

            "messages":
                messages,

            "temperature":
                0.7,

            "max_tokens":
                4096
        },

        timeout=90
    )

    data = response.json()

    if response.status_code != 200:

        print(
            "AGNES CHAT ERROR:",
            data
        )

        raise Exception(
            "Erro na Agnes"
        )

    return data[
        "choices"
    ][0][
        "message"
    ][
        "content"
    ]


# ============================================================
# CHAT
# ============================================================

@app.post("/api/chat")
def chat(request: ChatRequest):

    if not AGNES_KEY:

        return {
            "error":
                "AGNES_KEY não configurada no Render."
        }

    user_id = (
        request.user_id
        or str(uuid.uuid4())
    )

    message = request.message.strip()

    if not message:

        return {
            "error":
                "Mensagem vazia."
        }

    user = get_user(user_id)

    # Aprendizado simples
    learn_from_message(
        user_id,
        message
    )

    # Pesquisa automática
    web_result = None

    search_words = [
        "pesquise",
        "pesquisa",
        "pesquisar",
        "procure",
        "procura na internet",
        "pesquise na internet",
        "pesquise na web",
        "busque na internet"
    ]

    if any(
        word in message.lower()
        for word in search_words
    ):

        web_result = search_web(
            message
        )

    try:

        answer = ask_agnes(
            user_id,
            message,
            web_result
        )

        user["history"].append({
            "role":
                "user",

            "content":
                message
        })

        user["history"].append({
            "role":
                "assistant",

            "content":
                answer
        })

        user["history"] = (
            user["history"]
            [-MAX_HISTORY:]
        )

        save_memory(memory)

        return {
            "user_id":
                user_id,

            "answer":
                answer
        }

    except Exception as error:

        print(
            "CHAT ERROR:",
            error
        )

        return {
            "error":
                "Não consegui conectar à IA."
        }


# ============================================================
# GERAR IMAGEM
# ============================================================

@app.post("/api/image")
def generate_image(
    request: GenerateRequest
):

    if not AGNES_KEY:

        return {
            "error":
                "AGNES_KEY não configurada."
        }

    try:

        response = requests.post(

            IMAGE_URL,

            headers={
                "Authorization":
                    f"Bearer {AGNES_KEY}",

                "Content-Type":
                    "application/json"
            },

            json={

                "model":
                    IMAGE_MODEL,

                "prompt":
                    request.prompt,

                "n":
                    1,

                "size":
                    "1024x1024"
            },

            timeout=300
        )

        data = response.json()

        if response.status_code != 200:

            print(
                "IMAGE ERROR:",
                data
            )

            return {
                "error":
                    "Erro ao gerar imagem."
            }

        image_data = (
            data.get("data", [{}])[0]
        )

        return {

            "type":
                "image",

            "url":
                image_data.get("url"),

            "b64_json":
                image_data.get("b64_json")
        }

    except Exception as error:

        print(
            "IMAGE ERROR:",
            error
        )

        return {
            "error":
                "Não consegui gerar a imagem."
        }


# ============================================================
# GERAR VÍDEO
# ============================================================

@app.post("/api/video")
def generate_video(
    request: VideoRequest
):

    if not AGNES_KEY:

        return {
            "error":
                "AGNES_KEY não configurada."
        }

    try:

        response = requests.post(

            VIDEO_URL,

            headers={
                "Authorization":
                    f"Bearer {AGNES_KEY}",

                "Content-Type":
                    "application/json"
            },

            json={

                "model":
                    VIDEO_MODEL,

                "prompt":
                    request.prompt,

                "width":
                    request.width,

                "height":
                    request.height,

                "num_frames":
                    request.num_frames,

                "frame_rate":
                    request.frame_rate
            },

            timeout=60
        )

        data = response.json()

        if response.status_code not in (
            200,
            201,
            202
        ):

            print(
                "VIDEO ERROR:",
                data
            )

            return {
                "error":
                    "Erro ao iniciar o vídeo."
            }

        video_id = (
            data.get("video_id")
            or data.get("id")
        )

        return {

            "type":
                "video",

            "video_id":
                video_id,

            "status":
                data.get(
                    "status",
                    "processing"
                )
        }

    except Exception as error:

        print(
            "VIDEO ERROR:",
            error
        )

        return {
            "error":
                "Não consegui iniciar o vídeo."
        }


# ============================================================
# CONSULTAR VÍDEO
# ============================================================

@app.get("/api/video/{video_id}")
def get_video(video_id: str):

    try:

        response = requests.get(

            f"{BASE_URL}/agnesapi",

            params={
                "video_id":
                    video_id
            },

            headers={
                "Authorization":
                    f"Bearer {AGNES_KEY}"
            },

            timeout=30
        )

        data = response.json()

        return data

    except Exception as error:

        print(
            "VIDEO POLL ERROR:",
            error
        )

        return {
            "error":
                "Erro ao consultar vídeo."
        }


# ============================================================
# ANALISAR IMAGEM
# ============================================================

@app.post("/api/vision")
async def analyze_image(
    user_id: str,
    prompt: str = "Analise esta imagem.",
    image: UploadFile = File(...)
):

    if not AGNES_KEY:

        return {
            "error":
                "AGNES_KEY não configurada."
        }

    try:

        image_bytes = await image.read()

        encoded = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        content_type = (
            image.content_type
            or "image/jpeg"
        )

        image_data = (
            f"data:{content_type};base64,"
            f"{encoded}"
        )

        messages = [

            {
                "role":
                    "system",

                "content":
                    SYSTEM_PROMPT
            },

            {

                "role":
                    "user",

                "content": [

                    {
                        "type":
                            "image_url",

                        "image_url": {

                            "url":
                                image_data
                        }
                    },

                    {
                        "type":
                            "text",

                        "text":
                            prompt
                    }
                ]
            }
        ]

        response = requests.post(

            CHAT_URL,

            headers={

                "Authorization":
                    f"Bearer {AGNES_KEY}",

                "Content-Type":
                    "application/json"
            },

            json={

                "model":
                    CHAT_MODEL,

                "messages":
                    messages,

                "max_tokens":
                    4096
            },

            timeout=120
        )

        data = response.json()

        if response.status_code != 200:

            print(
                "VISION ERROR:",
                data
            )

            return {
                "error":
                    "Erro ao analisar imagem."
            }

        answer = (
            data["choices"][0]
            ["message"]["content"]
        )

        return {
            "answer":
                answer
        }

    except Exception as error:

        print(
            "VISION ERROR:",
            error
        )

        return {
            "error":
                "Não consegui analisar a imagem."
        }


# ============================================================
# MEMÓRIA
# ============================================================

@app.get("/api/memory/{user_id}")
def get_memories(user_id: str):

    user = get_user(user_id)

    return {
        "memories":
            user["memories"]
    }


@app.delete("/api/memory/{user_id}")
def delete_memories(user_id: str):

    user = get_user(user_id)

    user["memories"] = []
    user["history"] = []

    save_memory(memory)

    return {
        "success":
            True
    }


# ============================================================
# SITE
# ============================================================

@app.get("/")
def home():

    return FileResponse(
        "index.html"
    )


@app.get("/style.css")
def css():

    return FileResponse(
        "style.css"
    )


@app.get("/app.js")
def javascript():

    return FileResponse(
        "app.js"
    )


# ============================================================
# RENDER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    uvicorn.run(

        app,

        host="0.0.0.0",

        port=port
        )
