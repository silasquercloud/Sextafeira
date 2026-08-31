const chat = document.getElementById("chat");
const input = document.getElementById("message");
const send = document.getElementById("send");


// =========================
// IDENTIDADE DO USUÁRIO
// =========================

let userId = localStorage.getItem("sexta_user_id");

if (!userId) {

    userId =
        crypto.randomUUID();

    localStorage.setItem(
        "sexta_user_id",
        userId
    );
}


// =========================
// ADICIONAR MENSAGEM
// =========================

function addMessage(text, type) {

    const message =
        document.createElement("div");

    message.className =
        `message ${type}`;

    const bubble =
        document.createElement("div");

    bubble.className =
        "bubble";

    bubble.textContent = text;

    message.appendChild(bubble);

    chat.appendChild(message);

    window.scrollTo({
        top: document.body.scrollHeight,
        behavior: "smooth"
    });

    return bubble;
}


// =========================
// ENVIAR
// =========================

async function sendMessage() {

    const text =
        input.value.trim();

    if (!text) return;

    input.value = "";

    document.querySelector(".welcome")?.remove();

    addMessage(text, "user");

    const loading =
        addMessage("Sexta Feira está pensando...", "assistant");

    try {

        const response =
            await fetch("/api/chat", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    message: text,
                    user_id: userId
                })
            });

        const data =
            await response.json();

        if (data.error) {

            loading.textContent =
                "⚠️ " + data.error;

            return;
        }

        loading.textContent =
            data.answer;

    } catch (error) {

        console.error(error);

        loading.textContent =
            "⚠️ Não consegui conectar ao servidor.";
    }
}


// =========================
// BOTÃO
// =========================

send.addEventListener(
    "click",
    sendMessage
);


// =========================
// ENTER
// =========================

input.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();
        }
    }
);
