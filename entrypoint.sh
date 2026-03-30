#!/bin/sh

set -e

echo "Iniciando entrypoint da aplicação..."

if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
  echo "Erro: variáveis de ambiente do banco não definidas corretamente."
  exit 1
fi

echo "Aguardando banco de dados em ${DB_HOST}:${DB_PORT}..."

while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q; do
  echo "Banco de dados indisponível, aguardando..."
  sleep 2
done

echo "Banco de dados disponível."

echo "Inicializando estrutura do banco..."
flask init-db

echo "Subindo aplicação com Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 app:app