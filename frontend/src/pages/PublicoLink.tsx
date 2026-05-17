import { useMutation, useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface ProductoHabitual {
  producto_id: string;
  nombre: string;
  cantidad_habitual: number;
  es_retornable: boolean;
}

interface LinkPublico {
  empresa: { nombre: string };
  cliente: { nombre_completo: string; telefono: string };
  zona_nombre: string | null;
  zona_dia_visita: string | null;
  productos_habituales: ProductoHabitual[];
}

const DIA_LABEL: Record<string, string> = {
  lunes: "el lunes",
  martes: "el martes",
  miercoles: "el miércoles",
  jueves: "el jueves",
  viernes: "el viernes",
  sabado: "el sábado",
  domingo: "el domingo",
};

type Estado = "pregunta" | "confirmado" | "rechazado";

interface ItemEstado {
  cantidad_llenos: number;
  cantidad_vacios: number;
}

export function PublicoLinkPage() {
  const { token } = useParams<{ token: string }>();
  const [estado, setEstado] = useState<Estado>("pregunta");
  const [items, setItems] = useState<Record<string, ItemEstado>>({});
  const [observacion, setObservacion] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["publico", token],
    queryFn: async (): Promise<LinkPublico> => {
      const resp = await axios.get<LinkPublico>(`${API_BASE}/api/publico/c/${token}`);
      return resp.data;
    },
    enabled: !!token,
    retry: false,
  });

  // Inicializar cantidades con las habituales cuando llega la data.
  useEffect(() => {
    if (data?.productos_habituales) {
      const init: Record<string, ItemEstado> = {};
      for (const p of data.productos_habituales) {
        init[p.producto_id] = {
          cantidad_llenos: p.cantidad_habitual,
          cantidad_vacios: p.es_retornable ? p.cantidad_habitual : 0,
        };
      }
      setItems(init);
    }
  }, [data]);

  const responder = useMutation({
    mutationFn: async (accion: "confirmo" | "rechazo") => {
      const productos =
        accion === "confirmo" && data
          ? data.productos_habituales.map((p) => ({
              producto_id: p.producto_id,
              cantidad_llenos: items[p.producto_id]?.cantidad_llenos ?? 0,
              cantidad_vacios: items[p.producto_id]?.cantidad_vacios ?? 0,
            }))
          : [];
      return axios.post(`${API_BASE}/api/publico/c/${token}/respuesta`, {
        accion,
        productos,
        observacion: observacion || null,
      });
    },
    onSuccess: (_resp, accion) => {
      setEstado(accion === "confirmo" ? "confirmado" : "rechazado");
    },
  });

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-sky-50 px-4 text-slate-600">
        <p>Cargando…</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-rose-50 px-4 text-rose-800">
        <div className="text-center">
          <h1 className="text-xl font-semibold">Link no válido</h1>
          <p className="mt-2 text-sm text-rose-600">
            Este link expiró o no es correcto. Pedile uno nuevo a tu sodería.
          </p>
        </div>
      </main>
    );
  }

  const primerNombre = data.cliente.nombre_completo.split(" ")[0];
  const tieneHabituales = data.productos_habituales.length > 0;

  if (estado === "confirmado") {
    const resumenLlenos = data.productos_habituales
      .map((p) => ({ p, qty: items[p.producto_id]?.cantidad_llenos ?? 0 }))
      .filter((x) => x.qty > 0);
    const resumenVacios = data.productos_habituales
      .map((p) => ({ p, qty: items[p.producto_id]?.cantidad_vacios ?? 0 }))
      .filter((x) => x.p.es_retornable && x.qty > 0);
    return (
      <main className="flex min-h-screen flex-col items-center bg-emerald-50 px-4 py-10 text-emerald-900">
        <div className="w-full max-w-md">
          <div className="text-center text-5xl">✓</div>
          <h1 className="mt-2 text-center text-2xl font-semibold">¡Listo, {primerNombre}!</h1>
          {resumenLlenos.length > 0 ? (
            <>
              <p className="mt-6 text-base text-emerald-800">Mañana pasamos con:</p>
              <ul className="mt-2 space-y-1 text-emerald-900">
                {resumenLlenos.map(({ p, qty }) => (
                  <li key={p.producto_id}>
                    • {qty} × {p.nombre}
                  </li>
                ))}
              </ul>
              {resumenVacios.length > 0 && (
                <>
                  <p className="mt-4 text-base text-emerald-800">Llevamos para devolución:</p>
                  <ul className="mt-2 space-y-1 text-emerald-900">
                    {resumenVacios.map(({ p, qty }) => (
                      <li key={p.producto_id}>
                        • {qty} × {p.nombre} (vacíos)
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : (
            <p className="mt-3 text-center text-base text-emerald-700">
              Mañana pasamos con tu pedido.
            </p>
          )}
          <p className="mt-10 text-center text-sm text-emerald-600">{data.empresa.nombre}</p>
        </div>
      </main>
    );
  }

  if (estado === "rechazado") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-slate-100 px-4 py-8 text-slate-700">
        <div className="max-w-md text-center">
          <div className="mb-4 text-5xl">👍</div>
          <h1 className="text-2xl font-semibold">Entendido, {primerNombre}.</h1>
          <p className="mt-3 text-base text-slate-600">
            No pasamos esta semana. Te avisamos la próxima.
          </p>
          <p className="mt-8 text-sm text-slate-500">{data.empresa.nombre}</p>
        </div>
      </main>
    );
  }

  function delta(producto_id: string, key: "cantidad_llenos" | "cantidad_vacios", d: number) {
    setItems((prev) => {
      const cur = prev[producto_id] ?? { cantidad_llenos: 0, cantidad_vacios: 0 };
      const next = { ...cur, [key]: Math.max(0, cur[key] + d) };
      return { ...prev, [producto_id]: next };
    });
  }

  const diaTxt =
    data.zona_dia_visita && DIA_LABEL[data.zona_dia_visita]
      ? DIA_LABEL[data.zona_dia_visita]
      : "mañana";
  const zonaTxt = data.zona_nombre ? ` por ${data.zona_nombre}` : " por tu zona";
  const cuando = `Pasamos ${diaTxt}${zonaTxt}.`;

  return (
    <main className="flex min-h-screen flex-col items-center bg-sky-50 px-4 py-8 text-slate-800">
      <div className="w-full max-w-md">
        <p className="text-sm uppercase tracking-wider text-sky-700">{data.empresa.nombre}</p>
        <h1 className="mt-2 text-3xl font-semibold leading-tight">¡Hola, {primerNombre}!</h1>
        <p className="mt-4 text-base text-slate-600">
          {cuando} {tieneHabituales ? "Confirmá tu pedido:" : "¿Te llevamos tu pedido?"}
        </p>

        {tieneHabituales && (
          <div className="mt-6 space-y-4">
            {data.productos_habituales.map((p) => {
              const it = items[p.producto_id] ?? { cantidad_llenos: 0, cantidad_vacios: 0 };
              return (
                <div key={p.producto_id} className="rounded-xl bg-white p-4 shadow-sm">
                  <h3 className="text-lg font-semibold text-slate-800">{p.nombre}</h3>
                  <div className="mt-3">
                    <p className="text-sm text-slate-600">¿Cuántos llenos querés?</p>
                    <Counter
                      value={it.cantidad_llenos}
                      onChange={(d) => delta(p.producto_id, "cantidad_llenos", d)}
                    />
                  </div>
                  {p.es_retornable && (
                    <div className="mt-3">
                      <p className="text-sm text-slate-600">¿Cuántos vacíos devolvés?</p>
                      <Counter
                        value={it.cantidad_vacios}
                        onChange={(d) => delta(p.producto_id, "cantidad_vacios", d)}
                      />
                    </div>
                  )}
                </div>
              );
            })}
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <label className="text-sm text-slate-700" htmlFor="obs">
                ¿Querés agregar algo?
              </label>
              <textarea
                id="obs"
                rows={2}
                value={observacion}
                onChange={(e) => setObservacion(e.target.value)}
                placeholder="(opcional)"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
        )}

        <div className="mt-8 flex flex-col gap-3">
          <button
            type="button"
            disabled={responder.isPending}
            onClick={() => responder.mutate("confirmo")}
            className="rounded-xl bg-emerald-600 px-6 py-5 text-lg font-semibold text-white shadow-md transition-colors hover:bg-emerald-700 active:bg-emerald-800 disabled:opacity-60"
          >
            ✓ Sí, pasen mañana
          </button>
          <button
            type="button"
            disabled={responder.isPending}
            onClick={() => responder.mutate("rechazo")}
            className="rounded-xl border-2 border-slate-300 bg-white px-6 py-5 text-lg font-semibold text-slate-700 shadow-sm transition-colors hover:bg-slate-50 active:bg-slate-100 disabled:opacity-60"
          >
            ✗ Esta semana no
          </button>
        </div>

        <p className="mt-12 text-xs text-slate-400">{data.cliente.telefono}</p>
      </div>
    </main>
  );
}

function Counter({ value, onChange }: { value: number; onChange: (d: number) => void }) {
  return (
    <div className="mt-1 flex items-center gap-3">
      <button
        type="button"
        onClick={() => onChange(-1)}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-200 text-2xl font-semibold text-slate-700 active:bg-slate-300"
      >
        −
      </button>
      <span className="min-w-[2ch] text-center text-2xl font-semibold tabular-nums text-slate-800">
        {value}
      </span>
      <button
        type="button"
        onClick={() => onChange(1)}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-sky-100 text-2xl font-semibold text-sky-700 active:bg-sky-200"
      >
        +
      </button>
    </div>
  );
}
