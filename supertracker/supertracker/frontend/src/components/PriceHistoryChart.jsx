import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { clp, miles } from "../api.js";

// Paleta estable y distinguible, coherente con la marca.
const PALETTE = ["#2e6b43", "#c14b32", "#c79100", "#3f6b8c", "#7a4ea0"];

function colorFor(store, index) {
  const known = { Jumbo: "#2e6b43", Líder: "#c14b32", Lider: "#c14b32", Unimarc: "#c79100" };
  return known[store] || PALETTE[index % PALETTE.length];
}

function fmtDia(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("es-CL", { day: "2-digit", month: "short" });
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="tooltip">
      <div className="tt-date">{label}</div>
      {payload
        .slice()
        .sort((a, b) => a.value - b.value)
        .map((p) => (
          <div className="tt-row" key={p.dataKey}>
            <span style={{ color: p.color, fontWeight: 700 }}>{p.dataKey}</span>
            <span className="num">{clp(p.value)}</span>
          </div>
        ))}
    </div>
  );
}

export default function PriceHistoryChart({ hist }) {
  const puntos = hist?.puntos || [];

  // Pivotar: una fila por fecha (día), una columna por supermercado.
  const stores = [...new Set(puntos.map((p) => p.supermercado_nombre))];
  const porFecha = new Map();
  for (const p of puntos) {
    const key = fmtDia(p.registrado_en);
    if (!porFecha.has(key)) porFecha.set(key, { fecha: key, _t: new Date(p.registrado_en).getTime() });
    const efectivo =
      p.precio_oferta !== null && p.precio_oferta < p.precio ? p.precio_oferta : p.precio;
    porFecha.get(key)[p.supermercado_nombre] = efectivo;
  }
  const data = [...porFecha.values()].sort((a, b) => a._t - b._t);

  if (data.length < 2) {
    return (
      <div className="chartcard">
        <p className="state" style={{ padding: "2rem 1rem" }}>
          <span className="emoji">📈</span>
          <br />
          Todavía no hay suficiente historial para graficar. Vuelve tras algunas
          actualizaciones de precios.
        </p>
      </div>
    );
  }

  return (
    <div className="chartcard">
      <div className="chart-legend">
        {stores.map((s, i) => (
          <span className="lg" key={s}>
            <span className="sw" style={{ background: colorFor(s, i) }} />
            {s}
          </span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 6, right: 14, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#ddd4c0" strokeDasharray="3 4" vertical={false} />
          <XAxis
            dataKey="fecha"
            tick={{ fontSize: 12, fill: "#8a9388", fontFamily: "Archivo Narrow" }}
            axisLine={{ stroke: "#c9bfa6" }}
            tickLine={false}
          />
          <YAxis
            width={54}
            tick={{ fontSize: 11, fill: "#8a9388", fontFamily: "Spline Sans Mono" }}
            tickFormatter={(v) => `$${miles(v)}`}
            axisLine={false}
            tickLine={false}
            domain={["auto", "auto"]}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: "#18201a", strokeWidth: 1 }} />
          {stores.map((s, i) => (
            <Line
              key={s}
              type="monotone"
              dataKey={s}
              stroke={colorFor(s, i)}
              strokeWidth={2.6}
              dot={{ r: 3, strokeWidth: 0, fill: colorFor(s, i) }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
