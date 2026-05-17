// Content script que corre en https://web.whatsapp.com/*.
// Responsabilidad acotada: cuando el background le manda MR_CLICK_SEND,
// busca el botón de Send y lo clickea. La NAVEGACIÓN la hace el background
// via chrome.tabs.update, no este script.

const SELECTORS = {
  // El botón Send: en WhatsApp Web actual es un button con aria-label
  // "Send"/"Enviar" o un span con data-icon="send".
  sendButton: [
    'button[aria-label="Send"]',
    'button[aria-label="Enviar"]',
    'span[data-icon="send"]',
    '[data-testid="send"]',
  ].join(", "),
  composeBox:
    'div[contenteditable="true"][data-tab="10"], div[contenteditable="true"][role="textbox"]',
  // Dialog de error "Phone number shared via url is invalid".
  invalidPhoneDialog: '[data-testid="popup-controls-ok"], div[role="dialog"]',
};

const rand = (min, max) => Math.floor(min + Math.random() * (max - min));
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function log(...args) {
  // Estos logs aparecen en la consola de la pestaña de WhatsApp Web.
  // eslint-disable-next-line no-console
  console.log("[MR-EXT]", ...args);
}

async function waitFor(testFn, timeoutMs = 12_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const el = testFn();
      if (el) return el;
    } catch {
      // ignore
    }
    await wait(250);
  }
  return null;
}

function detectInvalidPhone() {
  const dialogs = document.querySelectorAll("div[role='dialog']");
  for (const d of dialogs) {
    const text = (d.textContent ?? "").toLowerCase();
    if (
      text.includes("no válid") ||
      text.includes("invalid") ||
      text.includes("incorrecta") ||
      text.includes("compartido en la url")
    ) {
      return d;
    }
  }
  return null;
}

async function clickSend() {
  log("clickSend: arrancando");

  // Si saltó el dialog de número inválido, abortar.
  const invalid = detectInvalidPhone();
  if (invalid) {
    log("clickSend: phone invalid dialog");
    return { ok: false, error: "Número no encontrado en WhatsApp." };
  }

  // Esperar a que aparezca el botón Send.
  const sendBtn = await waitFor(() => document.querySelector(SELECTORS.sendButton), 15_000);
  if (!sendBtn) {
    log("clickSend: no apareció el Send button");
    return { ok: false, error: "No apareció el botón Send (chat no cargó)." };
  }
  log("clickSend: send button encontrado", sendBtn.tagName, sendBtn.getAttribute("aria-label"));

  // Delay aleatorio anti-detección antes de clickear.
  const delay = rand(800, 1800);
  log("clickSend: delay", delay, "ms");
  await wait(delay);

  // Si encontramos el span data-icon=send, subir al button ancestor.
  const btn = sendBtn.closest("button") ?? sendBtn;
  try {
    btn.click();
    log("clickSend: click disparado");
  } catch (e) {
    log("clickSend: click falló", e);
    return { ok: false, error: `Click falló: ${e?.message ?? e}` };
  }

  // Esperar a que el compose se vacíe (señal de envío exitoso).
  const sent = await waitFor(() => {
    const box = document.querySelector(SELECTORS.composeBox);
    if (!box) return true;
    return (box.textContent ?? "").trim() === "";
  }, 8000);

  if (!sent) {
    log("clickSend: timeout esperando compose vacío");
    return { ok: false, error: "Timeout esperando confirmación de envío." };
  }

  log("clickSend: enviado OK");
  return { ok: true };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  log("onMessage recibido", msg?.type);
  if (msg?.type !== "MR_CLICK_SEND") return;
  clickSend()
    .then((resp) => {
      log("clickSend resp", resp);
      sendResponse(resp);
    })
    .catch((e) => {
      log("clickSend throw", e);
      sendResponse({ ok: false, error: String(e?.message ?? e) });
    });
  return true; // async response
});

log("wa-content.js loaded v0.1.1");
