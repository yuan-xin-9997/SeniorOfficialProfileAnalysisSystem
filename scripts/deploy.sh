#!/usr/bin/env bash
set -euo pipefail

# Deploy SOPAS to remote Linux server (Docker Compose or Minikube)
# Usage: ./scripts/deploy.sh [compose|k8s]

REMOTE_HOST="${REMOTE_HOST:-192.168.0.111}"
REMOTE_USER="${REMOTE_USER:-yuanxin}"
REMOTE_DIR="${REMOTE_DIR:-~/sopas}"
MODE="${1:-compose}"

echo "==> Syncing project to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}"
ssh "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${REMOTE_DIR}"

rsync -avz --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude 'frontend/dist' \
  ./ "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"

if [ "$MODE" = "compose" ]; then
  echo "==> Starting services with Docker Compose"
  ssh "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_DIR} && docker compose down && docker compose up -d --build"
  echo "==> Done. Frontend: http://${REMOTE_HOST}  API: http://${REMOTE_HOST}:8000/docs"
elif [ "$MODE" = "k8s" ]; then
  echo "==> Building images inside Minikube Docker"
  ssh "${REMOTE_USER}@${REMOTE_HOST}" bash -s <<'REMOTE'
set -euo pipefail
cd ~/sopas
eval $(minikube docker-env)
docker build -t sopas-backend:latest ./backend
docker build -t sopas-frontend:latest ./frontend
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/neo4j-statefulset.yaml
kubectl apply -f k8s/redis-deployment.yaml
echo "Waiting for databases..."
sleep 30
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/celery-worker-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl rollout status deployment/backend -n sopas --timeout=180s || true
minikube service frontend -n sopas --url || echo "Frontend NodePort: http://$(minikube ip):30080"
REMOTE
  echo "==> K8S deployment triggered"
else
  echo "Unknown mode: $MODE (use compose or k8s)"
  exit 1
fi
