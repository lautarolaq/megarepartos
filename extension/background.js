// Service worker que coordina entre la app de Megarepartos y WhatsApp Web.
//
// Flujo:
// 1. El app-content.js (que corre en la app web) escucha window.postMessage
//    desde la página y los reenvía a este service worker.
// 2. Este worker abre o reutiliza una tab de https://web.whatsapp.com.
// 3. Le manda los mensajes al wa-content.js (que corre en esa tab).
// 4. wa-content.js automatiza los clicks y reporta back el resultado.
// 5. El resultado vuelve al app-content.js y a la app web.

const WA_URL = "https://web.whatsapp.com/";

// Estado de la "campaña" activa (in-memory, sólo dura mientras la extensión
// está running). Si el service worker se duerme entre mensajes, no perdemos
// nada crítico porque cada mensaje es individual.
const state = {
  /** @type {number | null} */ waTabId: null,
  /** @type {Array<{phone: string, message: string, idx: number}>} */ queue: [],
  appTabId: null,
};

async function findOrOpenWhatsAppTab() {
  const tabs = await chrome.tabs.query({ url: "https://web.whatsapp.com/*" });
  if (tabs.length > 0) {
    state.waTabId = tabs[0].id;
    await chrome.tabs.update(state.waTabId, { active: false });
    return tabs[0];
  }
  const created = await chrome.tabs.create({ url: WA_URL, active: false });
  state.waTabId = created.id;
  // Esperar un poco a que el content script cargue.
  await new Promise((r) => setTimeout(r, 4000));
  return created;
}

async function sendOne(phone, message) {
  await findOrOpenWhatsAppTab();
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(
      state.waTabId,
      { type: "MR_SEND_ONE", phone, message },
      (resp) => {
        if (chrome.runtime.lastError) {
          resolve({
            ok: false,
            error: chrome.runtime.lastError.message ?? "send failed",
          });
        } else {
          resolve(resp ?? { ok: false, error: "no response" });
        }
      },
    );
  });
}

// Mensajes desde el content script de la app o del WhatsApp.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === "MR_PING") {
    sendResponse({ ok: true, version: chrome.runtime.getManifest().version });
    return;
  }

  if (msg?.type === "MR_SEND_ONE") {
    // Recordar quién pidió, para reportar progress.
    if (sender.tab?.id) state.appTabId = sender.tab.id;
    sendOne(msg.phone, msg.message).then(sendResponse);
    return true; // async response
  }

  if (msg?.type === "MR_PROGRESS" && state.appTabId) {
    // Re-difundir el progreso de WA → app.
    chrome.tabs.sendMessage(state.appTabId, msg).catch(() => {});
    return;
  }
});
