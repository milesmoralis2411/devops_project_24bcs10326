# Monitoring: Prometheus + Grafana

```text
FastAPI pods ──/metrics──▶ Prometheus ──▶ Grafana dashboard "StockPilot - Service & Inventory Overview"
     ▲                         ▲   └──▶ alert rules (PrometheusRule) ──▶ Alertmanager
     │                         │
 ServiceMonitor  (helm/stockpilot/templates/servicemonitor.yaml) tells the Prometheus Operator what to scrape
```

| File | Purpose |
|------|---------|
| `kube-prometheus-stack-values.yaml` | Prometheus, Grafana, Alertmanager, kube-state-metrics, node-exporter |
| `kube-prometheus-stack-values-kind.yaml` | Local only: Grafana/Prometheus via Ingress at `*.localtest.me` |
| `traefik-values.yaml` | Ingress controller (installed by the same bootstrap script) |

Everything is installed by `scripts/bootstrap-cluster.sh kind|eks` with pinned chart versions.

## What the application exposes

`GET /metrics` on the backend (Prometheus text format):

| Metric | Type | Meaning |
|--------|------|---------|
| `http_requests_total{handler,method,status}` | counter | requests per endpoint and status class (2xx/4xx/5xx) |
| `http_request_duration_seconds_bucket{handler,method}` | histogram | latency → p50/p95 |
| `stockpilot_products` | gauge | products in the catalogue |
| `stockpilot_products_low_stock` / `_out_of_stock` | gauge | reorder pressure |
| `stockpilot_inventory_value` | gauge | Σ quantity × unit price |
| `stockpilot_stock_movements_total{reason}` | counter | receipts, sales, returns, write-offs |
| `stockpilot_stock_units_moved_total{direction}` | counter | units in / out |

The inventory gauges are read from PostgreSQL at scrape time, so every replica reports
the same truth.

## Where to look

| | Local kind cluster | EKS |
|---|---|---|
| Grafana | http://grafana.localtest.me | `kubectl port-forward svc/kube-prometheus-stack-grafana 3001:80 -n monitoring` → http://localhost:3001 |
| Prometheus targets | http://prometheus.localtest.me/targets | `kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring` |
| Grafana password | `kubectl get secret kube-prometheus-stack-grafana -n monitoring -o jsonpath='{.data.admin-password}' \| base64 -d` | same |

* **Targets page:** filter for `stockpilot` → `serviceMonitor/stockpilot/stockpilot-backend/0`, one `UP` row per backend pod.
* **Grafana:** *Dashboards → StockPilot → StockPilot - Service & Inventory Overview* (provisioned
  automatically from the ConfigMap the Helm chart ships; source: `helm/stockpilot/files/grafana-dashboard.json`).
  Rows: golden signals (rate, errors, p95 latency, pods up) · per-endpoint traffic and latency ·
  CPU per pod + HPA current/desired replicas · inventory KPIs and stock movements.
* **Alerts:** *Prometheus → Alerts*: `StockPilotBackendDown`, `StockPilotHighErrorRate`,
  `StockPilotSlowRequests`, `StockPilotProductsOutOfStock` (the last one fires with the demo data on purpose).

## Useful PromQL

```promql
sum by (handler) (rate(http_requests_total{namespace="stockpilot"}[1m]))                     # traffic
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{namespace="stockpilot"}[5m])))  # p95
sum(rate(http_requests_total{namespace="stockpilot",status=~"5.."}[5m])) / sum(rate(http_requests_total{namespace="stockpilot"}[5m]))  # error ratio
kube_horizontalpodautoscaler_status_current_replicas{namespace="stockpilot"}                # HPA replicas
```

Generate traffic for a livelier dashboard: `scripts/load-test.sh` (also triggers the HPA).
