const chat = document.getElementById("chat");
const input = document.getElementById("message");
const send = document.getElementById("send");

const sidebar = document.getElementById("sidebar");
const menuButton = document.getElementById("menuButton");
const closeMenu = document.getElementById("closeMenu");

const memoryModal = document.getElementById("memoryModal");
const settingsModal = document.getElementById("settingsModal");

const userId =
    localStorage.getItem("sexta_user_id") ||
    crypto.randomUUID();

localStorage.setItem("sexta_user_id", userId);


// ============================================================
// MENU
// ============================================================

menuButton.addEventListener("click", () => {
    sidebar.classList.add("open");
});

closeMenu.addEventListener("click", () => {
    sidebar.classList.remove("open");
});


// ============================================================
// NOVA CONVERSA
// ============================================================

document.getElementById("newChat").addEventListener("click", () => {

    chat.innerHTML = `
        <div class="welcome">

            <div class="welcome-logo">S</div>

            <h1>Olá! 👋</h1>

            <p>
                Eu sou a Sexta Feira.
                <br>
                Como posso ajudar você hoje?
            </p>

            <div class="suggestions">

                <button onclick="useSuggestion('Pesquise as principais notícias de tecnologia de hoje')">
                    🔎 Pesquisar na internet
                </button>

                <button onclick="useSuggestion('Explique como você pode me ajudar')">
                    ✨ O que você consegue fazer?
                </button>

                <button onclick="useSuggestion('Me conte algo interessante')">
                    💡 Me surpreenda
                </button>

            </div>

        </div>
    `;

    sidebar.classList.remove("open");
});


// ============================================================
// SUGESTÕES
// ============================================================

function useSuggestion(text) {

    input.value = text;

    input.focus();

    if (!text.endsWith(" ")) {
        sendMessage();
    }
}


// ============================================================
// ADICIONAR MENSAGEM
// ============================================================

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


// ============================================================
// ENVIAR MENSAGEM
// ============================================================

async function sendMessage() {

    const text =
        input.value.trim();

    if (!text) return;

    input.value = "";

    document.querySelector(".welcome")?.remove();

    addMessage(text, "user");

    const loading =
        addMessage(
            "Sexta Feira está pensando...",
            "assistant"
        );

    send.disabled = true;

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

    } finally {

        send.disabled = false;

        input.focus();
    }
}


// ============================================================
// BOTÃO ENVIAR
// ============================================================

send.addEventListener(
    "click",
    sendMessage
);


// ============================================================
// ENTER
// ============================================================

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


// ============================================================
// TEXTAREA AUTOMÁTICO
// ============================================================

input.addEventListener(
    "input",
    function() {

        this.style.height = "auto";

        this.style.height =
            Math.min(
                this.scrollHeight,
                150
            ) + "px";
    }
);


// ============================================================
// APAGAR CHAT
// ============================================================

document
    .getElementById("clearChat")
    .addEventListener("click", async () => {

        if (
            !confirm(
                "Apagar todo o histórico e memória?"
            )
        ) {
            return;
        }

        try {

            await fetch(
                `/api/memory/${userId}`,
                {
                    method: "DELETE"
                }
            );

            chat.innerHTML = `
                <div class="welcome">

                    <div class="welcome-logo">S</div>

                    <h1>Memória apagada 🧠</h1>

                    <p>
                        Podemos começar novamente.
                    </p>

                </div>
            `;

        } catch {

            alert(
                "Não consegui apagar a memória."
            );
        }
    });


// ============================================================
// MEMÓRIA
// ============================================================

document
    .getElementById("memoryButton")
    .addEventListener(
        "click",
        openMemory
    );


async function openMemory() {

    memoryModal.classList.remove("hidden");

    const list =
        document.getElementById("memoryList");

    list.innerHTML =
        "Carregando memórias...";

    try {

        const response =
            await fetch(
                `/api/memory/${userId}`
            );

        const data =
            await response.json();

        if (
            !data.memories ||
            data.memories.length === 0
        ) {

            list.innerHTML =
                "<p>Nenhuma memória salva.</p>";

            return;
        }

        list.innerHTML = "";

        data.memories.forEach(
            (memory, index) => {

                const item =
                    document.createElement("div");

                item.className =
                    "memory-item";

                item.textContent =
                    `${index + 1}. ${memory}`;

                list.appendChild(item);
            }
        );

    } catch {

        list.innerHTML =
            "<p>Erro ao carregar memória.</p>";
    }
}


function closeMemory() {

    memoryModal.classList.add("hidden");
}


// ============================================================
// APAGAR MEMÓRIA
// ============================================================

document
    .getElementById("deleteMemory")
    .addEventListener(
        "click",
        async () => {

            if (
                !confirm(
                    "Tem certeza que deseja apagar suas memórias?"
                )
            ) {
                return;
            }

            await fetch(
                `/api/memory/${userId}`,
                {
                    method: "DELETE"
                }
            );

            openMemory();
        }
    );


// ============================================================
// CONFIGURAÇÕES
// ============================================================

document
    .getElementById("settingsButton")
    .addEventListener(
        "click",
        () => {

            settingsModal.classList.remove(
                "hidden"
            );

            sidebar.classList.remove(
                "open"
            );
        }
    );


function closeSettings() {

    settingsModal.classList.add(
        "hidden"
    );
}


// ============================================================
// TEMA
// ============================================================

function toggleTheme() {

    document.body.classList.toggle(
        "light"
    );

    const isLight =
        document.body.classList.contains(
            "light"
        );

    localStorage.setItem(
        "sexta_theme",
        isLight ? "light" : "dark"
    );
}


// Restaurar tema

if (
    localStorage.getItem("sexta_theme")
    === "light"
) {

    document.body.classList.add(
        "light"
    );
    }
