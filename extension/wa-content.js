// Content script que corre en https://web.whatsapp.com/*.
// Automatiza el flujo de "abrir chat con teléfono → escribir mensaje → enviar".
//
// Estrategia:
// 1. Navegar a https://web.whatsapp.com/send?phone=<phone>&text=<message>.
//    WhatsApp Web reconoce esta URL y pre-llena el chat con el mensaje.
// 2. Esperar a que aparezca el botón Send (con un timeout razonable).
// 3. Click Send.
// 4. Esperar a que el mensaje desaparezca del compose box.
//
// Anti-detection: delays randomizados entre operaciones (SPEC 8.4).

const SELECTORS = {
  // El botón de enviar: data-tab=11 históricamente. Por las dudas, fallback.
  sendButton:
    'button[data-tab="11"][aria-label*="Enviar"], button[data-tab="11"][aria-label*="Send"], span[data-icon="send"]',
  // Caja de texto donde escribimos.
  composeBox: 'div[contenteditable="true"][data-tab="10"]',
  // Banner de "Phone number shared via url is invalid"
  invalidPhone: 'div[role="dialog"]',
};

const rand = (min, max) => Math.floor(min + Math.random() * (max - min));
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitFor(selectorOrFn, timeoutMs = 15000) {
  const start = Date.now();
  const fn =
    typeof selectorOrFn === "string"
      ? () => document.querySelector(selectorOrFn)
      : selectorOrFn;
  while (Date.now() - start < timeoutMs) {
    const el = fn();
    if (el) return el;
    await wait(200);
  }
  return null;
}

async function sendToPhone({ phone, message }) {
  const digits = String(phone).replace(/\D/g, "");
  if (!digits) return { ok: false, error: "Teléfono inválido." };

  // Cargar la URL de send. WhatsApp pre-llena el text si el contacto existe.
  const url = `https://web.whatsapp.com/send?phone=${digits}&text=${encodeURIComponent(message)}`;
  if (location.href.includes("/send?") === false || !location.href.includes(`phone=${digits}`)) {
    location.href = url;
    // Esperar a que la app cargue (puede tardar varios segundos).
    await wait(rand(3500, 5500));
  }

  // Si saltó modal de "número inválido", abortar.
  const dialog = document.querySelector(SELECTORS.invalidPhone);
  if (dialog && /no.*válid|invalid/i.test(dialog.textContent ?? "")) {
    return { ok: false, error: "Número no encontrado en WhatsApp." };
  }

  // Esperar a que aparezca el botón Send.
  const sendBtn = await waitFor(() => document.querySelector(SELECTORS.sendButton), 12000);
  if (!sendBtn) {
    return { ok: false, error: "No apareció el botón de enviar (chat no cargó)." };
  }

  // Delay aleatorio anti-detección antes de clickear.
  await wait(rand(800, 1800));

  // El botón send está dentro de un button — buscar el button ancestor real.
  const btn = sendBtn.closest("button") ?? sendBtn;
  btn.click();

  // Esperar a que se vacíe el compose box o desaparezca el botón (sent).
  const sent = await waitFor(() => {
    const box = document.querySelector(SELECTORS.composeBox);
    return !box || (box.textContent ?? "").trim() === "";
  }, 8000);

  if (!sent) {
    return { ok: false, error: "Pasó el timeout esperando confirmación de envío." };
  }

  return { ok: true };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "MR_SEND_ONE") return;
  sendToPhone({ phone: msg.phone, message: msg.message })
    .then(sendResponse)
    .catch((e) => sendResponse({ ok: false, error: String(e?.message ?? e) }));
  return true; // async response
});

// Heartbeat al background para que sepa que el content script está vivo.
chrome.runtime.sendMessage({ type: "MR_PROGRESS", event: "wa-ready" }).catch(() => {});
