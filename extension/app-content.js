// Content script que corre en la app de Megarepartos (localhost / túneles /
// dominio prod). Sirve de puente entre la página y el background.
//
// La página detecta la extensión via window.postMessage:
//   window.postMessage({ source: "mr-app", type: "MR_PING" }, "*");
// y este content script responde con la versión, así la app sabe que la
// extensión está instalada y puede ofrecer "envío automático".

const ALLOWED_TYPES = new Set(["MR_PING", "MR_SEND_ONE", "MR_SEND_BROADCAST"]);
// Campos que reenviamos del page al background (whitelist explícita).
const FORWARD_FIELDS = ["phone", "message", "listName"];

window.addEventListener("message", async (event) => {
  if (event.source !== window) return;
  const data = event.data;
  if (!data || data.source !== "mr-app") return;
  if (!ALLOWED_TYPES.has(data.type)) return;

  const reqId = data.reqId;
  const payload = { type: data.type };
  for (const k of FORWARD_FIELDS) {
    if (data[k] !== undefined) payload[k] = data[k];
  }
  try {
    const resp = await chrome.runtime.sendMessage(payload);
    window.postMessage(
      { source: "mr-ext", reqId, type: data.type + "_RESP", payload: resp },
      "*",
    );
  } catch (e) {
    window.postMessage(
      {
        source: "mr-ext",
        reqId,
        type: data.type + "_RESP",
        payload: { ok: false, error: String(e?.message ?? e) },
      },
      "*",
    );
  }
});

// Inyectar marker para que la app pueda detectar la extensión sincronicamente.
// (postMessage es async; el marker permite renderizar el botón sin esperar.)
const marker = document.createElement("meta");
marker.name = "megarepartos-extension";
marker.content = chrome.runtime.getManifest().version;
(document.head || document.documentElement).appendChild(marker);

// Forward progress events del background a la página.
chrome.runtime.onMessage.addListener((msg) => {
  if (msg?.type === "MR_PROGRESS") {
    window.postMessage({ source: "mr-ext", type: "MR_PROGRESS", payload: msg }, "*");
  }
});
