<<<<<<< HEAD
#!/bin/bash
# Script de deploy para ambiente de Produção (LogCenter)

set -e

echo "[PROD DEPLOY] Iniciando deploy no servidor Prod..."

APP_DIR="/home/admin/logcenter"
BRANCH="main"
export ENV="prod"

cd "$APP_DIR" || { echo "Diretório $APP_DIR não encontrado"; exit 1; }

git fetch origin $BRANCH
git reset --hard origin/$BRANCH
git pull origin $BRANCH

docker compose down
docker compose up -d --build

echo "[PROD DEPLOY] Deploy de produção concluído."
=======
#!/bin/bash
# Script de deploy para ambiente de Produção (LogCenter)

set -e

echo "[PROD DEPLOY] Iniciando deploy no servidor Prod..."

APP_DIR="/home/admin/logcenter"
BRANCH="main"
export ENV="prod"

cd "$APP_DIR" || { echo "Diretório $APP_DIR não encontrado"; exit 1; }

git fetch origin $BRANCH
git reset --hard origin/$BRANCH
git pull origin $BRANCH

docker compose down
docker compose up -d --build

echo "[PROD DEPLOY] Deploy de produção concluído."
>>>>>>> dev
