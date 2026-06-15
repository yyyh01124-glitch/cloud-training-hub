#!/bin/bash
# Cloud Training Hub - ECS Deployment Script
set -euo pipefail

ECS_HOST="8.146.230.215"
ECS_USER="root"
SSH_KEY="$HOME/.ssh/id_ed25519"
REMOTE_DIR="/opt/cloud-training-hub"

echo "=== Cloud Training Hub Deployment ==="
echo "Target: ${ECS_USER}@${ECS_HOST}:${REMOTE_DIR}"
echo ""

# 1. Upload source files
echo "[1/4] Uploading source files..."
rsync -avz --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.idea' \
  --exclude '.env' \
  --exclude 'uploads/*' \
  --exclude 'logs/*' \
  --exclude 'migrations/versions/*' \
  -e "ssh -i ${SSH_KEY}" \
  ./ ${ECS_USER}@${ECS_HOST}:${REMOTE_DIR}/

# 2. Rebuild and restart containers
echo ""
echo "[2/4] Rebuilding Docker images..."
ssh -i ${SSH_KEY} ${ECS_USER}@${ECS_HOST} "cd ${REMOTE_DIR} && docker compose build web --no-cache"

echo ""
echo "[3/4] Restarting containers..."
ssh -i ${SSH_KEY} ${ECS_USER}@${ECS_HOST} "cd ${REMOTE_DIR} && docker compose up -d"

# 3. Verify deployment
echo ""
echo "[4/4] Verifying deployment..."
sleep 5
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://${ECS_HOST}/auth/login)
if [ "$HTTP_CODE" = "200" ]; then
    echo "  Deployment successful! http://${ECS_HOST}"
else
    echo "  WARNING: Login page returned HTTP ${HTTP_CODE}"
fi

echo ""
echo "=== Deployment complete ==="
echo "  URL: http://${ECS_HOST}"
echo "  Admin: admin / admin123"
echo ""
echo "Useful commands:"
echo "  ssh -i ${SSH_KEY} ${ECS_USER}@${ECS_HOST} docker compose -f ${REMOTE_DIR}/docker-compose.yml logs -f"
echo "  ssh -i ${SSH_KEY} ${ECS_USER}@${ECS_HOST} docker compose -f ${REMOTE_DIR}/docker-compose.yml restart"
echo "  ssh -i ${SSH_KEY} ${ECS_USER}@${ECS_HOST} docker compose -f ${REMOTE_DIR}/docker-compose.yml down"
