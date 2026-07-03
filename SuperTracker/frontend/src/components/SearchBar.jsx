// src/components/SearchBar.jsx
import { useState } from "react";

export default function SearchBar({ onSearch, categorias = [] }) {
  const [query, setQuery]         = useState("");
  const [categoria, setCategoria] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (query.trim().length >= 2) onSearch(query.trim(), categoria || null);
  }

  return (
    <form onSubmit={handleSubmit} className="search-bar">
      <input
        type="search"
        placeholder="Buscar producto… (ej: leche, detergente)"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        minLength={2}
        required
        className="search-input"
      />
      <select
        value={categoria}
        onChange={(e) => setCategoria(e.target.value)}
        className="search-select"
      >
        <option value="">Todas las categorías</option>
        {categorias.map((c) => (
          <option key={c} value={c}>
            {c.charAt(0).toUpperCase() + c.slice(1)}
          </option>
        ))}
      </select>
      <button type="submit" className="search-btn">
        Buscar
      </button>
    </form>
  );
}
