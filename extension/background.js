// Service worker que coordina entre la app de Megarepartos y WhatsApp Web.
//
// Flujo correcto (sin que se rompa cuando navega WhatsApp Web):
// 1. app-content.js manda MR_SEND_ONE al background con {phone, message}.
// 2. background.js navega o reusa la tab de WhatsApp Web a /send?phone=X&text=Y
//    via chrome.tabs.update — esto recarga la página y el content script.
// 3. background.js espera a que la tab termine de cargar (status="complete").
// 4. background.js le manda MR_CLICK_SEND al content script de la tab ya cargada.
// 5. wa-content.js hace el click y devuelve {ok, error?}.
// 6. background.js le responde al app-content.js.

const WA_BASE = "https://web.whatsapp.com";

const state = {
  /** @type {number | null} */ waTabId: null,
  /** @type {number | null} */ appTabId: null,
};

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function findOrOpenWhatsAppTab() {
  const tabs = await chrome.tabs.query({ url: `${WA_BASE}/*` });
  if (tabs.length > 0) {
    state.waTabId = tabs[0].id;
    return tabs[0];
  }
  const created = await chrome.tabs.create({ url: `${WA_BASE}/`, active: false });
  state.waTabId = created.id;
  await waitForTabComplete(state.waTabId, 30_000);
  // WhatsApp Web tarda un poco más en realmente arrancar la app.
  await delay(3000);
  return created;
}

function waitForTabComplete(tabId, timeoutMs = 30_000) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const timeout = setTimeout(() => {
      if (settled) return;
      settled = true;
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error("Timeout esperando que la tab termine de cargar."));
    }, timeoutMs);

    const listener = (id, info) => {
      if (id !== tabId) return;
      if (info.status === "complete") {
        if (settled) return;
        settled = true;
        clearTimeout(timeout);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    };
    chrome.tabs.onUpdated.addListener(listener);

    // Si ya está complete, resolver enseguida.
    chrome.tabs.get(tabId).then((t) => {
      if (t.status === "complete" && !settled) {
        settled = true;
        clearTimeout(timeout);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    });
  });
}

async function sendOne(phone, message) {
  const digits = String(phone).replace(/\D/g, "");
  if (!digits) return { ok: false, error: "Teléfono inválido." };

  try {
    await findOrOpenWhatsAppTab();
  } catch (e) {
    return { ok: false, error: `No pude abrir WhatsApp Web: ${e?.message ?? e}` };
  }

  const url = `${WA_BASE}/send?phone=${digits}&text=${encodeURIComponent(message)}`;
  try {
    await chrome.tabs.update(state.waTabId, { url, active: false });
  } catch (e) {
    return { ok: false, error: `No pude navegar WhatsApp Web: ${e?.message ?? e}` };
  }

  try {
    await waitForTabComplete(state.waTabId, 30_000);
  } catch (e) {
    return { ok: false, error: e?.message ?? String(e) };
  }

  // Esperar a que WhatsApp Web cargue el chat (incluye render del compose box).
  await delay(2500);

  // Pedirle al content script que clickee Send.
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(state.waTabId, { type: "MR_CLICK_SEND" }, (resp) => {
      if (chrome.runtime.lastError) {
        resolve({
          ok: false,
          error: `Content script no responde: ${chrome.runtime.lastError.message}`,
        });
        return;
      }
      resolve(resp ?? { ok: false, error: "Sin respuesta del content script." });
    });
  });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === "MR_PING") {
    sendResponse({ ok: true, version: chrome.runtime.getManifest().version });
    return;
  }

  if (msg?.type === "MR_SEND_ONE") {
    if (sender.tab?.id) state.appTabId = sender.tab.id;
    sendOne(msg.phone, msg.message)
      .then(sendResponse)
      .catch((e) => sendResponse({ ok: false, error: String(e?.message ?? e) }));
    return true; // async response
  }
});
