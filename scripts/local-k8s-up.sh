#!/usr/bin/env bash
# Complete local Kubernetes environment in one command:
#   kind cluster -> Traefik / metrics-server / Prometheus+Grafana -> build images
#   -> load images into kind -> namespace -> helm upgrade --install -> helm test
#
# Requirements: Docker, kind, kubectl, helm.   Tear down: kind delete cluster --name stockpilot
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER="stockpilot"
NAMESPACE="stockpilot"
# A unique tag per run forces Kubernetes to roll out freshly built images.
SHA="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)"
TAG="local-${SHA}-$(date +%s)"

for tool in docker kind kubectl helm; do
  command -v "$tool" >/dev/null || { echo "missing required tool: $tool" >&2; exit 1; }
done

if ! kind get clusters 2>/dev/null | grep -qx "$CLUSTER"; then
  echo "==> Creating kind cluster '$CLUSTER'"
  kind create cluster --config "$ROOT/k8s/kind-cluster.yaml" --wait 120s
fi
kubectl config use-context "kind-$CLUSTER" >/dev/null

"$ROOT/scripts/bootstrap-cluster.sh" kind

echo "==> Building images (tags $TAG and local)"
# ":local" is what values-dev.yaml references, so a manual `helm upgrade -f values-dev.yaml`
# also works; the unique tag is what this script deploys to force a rollout.
docker build -t "stockpilot-backend:$TAG" -t stockpilot-backend:local \
  --build-arg GIT_SHA="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo local)" "$ROOT/backend"
docker build -t "stockpilot-frontend:$TAG" -t stockpilot-frontend:local "$ROOT/frontend"

echo "==> Loading images into the kind nodes"
kind load docker-image "stockpilot-backend:$TAG" "stockpilot-frontend:$TAG" \
  stockpilot-backend:local stockpilot-frontend:local --name "$CLUSTER"

echo "==> Deploying with Helm"
kubectl apply -f "$ROOT/k8s/namespace.yaml"
helm upgrade --install stockpilot "$ROOT/helm/stockpilot" \
  --namespace "$NAMESPACE" \
  -f "$ROOT/helm/stockpilot/values-dev.yaml" \
  --set backend.image.tag="$TAG" \
  --set frontend.image.tag="$TAG" \
  --wait --timeout 5m

echo "==> Helm test"
helm test stockpilot -n "$NAMESPACE" --logs

kubectl get pods,svc,ingress,hpa -n "$NAMESPACE"
cat <<EOF

StockPilot is running on Kubernetes:
  App (via Ingress):  http://stockpilot.localtest.me
  Swagger:            http://stockpilot.localtest.me/docs
EOF
