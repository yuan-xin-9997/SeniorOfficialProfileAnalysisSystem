param(
    [ValidateSet("compose", "k8s")]
    [string]$Mode = "compose"
)

$RemoteHost = if ($env:REMOTE_HOST) { $env:REMOTE_HOST } else { "192.168.0.111" }
$RemoteUser = if ($env:REMOTE_USER) { $env:REMOTE_USER } else { "yuanxin" }
$RemoteDir = "~/sopas"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "==> Packaging project..."
$archive = Join-Path $env:TEMP "sopas-deploy.tar.gz"
if (Test-Path $archive) { Remove-Item $archive -Force }

Push-Location $ProjectRoot
tar -czf $archive --exclude=.git --exclude=node_modules --exclude=.venv --exclude=__pycache__ --exclude=frontend/dist .
Pop-Location

Write-Host "==> Uploading to ${RemoteUser}@${RemoteHost}..."
ssh "${RemoteUser}@${RemoteHost}" "mkdir -p $RemoteDir"
scp $archive "${RemoteUser}@${RemoteHost}:${RemoteDir}/sopas-deploy.tar.gz"
ssh "${RemoteUser}@${RemoteHost}" "cd $RemoteDir && tar -xzf sopas-deploy.tar.gz && rm sopas-deploy.tar.gz"

if ($Mode -eq "compose") {
    Write-Host "==> Starting Docker Compose..."
    ssh "${RemoteUser}@${RemoteHost}" "cd $RemoteDir && docker compose down 2>/dev/null; docker compose up -d --build"
    Write-Host "==> Done. Frontend: http://${RemoteHost}  API: http://${RemoteHost}:8000/docs"
} else {
    Write-Host "==> Deploying to Minikube..."
    ssh "${RemoteUser}@${RemoteHost}" @"
cd ~/sopas && eval \$(minikube docker-env) && \
docker build -t sopas-backend:latest ./backend && \
docker build -t sopas-frontend:latest ./frontend && \
kubectl apply -f k8s/ && sleep 30 && \
kubectl rollout status deployment/backend -n sopas --timeout=180s || true && \
minikube service frontend -n sopas --url
"@
}

Remove-Item $archive -Force -ErrorAction SilentlyContinue
