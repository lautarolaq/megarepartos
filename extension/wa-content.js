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
  // Si saltó el dialog de número inválido, abortar.
  const invalid = detectInvalidPhone();
  if (invalid) {
    return { ok: false, error: "Número no encontrado en WhatsApp." };
  }

  // Esperar a que aparezca el botón Send.
  const sendBtn = await waitFor(() => document.querySelector(SELECTORS.sendButton), 15_000);
  if (!sendBtn) {
    return { ok: false, error: "No apareció el botón Send (chat no cargó)." };
  }

  // Delay aleatorio anti-detección antes de clickear.
  await wait(rand(800, 1800));

  // Si encontramos el span data-icon=send, subir al button ancestor.
  const btn = sendBtn.closest("button") ?? sendBtn;
  try {
    btn.click();
  } catch (e) {
    return { ok: false, error: `Click falló: ${e?.message ?? e}` };
  }

  // Esperar a que el compose se vacíe (señal de envío exitoso).
  const sent = await waitFor(() => {
    const box = document.querySelector(SELECTORS.composeBox);
    if (!box) return true;
    return (box.textContent ?? "").trim() === "";
  }, 8000);

  if (!sent) {
    return { ok: false, error: "Timeout esperando confirmación de envío." };
  }

  return { ok: true };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "MR_CLICK_SEND") return;
  clickSend()
    .then(sendResponse)
    .catch((e) => sendResponse({ ok: false, error: String(e?.message ?? e) }));
  return true; // async response
});
