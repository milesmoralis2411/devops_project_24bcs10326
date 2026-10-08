#!/usr/bin/env bash
# Installs the cluster add-ons StockPilot relies on:
#   * Traefik             - Ingress controller that implements the Ingress resource
#   * metrics-server      - CPU/memory metrics consumed by the HorizontalPodAutoscaler
#   * kube-prometheus-stack - Prometheus Operator, Prometheus, Grafana, Alertmanager
#
# Usage: scripts/bootstrap-cluster.sh [kind|eks]     (default: kind)
set -euo pipefail

TARGET="${1:-kind}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRAEFIK_VERSION="41.7.0"
METRICS_SERVER_VERSION="3.14.0"
KUBE_PROMETHEUS_STACK_VERSION="92.1.1"

if [[ "$TARGET" != "kind" && "$TARGET" != "eks" ]]; then
  echo "usage: $0 [kind|eks]" >&2
  exit 1
fi

echo "==> Adding Helm repositories"
helm repo add traefik https://traefik.github.io/charts --force-update >/dev/null
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ --force-update >/dev/null
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update >/dev/null
helm repo update >/dev/null

echo "==> Traefik ingress controller ($TARGET)"
traefik_args=()
if [[ "$TARGET" == "kind" ]]; then
  # kind has no cloud load balancer: listen on NodePort 30080, mapped to host port 80
  # by k8s/kind-cluster.yaml.
  traefik_args+=(--set service.type=NodePort --set ports.web.nodePort=30080)
else
  # EKS: an internet-facing AWS Network Load Balancer in the public subnets.
  traefik_args+=(--set-string 'service.annotations.service\.beta\.kubernetes\.io/aws-load-balancer-type=nlb')
fi
helm upgrade --install traefik traefik/traefik --version "$TRAEFIK_VERSION" \
  --namespace traefik --create-namespace \
  -f "$ROOT/monitoring/traefik-values.yaml" ${traefik_args[@]+"${traefik_args[@]}"} \
  --wait --timeout 5m

echo "==> metrics-server (resource metrics for the HPA)"
metrics_args=()
if [[ "$TARGET" == "kind" ]]; then
  # kind kubelets use self-signed serving certificates.
  metrics_args+=(--set "args={--kubelet-insecure-tls}")
fi
helm upgrade --install metrics-server metrics-server/metrics-server --version "$METRICS_SERVER_VERSION" \
  --namespace kube-system ${metrics_args[@]+"${metrics_args[@]}"} \
  --wait --timeout 5m

echo "==> kube-prometheus-stack (Prometheus + Grafana)"
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f - >/dev/null
# Keep the existing Grafana password on re-runs; generate a random one on first install.
if GRAFANA_PASSWORD_B64="$(kubectl get secret kube-prometheus-stack-grafana -n monitoring -o jsonpath='{.data.admin-password}' 2>/dev/null)" && [[ -n "$GRAFANA_PASSWORD_B64" ]]; then
  GRAFANA_PASSWORD="$(printf '%s' "$GRAFANA_PASSWORD_B64" | base64 -d)"
else
  GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-$(od -An -N12 -tx1 /dev/urandom | tr -d ' \n')}"
fi
monitoring_values=(-f "$ROOT/monitoring/kube-prometheus-stack-values.yaml")
if [[ "$TARGET" == "kind" ]]; then
  monitoring_values+=(-f "$ROOT/monitoring/kube-prometheus-stack-values-kind.yaml")
fi
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --version "$KUBE_PROMETHEUS_STACK_VERSION" --namespace monitoring \
  "${monitoring_values[@]}" \
  --set-string grafana.adminPassword="$GRAFANA_PASSWORD" \
  --wait --timeout 10m

if [[ "$TARGET" == "kind" ]]; then
  GRAFANA_URL="http://grafana.localtest.me"
  PROMETHEUS_URL="http://prometheus.localtest.me/targets"
else
  GRAFANA_URL="kubectl port-forward svc/kube-prometheus-stack-grafana 3001:80 -n monitoring  -> http://localhost:3001"
  PROMETHEUS_URL="kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring  -> http://localhost:9090/targets"
fi
cat <<EOF

Cluster add-ons are ready.
  Grafana:    $GRAFANA_URL   (user: admin)
              password: kubectl get secret kube-prometheus-stack-grafana -n monitoring -o jsonpath='{.data.admin-password}' | base64 -d
  Prometheus: $PROMETHEUS_URL
EOF
