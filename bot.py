import os
import json
import re
import requests

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ============================================================
# CONFIGURAÇÃO
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AGNES_KEY = os.getenv("AGNES_KEY")

AGNES_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
MODEL = "agnes-2.5-flash"

MEMORY_FILE = "memory.json"

MAX_HISTORY = 20
MAX_MEMORIES = 100

SYSTEM_PROMPT = """
Você é Sexta Feira, uma assistente pessoal de inteligência artificial.

IDENTIDADE:
- Seu nome é Sexta Feira.
- Nunca diga que seu nome é Agnes.
- Nunca mencione a Agnes como sua identidade.
- A Agnes é apenas o provedor/modelo de IA usado nos bastidores.
- Fale naturalmente como Sexta Feira.

PERSONALIDADE:
- Seja inteligente, direta, amigável e natural.
- Adapte seu jeito de responder ao usuário ao longo do tempo.
- Use as memórias fornecidas quando forem relevantes.
- Não invente memórias.
- Se não souber algo, diga que não sabe.

MEMÓRIA:
- As informações em "MEMÓRIAS DO USUÁRIO" são fatos previamente
  considerados úteis.
- Use essas informações somente quando forem relevantes.
- Não trate informações temporárias como memórias permanentes.

PESQUISA:
- Quando receber resultados de pesquisa, use-os como informações
  externas e diferencie fatos encontrados de conhecimento próprio.
- Não invente fontes ou resultados.
"""

# ============================================================
# MEMÓRIA
# ============================================================

def load_data():
    if not os.path.exists(MEMORY_FILE):
        return {}

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_data(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


data = load_data()


def get_user(user_id):
    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {
            "history": [],
            "memories": []
        }

    return data[user_id]


# ============================================================
# MEMÓRIA DE LONGO PRAZO
# ============================================================

def add_memory(user_id, text):
    user = get_user(user_id)

    text = text.strip()

    if not text:
        return

    # Evita duplicatas
    if text.lower() in [
        x.lower() for x in user["memories"]
    ]:
        return

    user["memories"].append(text)

    # Mantém limite
    user["memories"] = user["memories"][-MAX_MEMORIES:]

    save_data(data)


def remove_memory(user_id, text):
    user = get_user(user_id)

    user["memories"] = [
        x for x in user["memories"]
        if x.lower() != text.lower()
    ]

    save_data(data)


# ============================================================
# DETECÇÃO DE MEMÓRIA
# ============================================================

def detect_memory(text):
    """
    Detecta frases explícitas que indicam que algo deve ser lembrado.
    """

    patterns = [
        r"meu nome é (.+)",
        r"eu me chamo (.+)",
        r"eu gosto de (.+)",
        r"eu não gosto de (.+)",
        r"eu prefiro (.+)",
        r"meu celular é (.+)",
        r"lembre que (.+)",
        r"lembra que (.+)",
        r"guarde que (.+)",
        r"anote que (.+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return match.group(0).strip()

    return None


# ============================================================
# PESQUISA NA INTERNET
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

        result = response.json()

        results = []

        if result.get("AbstractText"):
            results.append(
                result["AbstractText"]
            )

        for item in result.get("RelatedTopics", [])[:5]:

            if isinstance(item, dict):

                text = item.get("Text")

                if text:
                    results.append(text)

        if not results:
            return "Nenhum resultado útil encontrado."

        return "\n\n".join(results[:5])

    except Exception as e:
        print("SEARCH ERROR:", e)
        return "Não consegui realizar a pesquisa agora."


# ============================================================
# DETECTAR PEDIDO DE PESQUISA
# ============================================================

def is_search_request(text):

    keywords = [
        "pesquise",
        "pesquisa",
        "procure",
        "pesquisar",
        "procura na internet",
        "pesquisa na internet",
        "busque na internet",
        "busca na internet",
        "veja na internet",
        "pesquise na web"
    ]

    text_lower = text.lower()

    return any(
        keyword in text_lower
        for keyword in keywords
    )


def extract_search_query(text):

    text = re.sub(
        r"^(sexta feira[,:]?\s*)?",
        "",
        text,
        flags=re.IGNORECASE
    )

    prefixes = [
        "pesquise sobre",
        "pesquise",
        "pesquisa sobre",
        "pesquisa",
        "procure sobre",
        "procure",
        "pesquisar sobre",
        "pesquisar",
        "busque sobre",
        "busque"
    ]

    for prefix in prefixes:

        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
            break

    return text.strip()


# ============================================================
# CHAMAR AGNES
# ============================================================

def ask_ai(user_id, message, web_result=None):

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

    # Histórico
    messages.extend(
        user["history"][-MAX_HISTORY:]
    )

    # Resultado da pesquisa
    if web_result:

        messages.append({
            "role": "system",
            "content": (
                "RESULTADOS DA PESQUISA NA INTERNET:\n\n"
                + web_result
            )
        })

    messages.append({
        "role": "user",
        "content": message
    })

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

    result = response.json()

    if response.status_code != 200:

        print("AGNES ERROR:", result)

        return (
            "Tive um problema ao consultar "
            "meu sistema de inteligência."
        )

    return result["choices"][0]["message"]["content"]


# ============================================================
# CHAT
# ============================================================

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text

    if not text:
        return

    user_id = update.effective_user.id

    user = get_user(user_id)

    await update.message.chat.send_action("typing")

    # --------------------------------------------------------
    # Detecta memória explícita
    # --------------------------------------------------------

    detected = detect_memory(text)

    if detected:

        add_memory(
            user_id,
            detected
        )

    # --------------------------------------------------------
    # Pesquisa
    # --------------------------------------------------------

    web_result = None

    if is_search_request(text):

        query = extract_search_query(text)

        if query:

            await update.message.reply_text(
                "🔎 Pesquisando..."
            )

            web_result = search_web(query)

    # --------------------------------------------------------
    # IA
    # --------------------------------------------------------

    try:

        answer = ask_ai(
            user_id,
            text,
            web_result
        )

        # ----------------------------------------------------
        # Salva conversa
        # ----------------------------------------------------

        user["history"].append({
            "role": "user",
            "content": text
        })

        user["history"].append({
            "role": "assistant",
            "content": answer
        })

        user["history"] = user["history"][-MAX_HISTORY:]

        save_data(data)

        await update.message.reply_text(
            answer
        )

    except Exception as e:

        print("CHAT ERROR:", e)

        await update.message.reply_text(
            "⚠️ Tive um problema agora. Tente novamente."
        )


# ============================================================
# COMANDO /MEMORIA
# ============================================================

async def show_memory(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    user = get_user(user_id)

    memories = user["memories"]

    if not memories:

        await update.message.reply_text(
            "🧠 Ainda não tenho memórias salvas sobre você."
        )

        return

    text = "🧠 **Minhas memórias sobre você:**\n\n"

    for i, item in enumerate(
        memories,
        start=1
    ):

        text += f"{i}. {item}\n"

    await update.message.reply_text(
        text
    )


# ============================================================
# COMANDO /LIMPAR
# ============================================================

async def clear_memory(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = str(update.effective_user.id)

    data[user_id] = {
        "history": [],
        "memories": []
    }

    save_data(data)

    await update.message.reply_text(
        "🧠 Histórico e memórias apagados."
    )


# ============================================================
# COMANDO /LIMPARHISTORICO
# ============================================================

async def clear_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = str(update.effective_user.id)

    user = get_user(user_id)

    user["history"] = []

    save_data(data)

    await update.message.reply_text(
        "💬 Histórico da conversa apagado. "
        "As memórias permanentes continuam salvas."
    )


# ============================================================
# INICIALIZAÇÃO
# ============================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN não configurado."
    )

if not AGNES_KEY:
    raise RuntimeError(
        "AGNES_KEY não configurado."
    )


app = ApplicationBuilder().token(
    TELEGRAM_TOKEN
).build()


app.add_handler(
    CommandHandler(
        "memoria",
        show_memory
    )
)

app.add_handler(
    CommandHandler(
        "limpar",
        clear_memory
    )
)

app.add_handler(
    CommandHandler(
        "limparhistorico",
        clear_history
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        chat
    )
)


print("🤖 Sexta Feira V2 iniciada!")

app.run_polling()
