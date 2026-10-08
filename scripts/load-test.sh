#!/usr/bin/env bash
# Generates sustained API traffic to push backend CPU above the HPA target so the
# autoscaler adds pods. Watch it in another terminal:
#   kubectl get hpa -n stockpilot -w
#
# Usage:
#   scripts/load-test.sh                    # in-cluster load generator pods (default)
#   MODE=local URL=http://stockpilot.localtest.me scripts/load-test.sh   # from this machine
#   DURATION=300 WORKERS=8 scripts/load-test.sh
#   scripts/load-test.sh stop               # remove the in-cluster load generator
set -euo pipefail

NAMESPACE="${NAMESPACE:-stockpilot}"
DURATION="${DURATION:-180}"
WORKERS="${WORKERS:-6}"
MODE="${MODE:-cluster}"
BACKEND="${BACKEND:-http://stockpilot-backend:8000}"

if [[ "${1:-}" == "stop" ]]; then
  kubectl delete deployment stockpilot-load -n "$NAMESPACE" --ignore-not-found
  exit 0
fi

if [[ "$MODE" == "cluster" ]]; then
  echo "==> Starting $WORKERS in-cluster load generators against $BACKEND for ${DURATION}s"
  kubectl apply -n "$NAMESPACE" -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stockpilot-load
  labels: {app: stockpilot-load}
spec:
  replicas: $WORKERS
  selector: {matchLabels: {app: stockpilot-load}}
  template:
    metadata: {labels: {app: stockpilot-load}}
    spec:
      securityContext: {runAsNonRoot: true, runAsUser: 65534, seccompProfile: {type: RuntimeDefault}}
      containers:
        - name: load
          image: busybox:1.37
          command: ["sh", "-c", "while true; do wget -qO- $BACKEND/api/stats >/dev/null; wget -qO- $BACKEND/api/products >/dev/null; wget -qO- $BACKEND/api/movements?limit=100 >/dev/null; done"]
          resources: {requests: {cpu: 20m, memory: 16Mi}, limits: {cpu: 200m, memory: 32Mi}}
          securityContext: {allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, capabilities: {drop: ["ALL"]}}
EOF
  echo "Load running. Watch:  kubectl get hpa -n $NAMESPACE -w"
  sleep "$DURATION"
  kubectl delete deployment stockpilot-load -n "$NAMESPACE" --ignore-not-found
  echo "==> Load stopped; the HPA scales back down after its stabilization window."
else
  URL="${URL:-http://stockpilot.localtest.me}"
  echo "==> Sending traffic to $URL from this machine with $WORKERS workers for ${DURATION}s"
  end=$((SECONDS + DURATION))
  worker() {
    while (( SECONDS < end )); do
      curl -s -o /dev/null "$URL/api/stats" || true
      curl -s -o /dev/null "$URL/api/products" || true
    done
  }
  for _ in $(seq 1 "$WORKERS"); do worker & done
  wait
  echo "==> Load test completed"
fi
