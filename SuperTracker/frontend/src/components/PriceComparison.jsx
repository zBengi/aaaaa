// src/components/PriceComparison.jsx

const CLP = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  minimumFractionDigits: 0,
});

const SUPERMERCADO_COLORES = {
  Jumbo:   "#e31837",
  Lider:   "#0046ad",
  Unimarc: "#f5a623",
};

export default function PriceComparison({ comparacion, ahorro }) {
  if (!comparacion || comparacion.length === 0) {
    return <p className="empty-msg">Sin precios disponibles.</p>;
  }

  return (
    <div className="price-comparison">
      {comparacion.map((item) => (
        <div
          key={item.supermercado}
          className={`price-row ${item.es_mas_barato ? "price-row--cheaper" : ""}`}
        >
          <span
            className="price-row__supermercado"
            style={{ borderLeftColor: SUPERMERCADO_COLORES[item.supermercado] ?? "#666" }}
          >
            {item.supermercado}
            {item.es_mas_barato && (
              <span className="badge-barato">más barato</span>
            )}
          </span>
          <span className="price-row__precio">{CLP.format(item.precio)}</span>
          <span className="price-row__fecha">
            {new Date(item.registrado_en).toLocaleString("es-CL", {
              dateStyle: "short",
              timeStyle: "short",
            })}
          </span>
        </div>
      ))}

      {ahorro > 0 && (
        <p className="saving-hint">
          💰 Puedes ahorrar hasta <strong>{CLP.format(ahorro)}</strong> eligiendo la tienda más barata.
        </p>
      )}
    </div>
  );
}
