// src/components/PriceHistoryChart.jsx
// Gráfico de variaciones históricas de precio por supermercado (Recharts).

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const COLORES = ["#e31837", "#0046ad", "#f5a623", "#2ca02c", "#9467bd"];

const CLP = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  minimumFractionDigits: 0,
});

function formatFecha(iso) {
  return new Date(iso).toLocaleDateString("es-CL", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Combina historial_por_supermercado en un array flat para Recharts.
 * Cada punto: { fecha, Jumbo: 1299, Lider: 1199, … }
 */
function buildChartData(historialPorSupermercado) {
  // Recopilar todos los timestamps únicos
  const timestampsSet = new Set();
  Object.values(historialPorSupermercado).forEach((puntos) =>
    puntos.forEach((p) => timestampsSet.add(p.fecha))
  );
  const timestamps = Array.from(timestampsSet).sort();

  return timestamps.map((fecha) => {
    const punto = { fecha: formatFecha(fecha) };
    Object.entries(historialPorSupermercado).forEach(([supermercado, puntos]) => {
      const match = puntos.find((p) => p.fecha === fecha);
      if (match) punto[supermercado] = match.precio;
    });
    return punto;
  });
}

export default function PriceHistoryChart({ historialPorSupermercado }) {
  if (!historialPorSupermercado || Object.keys(historialPorSupermercado).length === 0) {
    return <p className="empty-msg">Sin datos históricos disponibles.</p>;
  }

  const supermercados = Object.keys(historialPorSupermercado);
  const data = buildChartData(historialPorSupermercado);

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 8, right: 20, left: 10, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="fecha" tick={{ fontSize: 11 }} />
        <YAxis
          tickFormatter={(v) => CLP.format(v)}
          tick={{ fontSize: 11 }}
          width={80}
        />
        <Tooltip formatter={(value) => CLP.format(value)} />
        <Legend />
        {supermercados.map((sup, i) => (
          <Line
            key={sup}
            type="monotone"
            dataKey={sup}
            stroke={COLORES[i % COLORES.length]}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
