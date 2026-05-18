// Puente con la extensión Chrome de Megarepartos.
//
// La extensión inyecta un <meta name="megarepartos-extension"> en el head
// cuando está activa. Si no está, isExtensionInstalled() devuelve false y
// la UI cae al envío manual (wa.me) como hasta ahora.

interface SendResult {
  ok: boolean;
  error?: string;
}

interface ExtensionResponse {
  source: "mr-ext";
  reqId?: string;
  type: string;
  payload: SendResult;
}

export function isExtensionInstalled(): boolean {
  const meta = document.querySelector<HTMLMetaElement>('meta[name="megarepartos-extension"]');
  return !!meta && !!meta.content;
}

export function getExtensionVersion(): string | null {
  const meta = document.querySelector<HTMLMetaElement>('meta[name="megarepartos-extension"]');
  return meta?.content ?? null;
}

let reqIdCounter = 0;
const nextReqId = () => `mr-${Date.now()}-${++reqIdCounter}`;

function sendToExtension<TPayload extends object>(
  type: "MR_SEND_ONE" | "MR_SEND_BROADCAST",
  payload: TPayload,
  timeoutMs: number,
): Promise<SendResult> {
  return new Promise((resolve) => {
    if (!isExtensionInstalled()) {
      resolve({ ok: false, error: "Extensión no instalada." });
      return;
    }
    const reqId = nextReqId();
    const expectedRespType = `${type}_RESP`;
    let done = false;

    const onMessage = (event: MessageEvent) => {
      if (event.source !== window) return;
      const data = event.data as ExtensionResponse | undefined;
      if (
        !data ||
        data.source !== "mr-ext" ||
        data.reqId !== reqId ||
        data.type !== expectedRespType
      ) {
        return;
      }
      cleanup();
      resolve(data.payload);
    };

    const cleanup = () => {
      if (done) return;
      done = true;
      window.removeEventListener("message", onMessage);
    };

    window.addEventListener("message", onMessage);

    window.postMessage({ source: "mr-app", type, reqId, ...payload }, window.location.origin);

    setTimeout(() => {
      if (done) return;
      cleanup();
      resolve({ ok: false, error: "Timeout esperando respuesta de la extensión." });
    }, timeoutMs);
  });
}

/**
 * Le pide a la extensión que envíe un mensaje a un cliente vía WhatsApp Web.
 * Resuelve cuando la extensión confirma que se envió, o falla con error.
 */
export function sendViaExtension(
  phone: string,
  message: string,
  timeoutMs = 60_000,
): Promise<SendResult> {
  return sendToExtension("MR_SEND_ONE", { phone, message }, timeoutMs);
}

/**
 * Le pide a la extensión que envíe el mensaje a una lista de difusión existente
 * en WhatsApp Web. La extensión busca la lista por nombre exacto, la abre,
 * pega el mensaje y clickea enviar. La lista de difusión tiene que existir
 * previamente — el sodero la crea manualmente desde el menú de WA Web.
 */
export function sendBroadcastViaExtension(
  listName: string,
  message: string,
  timeoutMs = 90_000,
): Promise<SendResult> {
  return sendToExtension("MR_SEND_BROADCAST", { listName, message }, timeoutMs);
}
