import { clp, miles } from "../api.js";
import { Ext } from "./Icons.jsx";

export default function ComparisonTable({ comp }) {
  const precios = comp.precios || [];
  if (precios.length === 0) {
    return <p className="state">Aún no hay precios registrados para este producto.</p>;
  }

  const efectivos = precios.map((x) => x.precio_efectivo);
  const min = Math.min(...efectivos);
  const max = Math.max(...efectivos);
  const ahorro = max - min;

  // ordenar de más barato a más caro
  const ordenados = [...precios].sort((a, b) => a.precio_efectivo - b.precio_efectivo);

  return (
    <>
      <div className="ctable">
        {ordenados.map((row) => {
          const esBest = row.precio_efectivo === min && precios.length > 1;
          const esWorst = row.precio_efectivo === max && precios.length > 1 && max !== min;
          const tieneOferta =
            row.precio_oferta !== null && row.precio_oferta < row.precio;
          return (
            <div
              key={row.supermercado_id}
              className={`crow ${esBest ? "best" : ""} ${esWorst ? "worst" : ""}`}
            >
              <div className="crow__store">
                <span className="nm">{row.supermercado_nombre}</span>
                {esBest && <span className="tag win">★ Más barato</span>}
                {esWorst && <span className="tag high">Más caro</span>}
              </div>

              <div className="crow__price">
                <div className="eff">
                  {clp(row.precio_efectivo)}
                  {tieneOferta && <span className="offer-flag">Oferta</span>}
                </div>
                {tieneOferta && (
                  <div className="strike">antes {clp(row.precio)}</div>
                )}
              </div>

              <div className="crow__link">
                <a href={row.url_producto} target="_blank" rel="noopener noreferrer">
                  Ver <Ext />
                </a>
              </div>
            </div>
          );
        })}
      </div>

      {ahorro > 0 && (
        <div className="savings-note">
          🟢 Comprando en <strong>&nbsp;{ordenados[0].supermercado_nombre}&nbsp;</strong> ahorras
          hasta <b>&nbsp;{clp(ahorro)}&nbsp;</b> frente a la opción más cara.
        </div>
      )}
    </>
  );
}
