// Cliente HTTP de la API REST de SuperTracker.
// La base es "/api": en producción Nginx la enruta al contenedor `api`;
// en desarrollo Vite la redirige (proxy) al servicio API local.
const BASE = import.meta.env.VITE_API_BASE || "/api";

async function http(path) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body && body.detail) detail = body.detail;
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  health: () => http("/health"),
  stats: () => http("/stats"),
  supermercados: () => http("/supermercados"),
  categorias: () => http("/categorias"),

  buscarProductos: ({ q = "", categoria = "", page = 1, pageSize = 12 } = {}) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (categoria) params.set("categoria", categoria);
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    return http(`/productos?${params.toString()}`);
  },

  comparativa: (id) => http(`/productos/${id}/comparativa`),
  historial: (id, dias = 30) => http(`/productos/${id}/historial?dias=${dias}`),
};

// Formatea un número como pesos chilenos: $1.190
export function clp(n) {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(n);
}

// Solo el número con separador de miles (sin símbolo), p.ej. 1.190
export function miles(n) {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(n);
}

// Fecha relativa amable: "hace 2 h", "hace 3 días"
export function desde(iso) {
  if (!iso) return "sin datos";
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "recién";
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)} h`;
  const dias = Math.floor(diff / 86400);
  return `hace ${dias} ${dias === 1 ? "día" : "días"}`;
}
