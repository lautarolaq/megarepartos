// Content script que corre en https://web.whatsapp.com/*.
//
// Maneja 2 flujos:
//
// 1. MR_CLICK_SEND — el background ya navegó la tab a /send?phone=X&text=Y
//    via chrome.tabs.update; nosotros solo clickeamos el botón Send.
// 2. MR_SEND_BROADCAST — el background nos pasa { listName, message }.
//    Buscamos la lista de difusión por nombre en el buscador, la abrimos,
//    pegamos el mensaje y enviamos. La navegación previa la hace background
//    (asegurarse de estar en web.whatsapp.com/ y no en /send).

const SELECTORS = {
  sendButton: [
    'button[aria-label="Send"]',
    'button[aria-label="Enviar"]',
    'span[data-icon="send"]',
    '[data-testid="send"]',
  ].join(", "),
  composeBox:
    'div[contenteditable="true"][data-tab="10"], div[contenteditable="true"][role="textbox"]',
  searchInput: 'input[type="text"][data-tab="3"]',
  invalidPhoneDialog: '[data-testid="popup-controls-ok"], div[role="dialog"]',
};

const rand = (min, max) => Math.floor(min + Math.random() * (max - min));
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function log(...args) {
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

// Setear el value de un INPUT controlado por React, disparando el evento
// "input" para que React detecte el cambio (sin esto, react-controlled
// inputs ignoran asignaciones directas a .value).
function setReactInputValue(input, value) {
  const proto =
    input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const nativeSetter = Object.getOwnPropertyDescriptor(proto, "value").set;
  nativeSetter.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

async function clickSend() {
  log("clickSend: arrancando");

  const invalid = detectInvalidPhone();
  if (invalid) {
    log("clickSend: phone invalid dialog");
    return { ok: false, error: "Número no encontrado en WhatsApp." };
  }

  const sendBtn = await waitFor(() => document.querySelector(SELECTORS.sendButton), 15_000);
  if (!sendBtn) {
    log("clickSend: no apareció el Send button");
    return { ok: false, error: "No apareció el botón Send (chat no cargó)." };
  }
  log("clickSend: send button encontrado");

  const delay = rand(800, 1800);
  await wait(delay);

  const btn = sendBtn.closest("button") ?? sendBtn;
  try {
    btn.click();
    log("clickSend: click disparado");
  } catch (e) {
    log("clickSend: click falló", e);
    return { ok: false, error: `Click falló: ${e?.message ?? e}` };
  }

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

// Busca una lista de difusión (o cualquier chat) por nombre exacto, la abre,
// pega el mensaje y envía.
async function broadcastSend(listName, message) {
  log("broadcastSend: arrancando", { listName });

  // 1. Encontrar el search input.
  const searchInput = await waitFor(
    () => document.querySelector(SELECTORS.searchInput),
    8000,
  );
  if (!searchInput) {
    log("broadcastSend: no apareció search input");
    return { ok: false, error: "No apareció la barra de búsqueda de WhatsApp Web." };
  }

  // 2. Limpiar cualquier valor previo + tipear el nombre.
  searchInput.focus();
  setReactInputValue(searchInput, "");
  await wait(150);
  setReactInputValue(searchInput, listName);
  log("broadcastSend: búsqueda iniciada");
  await wait(1200); // dar tiempo a que WA Web filtre

  // 3. Buscar el chat con title === listName en la lista filtrada.
  // WA Web los renderiza como div[role="listitem"] con un span[title=...]
  // dentro. Tomamos match exacto (case-sensitive) para evitar abrir un chat
  // ambiguo. Si hay >1 exacto, fallar.
  const matches = Array.from(document.querySelectorAll("span[title]")).filter(
    (s) => s.title === listName && s.offsetParent !== null,
  );

  if (matches.length === 0) {
    log("broadcastSend: sin matches exactos");
    return {
      ok: false,
      error: `No encontré una lista/chat con nombre exacto "${listName}". Revisá la ortografía y mayúsculas.`,
    };
  }
  if (matches.length > 1) {
    log("broadcastSend: matches ambiguos", matches.length);
    return {
      ok: false,
      error: `Hay ${matches.length} chats con ese nombre. Renombrá para que sea único.`,
    };
  }

  // 4. Subir al elemento clickeable (div con role=listitem o equivalente).
  let chatItem = matches[0];
  for (let i = 0; i < 8; i++) {
    if (
      chatItem.getAttribute("role") === "listitem" ||
      chatItem.getAttribute("role") === "row" ||
      chatItem.getAttribute("data-tab") === "4"
    ) {
      break;
    }
    if (!chatItem.parentElement) break;
    chatItem = chatItem.parentElement;
  }
  try {
    chatItem.click();
    log("broadcastSend: chat abierto");
  } catch (e) {
    return { ok: false, error: `No pude abrir el chat: ${e?.message ?? e}` };
  }

  // 5. Esperar a que aparezca el compose box (chat cargado).
  const compose = await waitFor(
    () => document.querySelector(SELECTORS.composeBox),
    8000,
  );
  if (!compose) {
    log("broadcastSend: no apareció compose box");
    return { ok: false, error: "El chat no cargó (compose box no apareció)." };
  }

  // 6. Limpiar el search + focus al compose.
  setReactInputValue(searchInput, "");
  await wait(300);
  compose.focus();
  await wait(200);

  // 7. Insertar el mensaje. execCommand("insertText") es deprecated pero es
  // la única forma confiable de meter texto en contenteditable de WA Web
  // (que es controlled por Lexical/Slate-like editor).
  try {
    document.execCommand("selectAll", false);
    document.execCommand("insertText", false, message);
    log("broadcastSend: mensaje insertado");
  } catch (e) {
    return { ok: false, error: `No pude tipear el mensaje: ${e?.message ?? e}` };
  }
  await wait(800);

  // 8. Click Send.
  const sendBtn = await waitFor(
    () => document.querySelector(SELECTORS.sendButton),
    5000,
  );
  if (!sendBtn) {
    return { ok: false, error: "No apareció el botón Send después de tipear." };
  }
  await wait(rand(500, 1200));
  const btn = sendBtn.closest("button") ?? sendBtn;
  try {
    btn.click();
    log("broadcastSend: send disparado");
  } catch (e) {
    return { ok: false, error: `Click Send falló: ${e?.message ?? e}` };
  }

  // 9. Esperar a que el compose se vacíe.
  const sent = await waitFor(() => {
    const box = document.querySelector(SELECTORS.composeBox);
    if (!box) return true;
    return (box.textContent ?? "").trim() === "";
  }, 10_000);

  if (!sent) {
    return { ok: false, error: "Timeout esperando confirmación de envío del broadcast." };
  }

  log("broadcastSend: broadcast enviado OK");
  return { ok: true };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  log("onMessage recibido", msg?.type);
  if (msg?.type === "MR_CLICK_SEND") {
    clickSend()
      .then((resp) => sendResponse(resp))
      .catch((e) => sendResponse({ ok: false, error: String(e?.message ?? e) }));
    return true;
  }
  if (msg?.type === "MR_SEND_BROADCAST") {
    broadcastSend(msg.listName, msg.message)
      .then((resp) => sendResponse(resp))
      .catch((e) => sendResponse({ ok: false, error: String(e?.message ?? e) }));
    return true;
  }
});

log("wa-content.js loaded v0.2.0");
