#!/bin/sh
# init-users.sh – Crea usuarios de RabbitMQ con mínimo privilegio.
#
#   - $RABBITMQ_PUBLISHER_USER : solo puede publicar en "precios_queue"
#                                 (usado por los 3 scrapers).
#   - $RABBITMQ_CONSUMER_USER  : solo puede leer "precios_queue"
#                                 (usado por el agregador, Servidor 2).
#
# El usuario admin ($RABBITMQ_DEFAULT_USER) NUNCA se comparte con las
# aplicaciones: se usa solo aquí, una vez, para crear a los demás.
set -eu

RABBITMQ_MGMT_URL="http://rabbitmq:15672"
QUEUE_NAME="${RABBITMQ_QUEUE:-precios_queue}"

echo "Esperando a que la Management API de RabbitMQ esté disponible…"
until curl -sf -u "${RABBITMQ_DEFAULT_USER}:${RABBITMQ_DEFAULT_PASS}" \
    "${RABBITMQ_MGMT_URL}/api/overview" >/dev/null 2>&1; do
  sleep 2
done

create_user() {
  user="$1"; pass="$2"
  curl -sf -u "${RABBITMQ_DEFAULT_USER}:${RABBITMQ_DEFAULT_PASS}" -X PUT \
    "${RABBITMQ_MGMT_URL}/api/users/${user}" \
    -H "content-type: application/json" \
    -d "{\"password\":\"${pass}\",\"tags\":\"\"}"
}

set_permissions() {
  user="$1"; configure="$2"; write="$3"; read="$4"
  curl -sf -u "${RABBITMQ_DEFAULT_USER}:${RABBITMQ_DEFAULT_PASS}" -X PUT \
    "${RABBITMQ_MGMT_URL}/api/permissions/%2F/${user}" \
    -H "content-type: application/json" \
    -d "{\"configure\":\"${configure}\",\"write\":\"${write}\",\"read\":\"${read}\"}"
}

echo "Creando usuario publisher (solo write en ${QUEUE_NAME})…"
create_user "${RABBITMQ_PUBLISHER_USER}" "${RABBITMQ_PUBLISHER_PASS}"
set_permissions "${RABBITMQ_PUBLISHER_USER}" "^${QUEUE_NAME}\$" "^${QUEUE_NAME}\$" "^\$"

echo "Creando usuario consumer (solo read en ${QUEUE_NAME})…"
create_user "${RABBITMQ_CONSUMER_USER}" "${RABBITMQ_CONSUMER_PASS}"
set_permissions "${RABBITMQ_CONSUMER_USER}" "^${QUEUE_NAME}\$" "^\$" "^${QUEUE_NAME}\$"

echo "Usuarios RabbitMQ de mínimo privilegio creados correctamente."
