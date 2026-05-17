// Service worker que coordina entre la app de Megarepartos y WhatsApp Web.
//
// Flujo (resiliente a MV3 SW idle timeout):
// 1. app-content.js manda MR_SEND_ONE al background con {phone, message}.
// 2. background.js navega o reusa la tab de WhatsApp Web a /send?phone=X&text=Y
//    via chrome.tabs.update.
// 3. background.js espera a que la tab termine de cargar polleando con
//    chrome.tabs.get cada 200ms — cada call resetea el timer de idle del SW.
// 4. background.js le manda MR_CLICK_SEND al content script de la tab.
// 5. wa-content.js hace el click y devuelve {ok, error?}.
// 6. background.js le responde al app-content.js.
//
// IMPORTANTE: nada de setTimeout largos sin chrome.* calls intercalados, sino
// el SW se duerme y el message channel se cierra antes del response.

const WA_BASE = "https://web.whatsapp.com";

const state = {
  /** @type {number | null} */ waTabId: null,
};

// Sleep en pasos cortos que hacen chrome.* calls para mantener vivo el SW.
async function safeSleep(totalMs) {
  const STEP = 150;
  const steps = Math.max(1, Math.ceil(totalMs / STEP));
  for (let i = 0; i < steps; i++) {
    await new Promise((r) => setTimeout(r, STEP));
    // chrome.runtime.getPlatformInfo es barato y resetea el timer del SW.
    try {
      await chrome.runtime.getPlatformInfo();
    } catch {
      // ignore
    }
  }
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
  await safeSleep(3000);
  return created;
}

// Polling-based: cada chrome.tabs.get resetea el SW idle timer.
async function waitForTabComplete(tabId, timeoutMs = 30_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const tab = await chrome.tabs.get(tabId);
      if (tab.status === "complete") return;
    } catch (e) {
      // Tab cerrada o inaccesible
      throw new Error(`Tab inaccesible: ${e?.message ?? e}`);
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error("Timeout esperando que la tab termine de cargar.");
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

  // Esperar a que WhatsApp Web cargue el chat (compose box + send button).
  await safeSleep(2500);

  // Pedirle al content script que clickee Send. Usamos sendMessage con timeout
  // explícito: si en 30s no llega respuesta, asumimos que wa-content murió.
  try {
    const resp = await Promise.race([
      chrome.tabs.sendMessage(state.waTabId, { type: "MR_CLICK_SEND" }),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error("Timeout esperando respuesta de wa-content.js (30s).")), 30_000),
      ),
    ]);
    return resp ?? { ok: false, error: "Sin respuesta del content script." };
  } catch (e) {
    return { ok: false, error: `Content script no responde: ${e?.message ?? e}` };
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "MR_PING") {
    sendResponse({ ok: true, version: chrome.runtime.getManifest().version });
    return;
  }

  if (msg?.type === "MR_SEND_ONE") {
    sendOne(msg.phone, msg.message)
      .then(sendResponse)
      .catch((e) => sendResponse({ ok: false, error: String(e?.message ?? e) }));
    return true; // async response
  }
});
