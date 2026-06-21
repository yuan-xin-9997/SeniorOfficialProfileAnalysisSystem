#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRET_DIR="${HOME}/SeniorOfficialProfileAnalysisSystem/secrets"
ADMIN_PASSWORD_FILE="${SECRET_DIR}/admin-password.txt"

cd "${ROOT_DIR}"

kubectl apply -f deploy/k8s/00-namespace.yaml
kubectl apply -f deploy/k8s/01-configmap.yaml

mkdir -p "${SECRET_DIR}"
chmod 700 "${SECRET_DIR}"

if [[ -f "${ADMIN_PASSWORD_FILE}" ]]; then
  ADMIN_PASSWORD="$(cat "${ADMIN_PASSWORD_FILE}")"
else
  ADMIN_PASSWORD="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 16)"
  printf "%s" "${ADMIN_PASSWORD}" > "${ADMIN_PASSWORD_FILE}"
  chmod 600 "${ADMIN_PASSWORD_FILE}"
fi

POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(openssl rand -hex 16)}"
JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}"

kubectl -n sopa create secret generic sopa-secret \
  --from-literal=POSTGRES_DB=sopa \
  --from-literal=POSTGRES_USER=sopa \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  --from-literal=DATABASE_URL="postgresql+psycopg://sopa:${POSTGRES_PASSWORD}@postgres:5432/sopa" \
  --from-literal=REDIS_URL="redis://redis:6379/0" \
  --from-literal=JWT_SECRET="${JWT_SECRET}" \
  --from-literal=INITIAL_ADMIN_USERNAME=admin \
  --from-literal=INITIAL_ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  --from-literal=LLM_API_KEY="" \
  --dry-run=client \
  -o yaml | kubectl apply -f -

kubectl apply -f deploy/k8s/03-postgres.yaml
kubectl apply -f deploy/k8s/04-redis.yaml
kubectl apply -f deploy/k8s/05-backend.yaml
kubectl apply -f deploy/k8s/06-worker.yaml
kubectl apply -f deploy/k8s/07-scheduler.yaml
kubectl apply -f deploy/k8s/08-frontend.yaml

kubectl -n sopa rollout status statefulset/postgres --timeout=180s
kubectl -n sopa rollout status deployment/redis --timeout=180s
kubectl -n sopa rollout status deployment/backend-api --timeout=300s
kubectl -n sopa rollout status deployment/frontend --timeout=180s

echo "Admin password file: ${ADMIN_PASSWORD_FILE}"
kubectl -n sopa get pods,svc

