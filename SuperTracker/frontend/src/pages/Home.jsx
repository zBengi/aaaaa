import { useState, useEffect } from "react";
import SearchBar from "../components/SearchBar";
import ProductCard from "../components/ProductCard";
import { api } from "../hooks/useApi";

export default function Home() {
  const [categorias, setCategorias] = useState([]);
  const [resultados, setResultados] = useState([]);
  const [total, setTotal]           = useState(0);
  const [pagina, setPagina]         = useState(1);
  const [busqueda, setBusqueda]     = useState({ q: "", categoria: null });
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);

  useEffect(() => {
    api.listarCategorias()
      .then((res) => {
        const data = res.data;
        // La API devuelve un array plano de strings
        setCategorias(Array.isArray(data) ? data : []);
      })
      .catch(() => setCategorias([]));
  }, []);

  async function handleSearch(q, categoria) {
    setBusqueda({ q, categoria });
    setPagina(1);
    await cargarResultados(q, categoria, 1);
  }

  async function cargarResultados(q, categoria, pag) {
    setLoading(true);
    setError(null);
    try {
      const res = await api.buscarProductos(q, categoria, pag);
      const data = res.data;
      setResultados(Array.isArray(data.resultados) ? data.resultados : []);
      setTotal(typeof data.total === "number" ? data.total : 0);
    } catch (err) {
      setError("Error al buscar productos. Intenta nuevamente.");
      setResultados([]);
    } finally {
      setLoading(false);
    }
  }

  async function cambiarPagina(nuevaPag) {
    setPagina(nuevaPag);
    await cargarResultados(busqueda.q, busqueda.categoria, nuevaPag);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const totalPaginas = Math.ceil(total / 20);

  return (
    <main className="page-home">
      <section className="hero">
        <h1 className="hero__title">SuperPrecios</h1>
        <p className="hero__subtitle">
          Compara precios de Jumbo, Líder y Unimarc en tiempo real.
        </p>
        <SearchBar onSearch={handleSearch} categorias={categorias} />
      </section>

      {loading && <p className="status-msg">Buscando productos…</p>}
      {error   && <p className="status-msg status-msg--error">{error}</p>}

      {resultados.length > 0 && (
        <>
          <p className="results-count">
            {total} resultado{total !== 1 ? "s" : ""} para{" "}
            <strong>"{busqueda.q}"</strong>
            {busqueda.categoria ? ` en ${busqueda.categoria}` : ""}
          </p>

          <div className="product-grid">
            {resultados.map((p) => (
              <ProductCard key={p.id} producto={p} />
            ))}
          </div>

          {totalPaginas > 1 && (
            <div className="pagination">
              <button
                onClick={() => cambiarPagina(pagina - 1)}
                disabled={pagina === 1}
                className="pagination__btn"
              >
                ← Anterior
              </button>
              <span className="pagination__info">
                Página {pagina} de {totalPaginas}
              </span>
              <button
                onClick={() => cambiarPagina(pagina + 1)}
                disabled={pagina === totalPaginas}
                className="pagination__btn"
              >
                Siguiente →
              </button>
            </div>
          )}
        </>
      )}

      {!loading && busqueda.q && resultados.length === 0 && (
        <p className="empty-msg">
          No se encontraron productos para "{busqueda.q}".
        </p>
      )}
    </main>
  );
}