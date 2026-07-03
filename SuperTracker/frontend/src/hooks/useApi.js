// src/hooks/useApi.js
// Hook centralizado para llamadas a la API REST de SuperPrecios.

import axios from "axios";
import { useState, useCallback } from "react";

const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

const client = axios.create({ baseURL: API_BASE });

/**
 * Hook genérico: retorna { data, loading, error, fetch }
 */
export function useApi() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const fetch = useCallback(async (url, params = {}) => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.get(url, { params });
      setData(res.data);
      return res.data;
    } catch (err) {
      const msg =
        err.response?.data?.detail ?? err.message ?? "Error desconocido";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, fetch };
}

// ── Funciones de API directas (para uso fuera de hooks) ───────────

export const api = {
  buscarProductos: (q, categoria, pagina = 1) =>
    client.get("/productos/buscar", { params: { q, categoria, pagina } }),

  compararPrecios: (productoId) =>
    client.get(`/productos/${productoId}/comparar`),

  historialPrecios: (productoId, supermercado, desde, hasta) =>
    client.get(`/productos/${productoId}/historial`, {
      params: { supermercado, desde, hasta },
    }),

  listarSupermercados: () => client.get("/supermercados"),

  listarCategorias: () => client.get("/categorias"),
};
