#!/bin/bash
# Script de deploy para ambiente de Desenvolvimento (LogCenter)

set -e  # encerra em caso de erro

echo "[DEV DEPLOY] Iniciando deploy no servidor Dev..."

# Caminho do app no servidor
APP_DIR="/home/ubuntu/logcenter"  # ajuste conforme necessário

# Branch de deploy
BRANCH="dev"

# Exporta variável de ambiente de deploy (se aplicável)
export ENV="dev"

# Navega até o diretório da aplicação
cd "$APP_DIR" || { echo "Diretório $APP_DIR não encontrado"; exit 1; }

# Atualiza código da branch dev
git fetch origin $BRANCH
git reset --hard origin/$BRANCH
git pull origin $BRANCH

# Reinicia containers Docker
docker compose down
docker compose up -d --build

echo "[DEV DEPLOY] Deploy concluído com sucesso."
