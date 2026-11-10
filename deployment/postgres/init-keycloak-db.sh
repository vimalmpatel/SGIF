#!/bin/sh
set -eu

case "${SGIF_DB_USER}${SGIF_DB_PASSWORD}${KEYCLOAK_DB_USER}${KEYCLOAK_DB_PASSWORD}" in
  *[!A-Za-z0-9]*)
    echo "Database usernames and passwords must be alphanumeric." >&2
    exit 1
    ;;
esac

if [ "${#SGIF_DB_PASSWORD}" -lt 32 ] || [ "${#KEYCLOAK_DB_PASSWORD}" -lt 32 ]; then
  echo "Database passwords must be at least 32 characters." >&2
  exit 1
fi

if [ "$SGIF_DB_USER" = "$KEYCLOAK_DB_USER" ] || [ "$SGIF_DB_PASSWORD" = "$KEYCLOAK_DB_PASSWORD" ]; then
  echo "SGIF and Keycloak database users and passwords must differ." >&2
  exit 1
fi

psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE ROLE ${SGIF_DB_USER} WITH LOGIN PASSWORD '${SGIF_DB_PASSWORD}';
CREATE ROLE ${KEYCLOAK_DB_USER} WITH LOGIN PASSWORD '${KEYCLOAK_DB_PASSWORD}';
CREATE DATABASE sgif OWNER ${SGIF_DB_USER};
CREATE DATABASE keycloak OWNER ${KEYCLOAK_DB_USER};
SQL