import { useState, useEffect, useCallback, useRef } from "react";
import { api, miles, desde } from "./api.js";
import SearchBar from "./components/SearchBar.jsx";
import ProductList from "./components/ProductList.jsx";
import ProductDetail from "./components/ProductDetail.jsx";
import { Tag } from "./components/Icons.jsx";

const PAGE_SIZE = 12;

function BrandMark() {
  return (
    <svg className="brand__mark" viewBox="0 0 64 64" aria-hidden="true">
      <rect width="64" height="64" rx="14" fill="#e9c46a" />
      <path
        d="M30 14 L50 14 L50 34 L31 53 L11 33 Z"
        fill="#1f3d2b"
        stroke="#0e1f15"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <circle cx="42" cy="22" r="3.4" fill="#e9c46a" />
      <path d="M22 30 l9 9 m-9 0 l9 -9" stroke="#e9c46a" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export default function App() {
  const [salud, setSalud] = useState("checking"); // checking | ok | down
  const [stats, setStats] = useState(null);
  const [categorias, setCategorias] = useState([]);

  const [q, setQ] = useState("");
  const [categoria, setCategoria] = useState("");
  const [page, setPage] = useState(1);

  const [data, setData] = useState({ items: [], total: 0 });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const [seleccionado, setSeleccionado] = useState(null);
  const primeraCarga = useRef(true);

  // Estado inicial: salud, stats y categorías.
  useEffect(() => {
    api
      .health()
      .then(() => setSalud("ok"))
      .catch(() => setSalud("down"));
    api.stats().then(setStats).catch(() => {});
    api.categorias().then(setCategorias).catch(() => {});
  }, []);

  // Búsqueda (reacciona a q, categoría y página).
  const buscar = useCallback(() => {
    setCargando(true);
    setError(null);
    api
      .buscarProductos({ q, categoria, page, pageSize: PAGE_SIZE })
      .then((d) => setData(d))
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, [q, categoria, page]);

  useEffect(() => {
    buscar();
  }, [buscar]);

  // Volver a la página 1 cuando cambian los filtros.
  useEffect(() => {
    if (primeraCarga.current) {
      primeraCarga.current = false;
      return;
    }
    setPage(1);
  }, [q, categoria]);

  const totalPaginas = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="app">
      {/* ---------- Encabezado ---------- */}
      <header className="masthead">
        <div className="masthead__inner wrap">
          <div className="topbar">
            <div className="brand">
              <BrandMark />
              <span className="brand__name">
                Super<b>Tracker</b>
              </span>
            </div>
            <span className={`health ${salud}`}>
              <span className="dot" />
              {salud === "ok"
                ? "API en línea"
                : salud === "down"
                ? "API no disponible"
                : "Conectando…"}
            </span>
          </div>

          <div className="hero">
            <div>
              <p className="kicker" style={{ color: "rgba(244,239,227,.6)" }}>
                Comparador de precios · Chile
              </p>
              <h1 className="hero__title">
                El precio justo, <em>sin dar vueltas</em> por el súper.
              </h1>
              <p className="hero__sub">
                Recolectamos precios de Jumbo, Líder y Unimarc de forma automática
                y los reunimos en un solo lugar. Busca un producto y descubre dónde
                conviene comprarlo hoy.
              </p>
              <div className="hero__stores">
                <span className="chip-store">Jumbo</span>
                <span className="chip-store">Líder</span>
                <span className="chip-store">Unimarc</span>
              </div>
            </div>

            <div className="hero__stats">
              <h3>El sistema ahora mismo</h3>
              <div className="statgrid">
                <div className="stat">
                  <div className="v green">
                    {stats ? miles(stats.total_productos) : "—"}
                  </div>
                  <div className="l">productos monitoreados</div>
                </div>
                <div className="stat">
                  <div className="v">
                    {stats ? miles(stats.total_supermercados) : "—"}
                  </div>
                  <div className="l">supermercados</div>
                </div>
                <div className="stat">
                  <div className="v">
                    {stats ? miles(stats.total_registros_precio) : "—"}
                  </div>
                  <div className="l">registros de precio</div>
                </div>
                <div className="stat">
                  <div className="v" style={{ fontSize: "1.15rem", paddingTop: ".4rem" }}>
                    {stats ? desde(stats.ultima_actualizacion) : "—"}
                  </div>
                  <div className="l">última actualización</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* ---------- Buscador ---------- */}
      <SearchBar
        categorias={categorias}
        categoria={categoria}
        onCategoria={setCategoria}
        onBuscar={setQ}
        valorInicial={q}
      />

      {/* ---------- Resultados ---------- */}
      <main className="results">
        <div className="wrap">
          <div className="results__head">
            <h2>
              {q
                ? `Resultados para “${q}”`
                : categoria
                ? `Categoría: ${categoria}`
                : "Todos los productos"}
            </h2>
            {!cargando && !error && (
              <span className="results__count">
                {data.total} {data.total === 1 ? "producto" : "productos"}
              </span>
            )}
          </div>

          {cargando ? (
            <div className="grid">
              {Array.from({ length: 6 }).map((_, i) => (
                <div className="skel" key={i} />
              ))}
            </div>
          ) : error ? (
            <div className="state">
              <span className="emoji">⚠️</span>
              <h3>No pudimos cargar los productos</h3>
              <p>{error}. Verifica que la API esté en línea e inténtalo de nuevo.</p>
            </div>
          ) : data.items.length === 0 ? (
            <div className="state">
              <span className="emoji">
                <Tag size={40} />
              </span>
              <h3>Sin coincidencias</h3>
              <p>
                No encontramos productos para esa búsqueda. Prueba con otro término
                o quita los filtros.
              </p>
            </div>
          ) : (
            <>
              <ProductList productos={data.items} onOpen={setSeleccionado} />

              {totalPaginas > 1 && (
                <div className="pager">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    ← Anterior
                  </button>
                  <span className="pginfo">
                    Página {page} de {totalPaginas}
                  </span>
                  <button
                    disabled={page >= totalPaginas}
                    onClick={() => setPage((p) => Math.min(totalPaginas, p + 1))}
                  >
                    Siguiente →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* ---------- Pie ---------- */}
      <footer className="foot">
        <div className="foot__inner wrap">
          <div>
            <b>SuperTracker</b> — Sistema distribuido de comparación de precios.
          </div>
          <div className="stack">
            <span>Pub/Sub · RabbitMQ</span>
            <span>FastAPI</span>
            <span>PostgreSQL 16</span>
            <span>React 18</span>
            <span>Docker</span>
          </div>
        </div>
      </footer>

      {/* ---------- Modal de detalle ---------- */}
      {seleccionado && (
        <ProductDetail producto={seleccionado} onClose={() => setSeleccionado(null)} />
      )}
    </div>
  );
}
