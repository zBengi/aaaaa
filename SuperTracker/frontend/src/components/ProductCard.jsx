// src/components/ProductCard.jsx
import { useNavigate } from "react-router-dom";

const CLP = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  minimumFractionDigits: 0,
});

export default function ProductCard({ producto }) {
  const navigate = useNavigate();

  return (
    <div
      className="product-card"
      onClick={() => navigate(`/producto/${producto.id}`)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && navigate(`/producto/${producto.id}`)}
    >
      <span className="product-card__categoria">{producto.categoria}</span>
      <h3 className="product-card__nombre">{producto.nombre}</h3>
      <div className="product-card__footer">
        <span className="product-card__precio">
          desde {CLP.format(producto.precio_minimo)}
        </span>
        <span className="product-card__tiendas">
          {producto.tiendas_disponibles}{" "}
          {producto.tiendas_disponibles === 1 ? "tienda" : "tiendas"}
        </span>
      </div>
    </div>
  );
}
