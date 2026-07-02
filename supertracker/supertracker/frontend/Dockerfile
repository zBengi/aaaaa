# ---------- Etapa 1: build con Node ----------
FROM node:20-alpine AS build
WORKDIR /app

# Instala dependencias usando la caché de capas.
COPY package.json package-lock.json* ./
RUN npm install

# Copia el código y genera el bundle de producción.
COPY . .
RUN npm run build

# ---------- Etapa 2: servir estáticos con Nginx ----------
FROM nginx:1.27-alpine AS runtime

# Configuración propia (SPA + proxy /api -> api:8000).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Artefactos compilados.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -q --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
