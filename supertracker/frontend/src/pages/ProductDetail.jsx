import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import PriceComparison from "../components/PriceComparison";
import PriceHistoryChart from "../components/PriceHistoryChart";
import { api } from "../hooks/useApi";

const PERIODOS = [
  { label: "Última semana",   dias: 7  },
  { label: "Último mes",      dias: 30 },
  { label: "Últimos 3 meses", dias: 90 },
  { label: "Todo el historial", dias: null },
];

function desdeFecha(dias) {
  if (!dias) return undefined;
  const d = new Date();
  d.setDate(d.getDate() - dias);
  return d.toISOString().split("T")[0];
}

export default function ProductDetail() {
  const { id } = useParams();

  const [comparacion, setComparacion] = useState(null);
  const [historial, setHistorial]     = useState(null);
  const [supFiltro, setSupFiltro]     = useState("");
  const [periodo, setPeriodo]         = useState(PERIODOS[1]);
  const [loadingComp, setLoadingComp] = useState(true);
  const [loadingHist, setLoadingHist] = useState(true);
  const [error, setError]             = useState(null);

  useEffect(() => {
    setLoadingComp(true);
    api.compararPrecios(id)
      .then((res) => setComparacion(res.data))
      .catch(() => setError("Error cargando precios."))
      .finally(() => setLoadingComp(false));
  }, [id]);

  useEffect(() => {
    setLoadingHist(true);
    api.historialPrecios(id, supFiltro || undefined, desdeFecha(periodo.dias))
      .then((res) => setHistorial(res.data))
      .catch(() => setError("Error cargando historial."))
      .finally(() => setLoadingHist(false));
  }, [id, supFiltro, periodo]);

  // Garantizar que siempre sea array
  const listaComparacion = Array.isArray(comparacion?.comparacion)
    ? comparacion.comparacion
    : [];
  const supermercados = listaComparacion.map((c) => c.supermercado);

  return (
    <main className="page-detail">
      <Link to="/" className="back-link">← Volver a resultados</Link>

      {error && <p className="status-msg status-msg--error">{error}</p>}

      {comparacion && (
        <section className="product-header">
          <span className="product-header__categoria">
            {comparacion.producto?.categoria}
          </span>
          <h1 className="product-header__nombre">
            {comparacion.producto?.nombre}
          </h1>
          {comparacion.producto?.codigo_barra && (
            <p className="product-header__barcode">
              EAN: {comparacion.producto.codigo_barra}
            </p>
          )}
        </section>
      )}

      <section className="section-card">
        <h2 className="section-card__title">Precios actuales</h2>
        {loadingComp ? (
          <p className="status-msg">Cargando precios…</p>
        ) : (
          <PriceComparison
            comparacion={listaComparacion}
            ahorro={comparacion?.ahorro_maximo ?? 0}
          />
        )}
      </section>

      <section className="section-card">
        <h2 className="section-card__title">Historial de precios</h2>

        <div className="history-filters">
          <select
            value={supFiltro}
            onChange={(e) => setSupFiltro(e.target.value)}
            className="search-select"
          >
            <option value="">Todos los supermercados</option>
            {supermercados.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <div className="period-btns">
            {PERIODOS.map((p) => (
              <button
                key={p.label}
                className={`period-btn ${periodo.label === p.label ? "period-btn--active" : ""}`}
                onClick={() => setPeriodo(p)}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {loadingHist ? (
          <p className="status-msg">Cargando historial…</p>
        ) : (
          <PriceHistoryChart
            historialPorSupermercado={
              historial?.historial_por_supermercado ?? {}
            }
          />
        )}

        {historial && (
          <p className="history-count">
            {historial.total_registros} registros en el período seleccionado.
          </p>
        )}
      </section>
    </main>
  );
}