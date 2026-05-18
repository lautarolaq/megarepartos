import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import {
  getExtensionVersion,
  isExtensionInstalled,
  sendBroadcastViaExtension,
  sendViaExtension,
} from "@/lib/extension";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, Package, Pencil, RotateCcw, Send, Trash2, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

interface Cliente {
  id: string;
  nombre_completo: string;
  telefono: string;
  email: string | null;
  direccion: string | null;
  zona_id: string | null;
  modalidad: string;
  frecuencia: string | null;
  observaciones_permanentes: string | null;
  condicion_pago: string;
  activo: boolean;
}

interface ClienteListResp {
  items: Cliente[];
  total: number;
  limit: number;
  offset: number;
}

interface Zona {
  id: string;
  nombre: string;
  dia_visita: string | null;
  color_display: string | null;
  activo: boolean;
}

interface LinkGenerado {
  cliente: Cliente;
  url: string;
}

type FiltroActivo = "activos" | "inactivos" | "todos";

export function ClientesPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [qDebounced, setQDebounced] = useState("");
  const [zonaFiltro, setZonaFiltro] = useState<string>("");
  const [filtroActivo, setFiltroActivo] = useState<FiltroActivo>("activos");
  const [openCreate, setOpenCreate] = useState(false);
  const [clienteHabituales, setClienteHabituales] = useState<Cliente | null>(null);
  const [linkGenerado, setLinkGenerado] = useState<LinkGenerado | null>(null);
  const [clienteEditar, setClienteEditar] = useState<Cliente | null>(null);
  const [openCampana, setOpenCampana] = useState(false);

  // Debounce simple sin librería: 300ms.
  useEffect(() => {
    const t = setTimeout(() => setQDebounced(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const { data: zonasData } = useQuery({
    queryKey: ["zonas"],
    queryFn: async (): Promise<{ items: Zona[] }> => (await api.get("/api/zonas")).data,
  });

  const zonasMap = new Map((zonasData?.items ?? []).map((z) => [z.id, z]));

  const { data, isLoading } = useQuery({
    queryKey: ["clientes", qDebounced, zonaFiltro, filtroActivo],
    queryFn: async (): Promise<ClienteListResp> => {
      const params: Record<string, string | number | boolean> = { limit: 100 };
      if (qDebounced) params.q = qDebounced;
      if (zonaFiltro) params.zona_id = zonaFiltro;
      if (filtroActivo === "activos") params.activo = true;
      else if (filtroActivo === "inactivos") params.activo = false;
      const resp = await api.get<ClienteListResp>("/api/clientes", { params });
      return resp.data;
    },
  });

  const desactivarMut = useMutation({
    mutationFn: async (id: string) => api.delete(`/api/clientes/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clientes"] }),
  });

  const reactivarMut = useMutation({
    mutationFn: async (id: string) => api.patch(`/api/clientes/${id}`, { activo: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clientes"] }),
  });

  const generarLinkMut = useMutation({
    mutationFn: async (cliente: Cliente) => {
      const resp = await api.post<{ url: string }>(`/api/clientes/${cliente.id}/generar-link`);
      return { cliente, url: resp.data.url };
    },
    onSuccess: (data) => setLinkGenerado(data),
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Clientes</h2>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => setOpenCampana(true)}>
            <Send size={14} />
            Campaña
          </Button>
          <Button onClick={() => setOpenCreate(true)}>+ Nuevo cliente</Button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <div className="min-w-[16rem] flex-1 max-w-md">
          <Input
            placeholder="Buscar por nombre o teléfono…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select
          value={zonaFiltro}
          onChange={(e) => setZonaFiltro(e.target.value)}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
        >
          <option value="">Todas las zonas</option>
          {(zonasData?.items ?? []).map((z) => (
            <option key={z.id} value={z.id}>
              {z.nombre}
            </option>
          ))}
        </select>
        <div className="inline-flex overflow-hidden rounded-md border border-slate-200 bg-white text-sm">
          {(["activos", "inactivos", "todos"] as FiltroActivo[]).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setFiltroActivo(v)}
              className={`px-3 py-2 capitalize transition-colors ${
                filtroActivo === v ? "bg-sky-600 text-white" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <p className="mt-4 text-slate-500">Buscando…</p>}
      {data && (
        <>
          <p className="mt-2 text-xs text-slate-500">
            {data.total} resultado{data.total === 1 ? "" : "s"}
          </p>
          <div className="mt-2 -mx-4 sm:mx-0 overflow-x-auto">
            <table className="w-full min-w-[720px] sm:min-w-0 overflow-hidden rounded-md border border-slate-200 bg-white text-sm sm:rounded-md">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2">Nombre</th>
                  <th className="px-4 py-2">Teléfono</th>
                  <th className="px-4 py-2">Dirección</th>
                  <th className="px-4 py-2">Zona</th>
                  <th className="px-4 py-2">Modalidad</th>
                  <th className="px-4 py-2">Estado</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                      {qDebounced || zonaFiltro ? "Sin resultados." : "No hay clientes todavía."}
                    </td>
                  </tr>
                )}
                {data.items.map((c) => (
                  <tr key={c.id} className="border-t border-slate-200">
                    <td className="px-4 py-2 font-medium">
                      <RouterLink
                        to={`/dashboard/clientes/${c.id}`}
                        className="text-slate-800 hover:text-sky-600 hover:underline"
                      >
                        {c.nombre_completo}
                      </RouterLink>
                    </td>
                    <td className="px-4 py-2 text-slate-600">{c.telefono}</td>
                    <td className="px-4 py-2 text-slate-600">{c.direccion ?? "—"}</td>
                    <td className="px-4 py-2 text-slate-600">
                      {c.zona_id ? (zonasMap.get(c.zona_id)?.nombre ?? "—") : "—"}
                    </td>
                    <td className="px-4 py-2 capitalize">{c.modalidad}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          c.activo
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {c.activo ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right">
                      {c.activo ? (
                        <div className="flex justify-end gap-3">
                          <button
                            type="button"
                            className="text-slate-600 hover:text-slate-800"
                            title="Editar"
                            onClick={() => setClienteEditar(c)}
                          >
                            <Pencil size={16} />
                          </button>
                          <button
                            type="button"
                            className="text-slate-600 hover:text-slate-800"
                            title="Productos habituales"
                            onClick={() => setClienteHabituales(c)}
                          >
                            <Package size={16} />
                          </button>
                          <button
                            type="button"
                            className="text-sky-600 hover:text-sky-800"
                            title="Enviar link por WhatsApp"
                            onClick={() => generarLinkMut.mutate(c)}
                            disabled={generarLinkMut.isPending}
                          >
                            <Link2 size={16} />
                          </button>
                          <button
                            type="button"
                            className="text-rose-600 hover:text-rose-800"
                            title="Desactivar"
                            onClick={() => {
                              if (confirm(`¿Desactivar a "${c.nombre_completo}"?`)) {
                                desactivarMut.mutate(c.id);
                              }
                            }}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      ) : (
                        <div className="flex justify-end gap-3">
                          <button
                            type="button"
                            className="inline-flex items-center gap-1 rounded-md border border-emerald-300 px-2 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-50"
                            title="Reactivar cliente"
                            onClick={() => reactivarMut.mutate(c.id)}
                            disabled={reactivarMut.isPending}
                          >
                            <RotateCcw size={12} />
                            Reactivar
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <CrearClienteModal open={openCreate} onClose={() => setOpenCreate(false)} />
      <HabitualesModal cliente={clienteHabituales} onClose={() => setClienteHabituales(null)} />
      <EnviarLinkModal data={linkGenerado} onClose={() => setLinkGenerado(null)} />
      <EditarClienteModal cliente={clienteEditar} onClose={() => setClienteEditar(null)} />
      <CampanaModal
        open={openCampana}
        zonaIdInicial={zonaFiltro}
        zonas={zonasData?.items ?? []}
        onClose={() => setOpenCampana(false)}
      />
    </div>
  );
}

interface LinkBulkItem {
  cliente_id: string;
  nombre_completo: string;
  telefono: string;
  url: string;
}

function CampanaModal({
  open,
  zonaIdInicial,
  zonas,
  onClose,
}: {
  open: boolean;
  zonaIdInicial: string;
  zonas: Zona[];
  onClose: () => void;
}) {
  const { data: empresa } = useQuery({
    queryKey: ["empresa-me"],
    queryFn: async (): Promise<{ mensaje_default_link: string | null }> =>
      (await api.get("/api/empresa/me")).data,
    enabled: open,
  });

  const mensajeBase =
    empresa?.mensaje_default_link ??
    "Hola {nombre}! Mañana pasamos por tu zona. Confirmá tu pedido en este link:\n\n{link}";

  const [zonaId, setZonaId] = useState(zonaIdInicial);
  const [items, setItems] = useState<LinkBulkItem[] | null>(null);
  const [enviados, setEnviados] = useState<Set<string>>(new Set());
  const [erroresAuto, setErroresAuto] = useState<Map<string, string>>(new Map());
  const [autoEnEjecucion, setAutoEnEjecucion] = useState(false);
  const [extensionDisponible, setExtensionDisponible] = useState(false);
  const [mensaje, setMensaje] = useState(mensajeBase);
  const [modo, setModo] = useState<"individual" | "broadcast">("individual");
  const [broadcastUrl, setBroadcastUrl] = useState<string | null>(null);
  const [broadcastCopied, setBroadcastCopied] = useState<"link" | "mensaje" | null>(null);
  // Nombre de la lista de difusión en WhatsApp Web (persistido en localStorage
  // para auto-completar la próxima vez).
  const [broadcastListName, setBroadcastListName] = useState<string>(
    () => localStorage.getItem("mr_broadcast_list_name") ?? "",
  );
  const [broadcastAutoEnviando, setBroadcastAutoEnviando] = useState(false);
  const [broadcastAutoResult, setBroadcastAutoResult] = useState<
    { ok: true } | { ok: false; error: string } | null
  >(null);

  // Resetear estado SOLO cuando el modal se abre. Si incluimos mensajeBase en las
  // deps, la response de /api/empresa/me llegando después de "Generar links"
  // reseteaba items=null y volvíamos al paso 1 perdiendo los links generados.
  useEffect(() => {
    if (open) {
      setZonaId(zonaIdInicial);
      setItems(null);
      setEnviados(new Set());
      setErroresAuto(new Map());
      setAutoEnEjecucion(false);
      setExtensionDisponible(isExtensionInstalled());
      setModo("individual");
      setBroadcastUrl(null);
      setBroadcastCopied(null);
      setBroadcastAutoEnviando(false);
      setBroadcastAutoResult(null);
    }
  }, [open, zonaIdInicial]);

  // Sincronizar el mensaje con el default de la empresa cuando llegue. Es OK
  // que esto reaccione a `open` también — solo cambia `mensaje`, no `items`.
  useEffect(() => {
    if (open) setMensaje(mensajeBase);
  }, [open, mensajeBase]);

  const generar = useMutation({
    mutationFn: async () => {
      const body: { zona_id?: string } = {};
      if (zonaId) body.zona_id = zonaId;
      const resp = await api.post<{ items: LinkBulkItem[] }>(
        "/api/clientes/generar-links-bulk",
        body,
      );
      return resp.data.items;
    },
    onSuccess: (data) => {
      setItems(data);
      setEnviados(new Set());
    },
  });

  const generarBroadcast = useMutation({
    mutationFn: async () => {
      const resp = await api.post<{ url: string }>("/api/clientes/generar-link-broadcast", {});
      return resp.data.url;
    },
    onSuccess: (url) => {
      setBroadcastUrl(url);
      setBroadcastCopied(null);
    },
  });

  // En modo broadcast el mensaje no tiene {nombre} (es genérico). Sustituimos
  // {link} por el broadcastUrl al copiar.
  const mensajeBroadcast = (() => {
    if (!broadcastUrl) return mensaje;
    // Si el user dejó el {nombre} en el template, lo reemplazamos por algo
    // genérico cordial. {link} se reemplaza por la URL del broadcast.
    return mensaje.replace(/\{nombre\}/g, "🚚").replace(/\{link\}/g, broadcastUrl);
  })();

  async function copiar(text: string, tipo: "link" | "mensaje") {
    try {
      await navigator.clipboard.writeText(text);
      setBroadcastCopied(tipo);
      setTimeout(() => setBroadcastCopied(null), 2000);
    } catch {
      // navigator.clipboard puede no estar disponible en contextos no-https.
      // Fallback: seleccionar el contenido del textarea para copy manual.
      window.prompt("Copiá este texto:", text);
    }
  }

  async function enviarBroadcastAuto() {
    const nombre = broadcastListName.trim();
    if (!nombre) {
      setBroadcastAutoResult({ ok: false, error: "Ingresá el nombre exacto de la lista." });
      return;
    }
    if (!broadcastUrl) return;
    localStorage.setItem("mr_broadcast_list_name", nombre);
    setBroadcastAutoEnviando(true);
    setBroadcastAutoResult(null);
    const resp = await sendBroadcastViaExtension(nombre, mensajeBroadcast);
    setBroadcastAutoEnviando(false);
    setBroadcastAutoResult(
      resp.ok ? { ok: true } : { ok: false, error: resp.error ?? "Error desconocido." },
    );
  }

  function mensajeFor(item: LinkBulkItem): string {
    const primer = item.nombre_completo.split(" ")[0];
    return mensaje.replace(/\{nombre\}/g, primer).replace(/\{link\}/g, item.url);
  }

  function waUrl(item: LinkBulkItem): string {
    const tel = item.telefono.replace(/\D/g, "");
    return `https://wa.me/${tel}?text=${encodeURIComponent(mensajeFor(item))}`;
  }

  function marcarEnviado(id: string) {
    setEnviados((prev) => {
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  }

  async function enviarTodoAutomatico() {
    if (!items || autoEnEjecucion) return;
    setAutoEnEjecucion(true);
    setErroresAuto(new Map());
    for (const it of items) {
      if (enviados.has(it.cliente_id)) continue;
      const resp = await sendViaExtension(it.telefono, mensajeFor(it));
      if (resp.ok) {
        setEnviados((prev) => {
          const next = new Set(prev);
          next.add(it.cliente_id);
          return next;
        });
      } else {
        setErroresAuto((prev) => {
          const next = new Map(prev);
          next.set(it.cliente_id, resp.error ?? "Error desconocido");
          return next;
        });
      }
      // Delay anti-detección entre clientes (la extensión también tiene su delay interno).
      await new Promise((r) => setTimeout(r, 1500 + Math.random() * 2000));
    }
    setAutoEnEjecucion(false);
  }

  return (
    <Modal open={open} onClose={onClose} title="Campaña — enviar a varios">
      <div className="flex flex-col gap-3">
        {!items && (
          <>
            {/* Toggle modo: individual (link por cliente) vs broadcast (UN link genérico). */}
            <div className="flex rounded-md bg-slate-100 p-1 text-xs font-medium">
              <button
                type="button"
                onClick={() => setModo("individual")}
                className={`flex-1 rounded px-3 py-1.5 transition ${
                  modo === "individual" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"
                }`}
              >
                Individual (1 link x cliente)
              </button>
              <button
                type="button"
                onClick={() => setModo("broadcast")}
                className={`flex-1 rounded px-3 py-1.5 transition ${
                  modo === "broadcast" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"
                }`}
              >
                Broadcast (1 link genérico)
              </button>
            </div>

            {modo === "individual" && (
              <>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium text-slate-700">Zona</span>
                  <select
                    value={zonaId}
                    onChange={(e) => setZonaId(e.target.value)}
                    className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                  >
                    <option value="">Todas las zonas (todos los clientes activos)</option>
                    {zonas.map((z) => (
                      <option key={z.id} value={z.id}>
                        {z.nombre}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium text-slate-700">
                    Mensaje (usá {"{nombre}"} y {"{link}"})
                  </span>
                  <textarea
                    rows={4}
                    value={mensaje}
                    onChange={(e) => setMensaje(e.target.value)}
                    className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                  />
                </label>
                <div className="mt-2 flex justify-end gap-2">
                  <Button variant="ghost" onClick={onClose}>
                    Cancelar
                  </Button>
                  <Button onClick={() => generar.mutate()} disabled={generar.isPending}>
                    {generar.isPending ? "Generando…" : "Generar links"}
                  </Button>
                </div>
              </>
            )}

            {modo === "broadcast" && (
              <>
                <p className="rounded-md bg-sky-50 px-3 py-2 text-xs text-sky-900">
                  El broadcast manda <strong>UN solo link genérico</strong> a hasta 256 contactos de
                  tu WhatsApp. Solo lo reciben los clientes que tienen tu número guardado. Cuando
                  abren el link tipean su teléfono y se identifican.
                </p>

                {!broadcastUrl && (
                  <>
                    <label className="flex flex-col gap-1 text-sm">
                      <span className="font-medium text-slate-700">
                        Mensaje (usá {"{link}"} donde quieras que vaya la URL)
                      </span>
                      <textarea
                        rows={4}
                        value={mensaje}
                        onChange={(e) => setMensaje(e.target.value)}
                        className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                      />
                      <span className="text-xs text-slate-500">
                        Tip: no uses {"{nombre}"} acá — el mensaje va igual a todos.
                      </span>
                    </label>
                    <div className="mt-2 flex justify-end gap-2">
                      <Button variant="ghost" onClick={onClose}>
                        Cancelar
                      </Button>
                      <Button
                        onClick={() => generarBroadcast.mutate()}
                        disabled={generarBroadcast.isPending}
                      >
                        {generarBroadcast.isPending ? "Generando…" : "Generar link broadcast"}
                      </Button>
                    </div>
                  </>
                )}

                {broadcastUrl && (
                  <>
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                      <p className="font-medium text-slate-700">Mensaje listo para pegar:</p>
                      <pre className="mt-2 whitespace-pre-wrap break-words rounded bg-white p-2 text-xs text-slate-800">
                        {mensajeBroadcast}
                      </pre>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Button onClick={() => copiar(mensajeBroadcast, "mensaje")}>
                          {broadcastCopied === "mensaje" ? "✓ Copiado" : "Copiar mensaje completo"}
                        </Button>
                        <Button variant="ghost" onClick={() => copiar(broadcastUrl, "link")}>
                          {broadcastCopied === "link" ? "✓ Copiado" : "Solo el link"}
                        </Button>
                      </div>
                    </div>

                    {extensionDisponible && (
                      <div className="rounded-md border border-sky-200 bg-sky-50 p-3">
                        <div className="text-sm font-medium text-sky-900">
                          ⚡ Enviar broadcast automático
                        </div>
                        <p className="mt-1 text-xs text-sky-800">
                          Si ya tenés una lista de difusión creada en WhatsApp Web con todos los
                          destinatarios, escribí el nombre exacto y la extensión se encarga del
                          resto.
                        </p>
                        <Input
                          className="mt-2"
                          placeholder='Ej: "Clientes Megarepartos"'
                          value={broadcastListName}
                          onChange={(e) => setBroadcastListName(e.target.value)}
                          disabled={broadcastAutoEnviando}
                        />
                        <div className="mt-2">
                          <Button
                            onClick={enviarBroadcastAuto}
                            disabled={broadcastAutoEnviando || !broadcastListName.trim()}
                          >
                            <Zap size={14} />
                            {broadcastAutoEnviando ? "Enviando…" : "Enviar broadcast ahora"}
                          </Button>
                        </div>
                        {broadcastAutoResult?.ok === true && (
                          <p className="mt-2 rounded bg-emerald-100 px-2 py-1 text-xs text-emerald-900">
                            ✓ Broadcast enviado.
                          </p>
                        )}
                        {broadcastAutoResult?.ok === false && (
                          <p className="mt-2 rounded bg-rose-100 px-2 py-1 text-xs text-rose-900">
                            ✗ {broadcastAutoResult.error}
                          </p>
                        )}
                      </div>
                    )}

                    <ol className="list-decimal space-y-1 pl-5 text-xs text-slate-600">
                      <li>Abrí WhatsApp Web (o WhatsApp en el celu).</li>
                      <li>Menú ⋮ → "Nueva difusión" / "Nueva lista de difusión".</li>
                      <li>Seleccioná los clientes destinatarios (máx 256).</li>
                      <li>
                        {extensionDisponible ? (
                          <>Una vez creada, escribí su nombre arriba y "Enviar broadcast ahora".</>
                        ) : (
                          <>Pegá el mensaje copiado y enviá.</>
                        )}
                      </li>
                    </ol>

                    <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900">
                      ⚠ Recordá: solo reciben el broadcast los que tienen tu número guardado en su
                      celu. Para clientes que no te tienen agendado, usá el modo Individual.
                    </p>

                    <div className="mt-2 flex justify-between">
                      <Button variant="ghost" onClick={() => setBroadcastUrl(null)}>
                        ← Volver
                      </Button>
                      <Button onClick={onClose}>Cerrar</Button>
                    </div>
                  </>
                )}
              </>
            )}
          </>
        )}

        {items && (
          <>
            <p className="text-sm text-slate-600">
              Tocá <strong>Enviar</strong> para abrir WhatsApp con el chat y el mensaje listo. Marcá
              los que ya enviaste para no perderte ninguno.
            </p>

            {extensionDisponible && items.length > 0 && (
              <div className="rounded-md border border-sky-200 bg-sky-50 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm text-sky-900">
                    <strong>Extensión Megarepartos detectada</strong>{" "}
                    <span className="text-xs text-sky-700">(v{getExtensionVersion()})</span>
                    <p className="text-xs text-sky-700">
                      Podés enviar todos automáticamente desde tu WhatsApp Web.
                    </p>
                  </div>
                  <Button
                    onClick={enviarTodoAutomatico}
                    disabled={autoEnEjecucion || enviados.size === items.length}
                  >
                    <Zap size={14} />
                    {autoEnEjecucion ? "Enviando…" : "Enviar todos auto"}
                  </Button>
                </div>
              </div>
            )}

            <p className="text-xs text-slate-500">
              {enviados.size} / {items.length} enviados
              {erroresAuto.size > 0 && (
                <span className="ml-2 text-rose-600">· {erroresAuto.size} con error</span>
              )}
            </p>

            {items.length === 0 && (
              <p className="rounded-md bg-slate-50 p-3 text-sm text-slate-500">
                No hay clientes activos en este filtro.
              </p>
            )}

            <ul className="flex max-h-80 flex-col gap-1 overflow-y-auto">
              {items.map((it) => {
                const enviado = enviados.has(it.cliente_id);
                const errorMsg = erroresAuto.get(it.cliente_id);
                return (
                  <li
                    key={it.cliente_id}
                    className={`rounded-md border px-3 py-2 ${
                      enviado
                        ? "border-emerald-200 bg-emerald-50"
                        : errorMsg
                          ? "border-rose-200 bg-rose-50"
                          : "border-slate-200 bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-slate-700">
                          {it.nombre_completo}
                        </p>
                        <p className="text-xs text-slate-500">{it.telefono}</p>
                      </div>
                      <a
                        href={waUrl(it)}
                        target="_blank"
                        rel="noreferrer"
                        onClick={() => marcarEnviado(it.cliente_id)}
                        className="inline-flex items-center gap-1 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700"
                      >
                        {enviado ? "✓ Enviado" : "Enviar"}
                      </a>
                    </div>
                    {errorMsg && <p className="mt-1 text-xs text-rose-700">{errorMsg}</p>}
                  </li>
                );
              })}
            </ul>

            <div className="mt-2 flex justify-between">
              <Button variant="ghost" onClick={() => setItems(null)}>
                ← Volver
              </Button>
              <Button onClick={onClose}>Cerrar</Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}

function EditarClienteModal({
  cliente,
  onClose,
}: {
  cliente: Cliente | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [telefono, setTelefono] = useState("");
  const [email, setEmail] = useState("");
  const [direccion, setDireccion] = useState("");
  const [zonaId, setZonaId] = useState("");
  const [modalidad, setModalidad] = useState<"fijo" | "consulta" | "demanda">("consulta");
  const [frecuencia, setFrecuencia] = useState<"semanal" | "quincenal" | "mensual" | "">("");
  const [condicionPago, setCondicionPago] = useState<"contado" | "cuenta_corriente">("contado");
  const [observaciones, setObservaciones] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: zonasData } = useQuery({
    queryKey: ["zonas"],
    queryFn: async (): Promise<{ items: Zona[] }> => (await api.get("/api/zonas")).data,
    enabled: !!cliente,
  });

  useEffect(() => {
    if (cliente) {
      setNombre(cliente.nombre_completo);
      setTelefono(cliente.telefono);
      setEmail(cliente.email ?? "");
      setDireccion(cliente.direccion ?? "");
      setZonaId(cliente.zona_id ?? "");
      setModalidad((cliente.modalidad as "fijo" | "consulta" | "demanda") ?? "consulta");
      setFrecuencia((cliente.frecuencia as "semanal" | "quincenal" | "mensual" | null) ?? "");
      setCondicionPago((cliente.condicion_pago as "contado" | "cuenta_corriente") ?? "contado");
      setObservaciones(cliente.observaciones_permanentes ?? "");
      setError(null);
    }
  }, [cliente]);

  const actualizar = useMutation({
    mutationFn: async () => {
      if (!cliente) throw new Error("missing cliente");
      return api.patch(`/api/clientes/${cliente.id}`, {
        nombre_completo: nombre,
        telefono,
        email: email || null,
        direccion: direccion || null,
        zona_id: zonaId || null,
        modalidad,
        frecuencia: frecuencia || null,
        condicion_pago: condicionPago,
        observaciones_permanentes: observaciones || null,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clientes"] });
      onClose();
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setError(e.response?.data?.error?.message ?? "Error al actualizar cliente.");
    },
  });

  return (
    <Modal open={!!cliente} onClose={onClose} title="Editar cliente">
      <div className="flex flex-col gap-3">
        <Input
          label="Nombre completo"
          name="nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
        <Input
          label="Teléfono"
          name="telefono"
          value={telefono}
          onChange={(e) => setTelefono(e.target.value)}
        />
        <Input
          label="Email"
          name="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Input
          label="Dirección"
          name="direccion"
          value={direccion}
          onChange={(e) => setDireccion(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Zona</span>
            <select
              value={zonaId}
              onChange={(e) => setZonaId(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            >
              <option value="">Sin zona</option>
              {(zonasData?.items ?? []).map((z) => (
                <option key={z.id} value={z.id}>
                  {z.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Modalidad</span>
            <select
              value={modalidad}
              onChange={(e) => setModalidad(e.target.value as "fijo" | "consulta" | "demanda")}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            >
              <option value="consulta">Consulta</option>
              <option value="fijo">Fijo</option>
              <option value="demanda">Demanda</option>
            </select>
          </label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Frecuencia</span>
            <select
              value={frecuencia}
              onChange={(e) =>
                setFrecuencia(e.target.value as "semanal" | "quincenal" | "mensual" | "")
              }
              className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            >
              <option value="">Sin definir</option>
              <option value="semanal">Semanal</option>
              <option value="quincenal">Quincenal</option>
              <option value="mensual">Mensual</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Cond. de pago</span>
            <select
              value={condicionPago}
              onChange={(e) => setCondicionPago(e.target.value as "contado" | "cuenta_corriente")}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            >
              <option value="contado">Contado</option>
              <option value="cuenta_corriente">Cuenta corriente</option>
            </select>
          </label>
        </div>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Observaciones</span>
          <textarea
            rows={2}
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
            placeholder="ej: timbre roto, dejar en portería"
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
        </label>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={() => actualizar.mutate()}
            disabled={!nombre.trim() || !telefono.trim() || actualizar.isPending}
          >
            {actualizar.isPending ? "Guardando…" : "Guardar"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function soloNumeros(s: string): string {
  return s.replace(/\D/g, "");
}

function EnviarLinkModal({
  data,
  onClose,
}: {
  data: LinkGenerado | null;
  onClose: () => void;
}) {
  const { data: empresa } = useQuery({
    queryKey: ["empresa-me"],
    queryFn: async (): Promise<{ mensaje_default_link: string | null }> =>
      (await api.get("/api/empresa/me")).data,
    enabled: !!data,
  });

  const primerNombre = data?.cliente.nombre_completo.split(" ")[0] ?? "";
  const plantilla =
    empresa?.mensaje_default_link ??
    "Hola {nombre}! Mañana pasamos por tu zona. Confirmá tu pedido en este link:\n\n{link}";
  const mensajeDefault = data
    ? plantilla.replace(/\{nombre\}/g, primerNombre).replace(/\{link\}/g, data.url)
    : "";
  const [mensaje, setMensaje] = useState(mensajeDefault);
  const [copiado, setCopiado] = useState<"link" | "mensaje" | null>(null);

  useEffect(() => {
    setMensaje(mensajeDefault);
    setCopiado(null);
  }, [mensajeDefault]);

  if (!data) return null;
  const datos = data;

  const telDigits = soloNumeros(datos.cliente.telefono);
  const waUrl = `https://wa.me/${telDigits}?text=${encodeURIComponent(mensaje)}`;

  async function copiar(qué: "link" | "mensaje") {
    const texto = qué === "link" ? datos.url : mensaje;
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(qué);
      setTimeout(() => setCopiado(null), 2000);
    } catch {
      // fallback nada — el usuario puede copiar manualmente.
    }
  }

  return (
    <Modal open={!!data} onClose={onClose} title={`Enviar link a ${primerNombre}`}>
      <div className="flex flex-col gap-3">
        <div>
          <label
            htmlFor="enviar-link-url"
            className="text-xs font-medium uppercase tracking-wider text-slate-500"
          >
            Link
          </label>
          <div className="mt-1 flex gap-2">
            <input
              id="enviar-link-url"
              readOnly
              value={datos.url}
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-700"
              onFocus={(e) => e.currentTarget.select()}
            />
            <Button variant="ghost" onClick={() => copiar("link")}>
              {copiado === "link" ? "✓ Copiado" : "Copiar"}
            </Button>
          </div>
        </div>

        <div>
          <label
            htmlFor="enviar-link-mensaje"
            className="text-xs font-medium uppercase tracking-wider text-slate-500"
          >
            Mensaje
          </label>
          <textarea
            id="enviar-link-mensaje"
            rows={5}
            value={mensaje}
            onChange={(e) => setMensaje(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
        </div>

        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <Button variant="ghost" onClick={() => copiar("mensaje")}>
            {copiado === "mensaje" ? "✓ Mensaje copiado" : "Copiar mensaje"}
          </Button>
          <a
            href={waUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-emerald-700"
            onClick={onClose}
          >
            Abrir WhatsApp
          </a>
        </div>
      </div>
    </Modal>
  );
}

interface Producto {
  id: string;
  nombre: string;
  es_retornable: boolean;
  activo: boolean;
}

interface HabitualItem {
  producto_id: string;
  cantidad: number;
  nombre: string;
  es_retornable: boolean;
}

function HabitualesModal({
  cliente,
  onClose,
}: {
  cliente: Cliente | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [items, setItems] = useState<HabitualItem[]>([]);
  const [agregarId, setAgregarId] = useState<string>("");

  const { data: habituales, isLoading } = useQuery({
    queryKey: ["habituales", cliente?.id],
    queryFn: async (): Promise<{ items: HabitualItem[] }> => {
      if (!cliente) throw new Error("missing cliente");
      return (await api.get(`/api/clientes/${cliente.id}/productos-habituales`)).data;
    },
    enabled: !!cliente,
  });

  const { data: productos } = useQuery({
    queryKey: ["productos"],
    queryFn: async (): Promise<{ items: Producto[] }> => (await api.get("/api/productos")).data,
    enabled: !!cliente,
  });

  useEffect(() => {
    if (habituales) setItems(habituales.items);
  }, [habituales]);

  const guardar = useMutation({
    mutationFn: async () => {
      if (!cliente) throw new Error("missing cliente");
      const payload = {
        items: items.map((it) => ({ producto_id: it.producto_id, cantidad: it.cantidad })),
      };
      return api.put(`/api/clientes/${cliente.id}/productos-habituales`, payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["habituales", cliente?.id] });
      onClose();
    },
  });

  function setCantidad(producto_id: string, cantidad: number) {
    setItems((prev) =>
      prev.map((it) =>
        it.producto_id === producto_id ? { ...it, cantidad: Math.max(0, cantidad) } : it,
      ),
    );
  }

  function quitar(producto_id: string) {
    setItems((prev) => prev.filter((it) => it.producto_id !== producto_id));
  }

  function agregar() {
    if (!agregarId || !productos) return;
    const prod = productos.items.find((p) => p.id === agregarId);
    if (!prod) return;
    if (items.some((it) => it.producto_id === prod.id)) return;
    setItems((prev) => [
      ...prev,
      { producto_id: prod.id, cantidad: 1, nombre: prod.nombre, es_retornable: prod.es_retornable },
    ]);
    setAgregarId("");
  }

  const disponibles =
    productos?.items.filter((p) => p.activo && !items.some((it) => it.producto_id === p.id)) ?? [];

  return (
    <Modal
      open={!!cliente}
      onClose={onClose}
      title={cliente ? `Productos habituales — ${cliente.nombre_completo}` : ""}
    >
      <div className="flex flex-col gap-3">
        {isLoading && <p className="text-sm text-slate-500">Cargando…</p>}

        {!isLoading && items.length === 0 && (
          <p className="rounded-md bg-slate-50 p-3 text-sm text-slate-500">
            Sin productos habituales. Agregá los que el cliente compra siempre — se prefijan en el
            link público.
          </p>
        )}

        {items.length > 0 && (
          <ul className="flex flex-col gap-2">
            {items.map((it) => (
              <li
                key={it.producto_id}
                className="flex items-center justify-between gap-3 rounded-md border border-slate-200 px-3 py-2"
              >
                <span className="flex-1 truncate text-sm font-medium text-slate-700">
                  {it.nombre}
                </span>
                <input
                  type="number"
                  min={0}
                  value={it.cantidad}
                  onChange={(e) => setCantidad(it.producto_id, Number(e.target.value))}
                  className="w-16 rounded-md border border-slate-300 px-2 py-1 text-right text-sm"
                />
                <button
                  type="button"
                  className="text-rose-500 hover:text-rose-700"
                  onClick={() => quitar(it.producto_id)}
                  title="Quitar"
                >
                  <Trash2 size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}

        {disponibles.length > 0 && (
          <div className="mt-2 flex gap-2">
            <select
              value={agregarId}
              onChange={(e) => setAgregarId(e.target.value)}
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            >
              <option value="">Agregar producto…</option>
              {disponibles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre}
                </option>
              ))}
            </select>
            <Button variant="ghost" onClick={agregar} disabled={!agregarId}>
              + Agregar
            </Button>
          </div>
        )}

        <div className="mt-3 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={() => guardar.mutate()} disabled={guardar.isPending}>
            {guardar.isPending ? "Guardando…" : "Guardar"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function CrearClienteModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [telefono, setTelefono] = useState("");
  const [email, setEmail] = useState("");
  const [direccion, setDireccion] = useState("");
  const [zonaId, setZonaId] = useState("");
  const [modalidad, setModalidad] = useState<"fijo" | "consulta" | "demanda">("consulta");
  const [frecuencia, setFrecuencia] = useState<"semanal" | "quincenal" | "mensual" | "">("");
  const [condicionPago, setCondicionPago] = useState<"contado" | "cuenta_corriente">("contado");
  const [observaciones, setObservaciones] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: zonasData } = useQuery({
    queryKey: ["zonas"],
    queryFn: async (): Promise<{ items: Zona[] }> => (await api.get("/api/zonas")).data,
    enabled: open,
  });

  function reset() {
    setNombre("");
    setTelefono("");
    setEmail("");
    setDireccion("");
    setZonaId("");
    setModalidad("consulta");
    setFrecuencia("");
    setCondicionPago("contado");
    setObservaciones("");
    setError(null);
  }

  const crear = useMutation({
    mutationFn: async () =>
      api.post("/api/clientes", {
        nombre_completo: nombre,
        telefono,
        email: email || null,
        direccion: direccion || null,
        zona_id: zonaId || null,
        modalidad,
        frecuencia: frecuencia || null,
        condicion_pago: condicionPago,
        observaciones_permanentes: observaciones || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clientes"] });
      reset();
      onClose();
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setError(e.response?.data?.error?.message ?? "Error al crear cliente.");
    },
  });

  return (
    <Modal open={open} onClose={onClose} title="Nuevo cliente">
      <div className="flex flex-col gap-3">
        <Input
          label="Nombre completo"
          name="nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Juan García"
        />
        <Input
          label="Teléfono"
          name="telefono"
          value={telefono}
          onChange={(e) => setTelefono(e.target.value)}
          placeholder="351 555 1234"
        />
        <Input
          label="Email (opcional)"
          name="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="juan@gmail.com"
        />
        <Input
          label="Dirección (opcional)"
          name="direccion"
          value={direccion}
          onChange={(e) => setDireccion(e.target.value)}
          placeholder="Av. Colón 123"
        />
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Zona</span>
            <select
              value={zonaId}
              onChange={(e) => setZonaId(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            >
              <option value="">Sin zona</option>
              {(zonasData?.items ?? []).map((z) => (
                <option key={z.id} value={z.id}>
                  {z.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Modalidad</span>
            <select
              value={modalidad}
              onChange={(e) => setModalidad(e.target.value as "fijo" | "consulta" | "demanda")}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            >
              <option value="consulta">Consulta</option>
              <option value="fijo">Fijo</option>
              <option value="demanda">Demanda</option>
            </select>
          </label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Frecuencia</span>
            <select
              value={frecuencia}
              onChange={(e) =>
                setFrecuencia(e.target.value as "semanal" | "quincenal" | "mensual" | "")
              }
              className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            >
              <option value="">Sin definir</option>
              <option value="semanal">Semanal</option>
              <option value="quincenal">Quincenal</option>
              <option value="mensual">Mensual</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Cond. de pago</span>
            <select
              value={condicionPago}
              onChange={(e) => setCondicionPago(e.target.value as "contado" | "cuenta_corriente")}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            >
              <option value="contado">Contado</option>
              <option value="cuenta_corriente">Cuenta corriente</option>
            </select>
          </label>
        </div>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Observaciones (opcional)</span>
          <textarea
            rows={2}
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
            placeholder="ej: timbre roto, dejar en portería"
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
        </label>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={() => crear.mutate()}
            disabled={!nombre.trim() || !telefono.trim() || crear.isPending}
          >
            {crear.isPending ? "Creando…" : "Crear"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
