import { clp, miles, desde } from "../api.js";
import { Store, Arrow } from "./Icons.jsx";

function ProductCard({ p, onOpen }) {
  return (
    <button className="pcard" onClick={() => onOpen(p)}>
      <div className="pcard__top">
        <span className="cat-tag">{p.categoria}</span>
      </div>

      <h3 className="pcard__name">{p.nombre}</h3>

      <div className="pricerow">
        <div className="priceblock">
          <div className="since">Desde</div>
          <div className="big">
            <span className="cur">$</span>
            {miles(p.precio_min)}
          </div>
        </div>

        {p.supermercado_mas_barato && (
          <div className="bestbadge">
            <span className="where">{p.supermercado_mas_barato}</span>
            {p.ahorro > 0 && (
              <div className="save">
                ahorra <span className="num">{clp(p.ahorro)}</span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="pcard__foot">
        <span className="stores">
          <Store /> {p.n_tiendas} {p.n_tiendas === 1 ? "tienda" : "tiendas"} ·{" "}
          {desde(p.ultima_actualizacion)}
        </span>
        <span className="arrow">
          Comparar <Arrow />
        </span>
      </div>
    </button>
  );
}

export default function ProductList({ productos, onOpen }) {
  return (
    <div className="grid">
      {productos.map((p) => (
        <ProductCard key={p.id} p={p} onOpen={onOpen} />
      ))}
    </div>
  );
}
