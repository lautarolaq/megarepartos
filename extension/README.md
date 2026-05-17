# Megarepartos — Extensión Chrome

Automatiza el envío de mensajes de WhatsApp Web desde el dashboard de Megarepartos.

## Cómo se carga (dev, sin Chrome Web Store)

1. Abrí Chrome → `chrome://extensions/`.
2. Activá "**Developer mode**" (toggle arriba a la derecha).
3. Click **"Load unpacked"** → seleccioná la carpeta `extension/` de este repo.
4. Listo. Vas a ver "Megarepartos" en la lista de extensiones.

## Cómo funciona

```
[Dashboard /clientes]  →  [Campaña: enviar a todos]
        │
        │ window.postMessage(MR_SEND_ONE, {phone, message})
        ▼
[app-content.js] (corre en localhost / tu dominio)
        │
        │ chrome.runtime.sendMessage
        ▼
[background.js] (service worker)
        │
        │ abre o reutiliza tab de WhatsApp Web
        │ chrome.tabs.sendMessage al wa-content.js
        ▼
[wa-content.js] (corre en web.whatsapp.com)
        │
        │ 1. location.href = /send?phone=X&text=Y
        │ 2. espera que cargue la app
        │ 3. click en el botón Send
        │ 4. confirma que el compose se vació
        ▼
   Responde {ok: true} (o {ok: false, error: "..."})
```

## Requisitos en runtime

- Tener **WhatsApp Web** abierto y logueado en el navegador.
- Tener el **dashboard** abierto en una tab (la app sabe detectar la extensión).
- Permitir la extensión en `web.whatsapp.com` y en el dominio de Megarepartos
  (esto lo configura el manifest).

## Anti-detección básica (SPEC 8.4)

- Entre mensajes: delays randomizados de 800-1800 ms antes de cada click.
- Sin "fire and forget": esperamos confirmación de envío antes de continuar.
- Sin bulk parallel — envío uno a uno secuencial.

## Limitaciones del MVP

- No tiene panel propio para iniciar campañas — se dispara desde el modal
  "Campaña" del dashboard.
- No reintenta envíos fallidos automáticamente. Cada error queda visible en
  el modal del dashboard.
- WhatsApp Web cambia el DOM cada tanto y puede romper los selectores de
  `wa-content.js`. Si pasa, actualizamos los selectores.

## Distribución

Para usuarios reales: empaquetar como `.zip` y publicar en Chrome Web Store.
Esto requiere cuenta de developer (US $5 one-time) y aprobación de Google.
Mientras estamos en MVP, "Load unpacked" es suficiente.
