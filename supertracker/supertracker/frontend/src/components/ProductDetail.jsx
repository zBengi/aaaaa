import { useState, useEffect, useCallback } from "react";
import { api } from "../api.js";
import ComparisonTable from "./ComparisonTable.jsx";
import PriceHistoryChart from "./PriceHistoryChart.jsx";

const RANGOS = [
  { dias: 7, label: "7 días" },
  { dias: 30, label: "30 días" },
  { dias: 90, label: "90 días" },
];

export default function ProductDetail({ producto, onClose }) {
  const [comp, setComp] = useState(null);
  const [hist, setHist] = useState(null);
  const [dias, setDias] = useState(30);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  // Cargar comparativa una vez.
  useEffect(() => {
    let vivo = true;
    setCargando(true);
    setError(null);
    api
      .comparativa(producto.id)
      .then((d) => vivo && setComp(d))
      .catch((e) => vivo && setError(e.message))
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
  }, [producto.id]);

  // Cargar historial cada vez que cambia el rango.
  const cargarHist = useCallback(() => {
    let vivo = true;
    api
      .historial(producto.id, dias)
      .then((d) => vivo && setHist(d))
      .catch(() => vivo && setHist(null));
    return () => {
      vivo = false;
    };
  }, [producto.id, dias]);

  useEffect(() => cargarHist(), [cargarHist]);

  // Cerrar con tecla Escape y bloquear scroll del fondo.
  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  const detalle = comp?.producto || producto;

  return (
    <div className="overlay" onMouseDown={onClose}>
      <div className="sheet" onMouseDown={(e) => e.stopPropagation()}>
        <div className="sheet__head">
          <div>
            <span className="cat-tag">{detalle.categoria}</span>
            <h2>{detalle.nombre}</h2>
            {detalle.descripcion && <div className="desc">{detalle.descripcion}</div>}
          </div>
          <button className="closebtn" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </div>

        <div className="sheet__body">
          {cargando && <p className="state">Cargando comparación…</p>}
          {error && (
            <p className="state">
              <span className="emoji">⚠️</span>
              <br />
              No se pudo cargar la comparación: {error}
            </p>
          )}

          {comp && !cargando && (
            <>
              <p className="section-label">Precios por tienda (último registrado)</p>
              <ComparisonTable comp={comp} />

              <div className="chartwrap">
                <div
                  className="section-label"
                  style={{ justifyContent: "space-between" }}
                >
                  <span>Evolución de precios</span>
                  <span className="range-tabs">
                    {RANGOS.map((r) => (
                      <button
                        key={r.dias}
                        className={dias === r.dias ? "active" : ""}
                        onClick={() => setDias(r.dias)}
                      >
                        {r.label}
                      </button>
                    ))}
                  </span>
                </div>
                <PriceHistoryChart hist={hist} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
