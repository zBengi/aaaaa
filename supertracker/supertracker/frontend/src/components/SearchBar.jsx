import { useState, useEffect } from "react";
import { Lens } from "./Icons.jsx";

export default function SearchBar({ categorias, categoria, onCategoria, onBuscar, valorInicial }) {
  const [texto, setTexto] = useState(valorInicial || "");

  useEffect(() => {
    setTexto(valorInicial || "");
  }, [valorInicial]);

  function submit(e) {
    e.preventDefault();
    onBuscar(texto.trim());
  }

  return (
    <div className="searchzone wrap">
      <form className="searchbar" onSubmit={submit} role="search">
        <Lens />
        <input
          type="text"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Busca un producto… p. ej. leche, arroz, detergente"
          aria-label="Buscar producto"
          autoComplete="off"
        />
        {texto && (
          <button
            type="button"
            className="clearbtn"
            aria-label="Limpiar"
            onClick={() => {
              setTexto("");
              onBuscar("");
            }}
          >
            ×
          </button>
        )}
        <button type="submit" className="gobtn">
          <span>Comparar</span>
        </button>
      </form>

      {categorias && categorias.length > 0 && (
        <div className="filters">
          <span className="flabel">Categorías</span>
          <button
            className={`pill ${!categoria ? "active" : ""}`}
            onClick={() => onCategoria("")}
          >
            Todas
          </button>
          {categorias.map((c) => (
            <button
              key={c}
              className={`pill ${categoria === c ? "active" : ""}`}
              onClick={() => onCategoria(categoria === c ? "" : c)}
            >
              {c}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
