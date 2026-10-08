# StockPilot: inventory management, from laptop to monitored Kubernetes

[![CI/CD](https://github.com/milesmoralis2411/devops_project_24bcs10326/actions/workflows/ci-cd.yml/badge.svg?branch=main)](https://github.com/milesmoralis2411/devops_project_24bcs10326/actions/workflows/ci-cd.yml)
· **Evidence for every grading module: [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md)**

**StockPilot** is a small SaaS-style inventory management system for warehouses and shops.
Staff keep a catalogue of products (SKU, supplier, bin location, price, reorder level),
record every stock movement (receipts, sales, customer returns, damage write-offs and
stock-count adjustments), and get **reorder alerts** when items fall to or below their
reorder level. Every change to a quantity is written to an immutable movement log, so
the stock level can always be explained.

The application is the vehicle for the real subject: the complete DevOps path it travels.

```text
Developer → Git/GitHub → GitHub Actions (pytest · build · Trivy · GHCR) → Terraform (AWS VPC + EKS)
          → Helm → Kubernetes (Ingress · HPA · probes) → Prometheus + Grafana → troubleshooting
```

![StockPilot dashboard](docs/images/dashboard.png)

---

## Contents

1. [Architecture](#1-architecture)
2. [Tech stack](#2-tech-stack)
3. [Repository layout](#3-repository-layout)
4. [Run it locally with Docker Compose](#4-run-it-locally-with-docker-compose)
5. [The application: features and REST API](#5-the-application)
6. [Tests and code quality](#6-tests-and-code-quality)
7. [Docker images](#7-docker-images)
8. [CI/CD pipeline](#8-cicd-pipeline)
9. [Security (DevSecOps)](#9-security-devsecops)
10. [Kubernetes + Helm (local kind cluster)](#10-kubernetes--helm)
11. [Terraform: AWS VPC + EKS](#11-terraform-aws-vpc--eks)
12. [Monitoring: Prometheus + Grafana](#12-monitoring-prometheus--grafana)
13. [Autoscaling demo](#13-autoscaling-demo)
14. [Troubleshooting lab](#14-troubleshooting-lab)
15. [Design decisions](#15-design-decisions)
16. [Grading checklist and demo script](#16-grading-checklist-and-demo-script)

---

## 1. Architecture

```mermaid
flowchart LR
    dev([Developer]) -->|git push| gh[GitHub]
    gh --> ci{{GitHub Actions}}
    ci -->|pytest · ruff · npm build · terraform test · helm lint| gate[Quality gates]
    gate --> build[docker build x2]
    build --> trivy[Trivy scan<br/>fail on HIGH/CRITICAL]
    trivy --> ghcr[(GHCR<br/>image:git-sha)]
    ghcr -->|helm upgrade --install<br/>OIDC, no AWS keys| eks

    subgraph aws[AWS ap-south-1 - created by Terraform]
      subgraph vpc[VPC: 2 public + 2 private subnets, NAT]
        subgraph eks[EKS cluster]
          ing[Traefik Ingress<br/>AWS NLB] -->|/| fe[Frontend x2<br/>React + Nginx]
          ing -->|/api| be[Backend x2..6<br/>FastAPI · HPA]
          fe -.->|/api proxy| be
          be --> pg[(PostgreSQL<br/>StatefulSet + EBS)]
          prom[Prometheus] -->|ServiceMonitor<br/>/metrics| be
          graf[Grafana] --> prom
        end
      end
    end
    user([Browser]) --> ing
```

* The browser only ever calls **relative `/api/...` URLs**. Through the Ingress, `/api` goes
  straight to the backend Service; when the UI is reached directly (Docker Compose, port-forward)
  its Nginx proxies `/api` to the backend. The browser never needs an internal hostname.
* The backend runs `alembic upgrade head` on start (guarded by a PostgreSQL advisory lock,
  so several replicas starting together migrate exactly once), then starts Uvicorn.

## 2. Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 8, responsive hand-written CSS, served by unprivileged Nginx 1.30 |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.1, Pydantic v2, Uvicorn |
| Database | PostgreSQL 17, Alembic migrations |
| Tests / quality | pytest (+ coverage), ruff lint/format, Node test runner, Terraform test, Helm lint, actionlint |
| Containers | Multi-stage Dockerfiles, non-root users, Docker Compose |
| CI/CD | GitHub Actions, GHCR, Trivy, SHA-pinned actions, AWS OIDC |
| Infrastructure | Terraform (terraform-aws-modules VPC 6.x, EKS 21.x), AWS VPC + EKS 1.36 |
| Kubernetes | Helm chart, Traefik Ingress, HPA (metrics-server), PDBs, Pod Security "restricted" |
| Observability | prometheus-fastapi-instrumentator + custom business metrics, kube-prometheus-stack (Prometheus, Grafana, Alertmanager) |

## 3. Repository layout

```text
.
├── backend/                  FastAPI service
│   ├── app/                  config, db, models, schemas, routers, metrics, prestart, seed
│   ├── alembic/versions/     0001_create_products, 0002_create_stock_movements
│   ├── tests/                51 pytest tests (SQLite by default, PostgreSQL in CI)
│   ├── Dockerfile            multi-stage, non-root (uid 10001)
│   └── requirements*.txt     runtime / dev dependencies (pinned)
├── frontend/                 React + Vite dashboard
│   ├── src/                  App, components/, lib/ (api client, formatting + tests)
│   ├── nginx/                Nginx config template (envsubst BACKEND_URL)
│   └── Dockerfile            Node build stage → nginx-unprivileged runtime (uid 101)
├── docker-compose.yml        postgres + backend + frontend with healthchecks
├── .github/workflows/        ci-cd.yml - test → build → scan → push → deploy
├── terraform/                AWS VPC + EKS (+ GitHub OIDC role), tests, tfvars example
├── k8s/                      namespace (restricted PSS), kind cluster, EKS gp3 StorageClass
├── helm/stockpilot/          chart: deployments, services, ingress, HPA, PDB, StatefulSet,
│                             ServiceMonitor, PrometheusRule, Grafana dashboard, helm test
├── monitoring/               kube-prometheus-stack + Traefik values, monitoring guide
├── scripts/                  local-k8s-up, bootstrap-cluster, smoke-test, load-test, eks-teardown
├── troubleshooting/          4 broken manifests + runbook
└── docs/                     AWS guide, security notes, grading checklist, demo script, images
```

## 4. Run it locally with Docker Compose

Requirements: Docker Desktop (or Docker Engine + Compose v2).

```bash
docker compose up --build        # first build takes a few minutes
```

| URL | What |
|-----|------|
| http://localhost:3000 | StockPilot UI (demo data is seeded on first start) |
| http://localhost:8000/docs | Swagger UI - try every endpoint |
| http://localhost:8000/health · /ready · /metrics | liveness · readiness · Prometheus metrics |

```bash
scripts/smoke-test.sh http://localhost:3000     # 11 checks incl. a full CRUD cycle
docker compose exec postgres psql -U stockpilot -c "select sku, quantity, reorder_level from products;"
docker compose down          # stop
docker compose down -v       # stop and delete the database volume
```

Start order is enforced with healthchecks: PostgreSQL `pg_isready` → backend `/health`
(after migrations) → frontend.

<details>
<summary>Run the backend and frontend without Docker</summary>

```bash
# backend (needs a PostgreSQL - e.g. `docker compose up -d postgres`)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m app.prestart                                  # wait for DB, migrate, seed
uvicorn app.main:app --reload --port 8000

# frontend (proxies /api to localhost:8000)
cd frontend && npm ci && npm run dev                    # http://localhost:5173
```
</details>

## 5. The application

**UI features:** dark sidebar navigation (Dashboard · Products · Movement log) with a live
reorder badge · KPI cards (products, units on hand, inventory value, items needing reorder) ·
reorder alerts with one-click restock · recent activity feed · inventory value by category ·
searchable, filterable product table with stock-level bars · create/edit product modal ·
stock adjustment modal with live "on hand → after" preview that blocks overselling ·
delete confirmation · toasts · loading skeletons, empty states and an API-error banner ·
build info (commit SHA, environment) and delivery-pipeline indicator · responsive layout
for desktop, tablet and phone (verified at 1440, 820 and 390 px wide).

| Responsive layout | Stock adjustment |
|---|---|
| ![responsive](docs/images/responsive.png) | ![adjust](docs/images/adjust-stock.png) |

**Domain rules enforced by the API**

* SKUs are unique, normalised to upper case, `A-Z 0-9 -`, 3–40 characters.
* Quantity can only change through **stock adjustments**, so the audit trail is complete.
  `PUT /api/products/{id}` rejects a `quantity` field.
* `RESTOCK`/`RETURN` must add stock, `SALE`/`DAMAGE` must remove it, `ADJUSTMENT` can do either.
* Stock can never go negative: overselling returns **409 Conflict**. On PostgreSQL the
  adjustment uses `SELECT … FOR UPDATE`, so concurrent sales cannot oversell.
* Status is derived: `OUT_OF_STOCK` (0), `LOW_STOCK` (≤ reorder level), `IN_STOCK`.

**REST API** (full interactive docs at `/docs`)

| Method | Path | Purpose | Success |
|--------|------|---------|---------|
| GET | `/api/products` | list; filters `?search=`, `?category=`, `?status=IN_STOCK\|LOW_STOCK\|OUT_OF_STOCK` | 200 |
| GET | `/api/products/{id}` | one product | 200 / 404 |
| POST | `/api/products` | create (opening stock is logged as an `INITIAL` movement) | 201 / 409 / 422 |
| PUT | `/api/products/{id}` | update details (partial) | 200 / 404 / 409 / 422 |
| DELETE | `/api/products/{id}` | delete product and its history | 204 / 404 |
| POST | `/api/products/{id}/adjustments` | receive / sell / return / write off stock | 201 / 409 / 422 |
| GET | `/api/products/{id}/movements` | stock history of one product | 200 |
| GET | `/api/movements?limit=` | latest movements across all products | 200 |
| GET | `/api/stats` | KPIs + per-category breakdown | 200 |
| GET | `/api/categories` | distinct categories | 200 |
| GET | `/api/info` | service version, environment, **git SHA of the running build** | 200 |
| GET | `/health` | liveness: process is up (does not touch the DB) | 200 |
| GET | `/ready` | readiness: database answers `SELECT 1` | 200 / 503 |
| GET | `/metrics` | Prometheus metrics | 200 |

**Database** (`backend/alembic/versions/`): `products` (unique SKU index, check constraints
`quantity >= 0`, `unit_price >= 0`) and `stock_movements` (FK → products `ON DELETE CASCADE`,
indexed by product and time). Migration 0002 shows the schema evolving after 0001.

## 6. Tests and code quality

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v                              # 51 tests, ~6 s, isolated in-memory SQLite
pytest --cov=app                       # 99% coverage
ruff check . && ruff format --check .  # lint + formatting
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/testdb pytest   # same suite on PostgreSQL

cd ../frontend && npm test             # 5 unit tests (formatting, API error handling)
```

| Test file | Covers |
|-----------|--------|
| `test_products.py` | create/list/search/filter/get/update/delete, validation (422), duplicate SKU (409), 404s |
| `test_stock.py` | restock, sale, oversell protection, direction rules, history ordering, recent feed |
| `test_stats.py` | KPI aggregation, category breakdown, stats after adjustments |
| `test_system.py` | `/health`, `/ready` (incl. 503 when the DB is down), `/api/info`, OpenAPI, `/metrics` |
| `test_migrations.py` | Alembic upgrade → downgrade round trip, and **models match migrations** (no forgotten migration) |
| `test_seed.py` | demo seed is consistent and idempotent |

**The tests never touch a real database.** `tests/conftest.py` overrides `DATABASE_URL`
before the app is imported and recreates the schema for every test. Configuration lives
in `backend/pytest.ini` and `backend/tests/conftest.py`.

## 7. Docker images

| Image | Build | Runtime user | Size |
|-------|-------|--------------|------|
| `stockpilot-backend` | `python:3.12-slim` builder installs deps into a venv → slim runtime copies only the venv and code | `app` uid **10001** | ~320 MB |
| `stockpilot-frontend` | **multi-stage**: `node:24-alpine` runs `npm ci && npm run build` → `nginxinc/nginx-unprivileged:1.30-alpine` serves `dist/` | `nginx` uid **101**, port 8080 | ~90 MB |

```bash
docker build -t stockpilot-backend:local --build-arg GIT_SHA=$(git rev-parse HEAD) ./backend
docker build -t stockpilot-frontend:local ./frontend
docker run --rm --entrypoint id stockpilot-backend:local     # uid=10001(app)
```

Both images have a `HEALTHCHECK`, keep code root-owned and read-only, and run with
`readOnlyRootFilesystem` in Kubernetes. Node, npm and the source never reach the frontend
runtime image.

## 8. CI/CD pipeline

[`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) runs on every push and pull
request to `main` (and manually via *Run workflow*).

```text
backend-test ─┐   ruff · pytest on SQLite · pytest on a PostgreSQL service container · alembic up/down/up + check
frontend-build┼─▶ build-scan-push (backend, frontend in parallel) ─▶ deploy (main only)
iac-validate ─┘   terraform fmt/validate/test · helm lint/template
```

| Job | Fails the build when… |
|-----|----------------------|
| `backend-test` | lint error, any test fails (SQLite **or** PostgreSQL), migrations do not round-trip or drift from the models |
| `frontend-build` | `npm ci`, unit tests or `vite build` fail |
| `iac-validate` | Terraform is unformatted/invalid or its tests fail; the Helm chart does not lint/render |
| `build-scan-push` | image build fails, or **Trivy finds a fixable HIGH/CRITICAL CVE**; on `main` the images are pushed to `ghcr.io/<owner>/stockpilot-{backend,frontend}:<full git SHA>` (never `latest`) |
| `deploy` | `helm upgrade --install … --set *.image.tag=<git SHA> --wait`, rollout or `helm test` fails |

Because the image tag is the commit SHA, every running pod traces back to an exact commit.
The UI sidebar and `GET /api/info` show that SHA, which makes the
*commit → pipeline → new version live* demo visible in the browser.

The deploy job authenticates to AWS with **GitHub OIDC** (no stored AWS keys) and is
skipped until the repository variable `AWS_DEPLOY_ROLE_ARN` exists. See
[docs/AWS-EKS-GUIDE.md](docs/AWS-EKS-GUIDE.md). The Free-plan AWS account used for this
submission blocks IAM OIDC providers, so the job stays skipped here. Releases are promoted
by deploying the CI-built, SHA-tagged image with `helm upgrade` (see
[docs/DEMO-SCRIPT.md](docs/DEMO-SCRIPT.md)).

## 9. Security (DevSecOps)

Trivy scans **both images** in CI. It always prints a full report, then a second gating
step uses `--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1`, so a vulnerability with
an available fix stops the pipeline before anything is pushed.

The first CI run passed the gate, and its full report showed 13 MEDIUM/LOW findings: six
CVEs in `pip` (e.g. **CVE-2025-8869**) and one in Alpine's `zlib` (**CVE-2026-85091**).
They were remediated by removing pip from the runtime image and applying Alpine security
updates at build time. Both images now have **0 fixable vulnerabilities of any severity**.
The base image was chosen the same way: `python:3.13-slim` carries 4 fixable HIGH CVEs,
`python:3.12-slim` none.

Other controls: SHA-pinned GitHub Actions (see the March 2026 `trivy-action` tag hijack) ·
least-privilege `GITHUB_TOKEN` permissions per job · OIDC instead of AWS keys · non-root
containers, read-only root filesystems, all Linux capabilities dropped, `restricted`
Pod Security Admission · DB password generated by Helm and stored in a Secret · no
credentials in Git (`.env`, `terraform.tfvars`, state files ignored). Details and the
written explanation of a scan result: [docs/SECURITY.md](docs/SECURITY.md).

## 10. Kubernetes + Helm

**One command** builds a local 3-node cluster and deploys everything (requires Docker,
[kind](https://kind.sigs.k8s.io), kubectl, Helm; works in Git Bash on Windows):

```bash
scripts/local-k8s-up.sh
```

It creates the kind cluster (`k8s/kind-cluster.yaml`), installs Traefik, metrics-server and
kube-prometheus-stack (`scripts/bootstrap-cluster.sh kind`), builds and loads both images,
applies `k8s/namespace.yaml`, runs `helm upgrade --install … -f values-dev.yaml --wait`,
and finishes with `helm test`.

| URL | |
|-----|---|
| http://stockpilot.localtest.me | app through the Ingress (`*.localtest.me` resolves to 127.0.0.1) |
| http://stockpilot.localtest.me/docs | Swagger through the Ingress |
| http://grafana.localtest.me | Grafana (`admin` / password from the secret, see §12) |
| http://prometheus.localtest.me/targets | Prometheus targets |

```bash
kubectl get pods,svc,ingress,hpa,pdb -n stockpilot
helm list -n stockpilot
helm test stockpilot -n stockpilot --logs
helm history stockpilot -n stockpilot     # releases; roll back with: helm rollback stockpilot <rev> -n stockpilot
kind delete cluster --name stockpilot     # remove everything
```

**What the chart (`helm/stockpilot`) creates**

| Object | Details |
|--------|---------|
| Deployments `stockpilot-backend`, `stockpilot-frontend` | 2 replicas each, rolling updates with `maxUnavailable: 0`, spread across nodes, `preStop` drain delay |
| Probes | backend: startup + liveness `/health`, readiness `/ready` (DB); frontend: `/healthz` |
| Services (ClusterIP) | `stockpilot-backend:8000`, `stockpilot-frontend:80`, `stockpilot-postgres:5432` |
| Ingress (`traefik`) | `/api`, `/docs`, `/openapi.json` → backend · `/` → frontend |
| HPA | backend 2→6 pods at 60% CPU (frontend autoscaling enabled in prod) |
| PodDisruptionBudgets | keep ≥1 pod of each tier during node drains |
| StatefulSet `stockpilot-postgres` | PVC per replica (`gp3` on EKS), runs as uid 70 |
| Secret / ConfigMap | DB credentials + `DATABASE_URL` (password generated once, kept across upgrades) / app settings |
| ServiceMonitor, PrometheusRule, dashboard ConfigMap | rendered only if the Prometheus Operator CRDs exist |
| `helm test` pod | checks `/ready`, `/api/stats`, `/healthz` and the frontend→backend proxy |

Values files: `values.yaml` (defaults) · `values-dev.yaml` (kind: local images,
`stockpilot.localtest.me`) · `values-prod.yaml` (EKS: GHCR images, gp3 storage, frontend HPA).

## 11. Terraform: AWS VPC + EKS

[`terraform/`](terraform/README.md) provisions, in the region set by `aws_region` (default
`ap-south-1`): a VPC with **2 public + 2 private subnets** across two AZs, an Internet gateway
and NAT gateway, an **EKS 1.36** cluster with a **managed node group** (2× t3.medium, Amazon
Linux 2023), EKS add-ons (VPC CNI, CoreDNS, kube-proxy, Pod Identity agent, **EBS CSI driver**
with an EKS Pod Identity role), and optionally the GitHub OIDC deploy role.

The submission environment was built in **`ap-southeast-2` (Sydney)** with the same code.
The AWS Free-plan account used is restricted by AWS Organizations service control policies,
handled with three settings in the git-ignored `terraform.tfvars`:
- `aws_region = "ap-southeast-2"`: the only allowed region;
- `node_instance_types = ["m7i-flex.large"]`: only free-tier-eligible instance types are allowed;
- `github_repository = ""`: IAM OIDC providers are blocked.

The story is in [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md#m7---terraform-real-aws).

```bash
cd terraform && cp terraform.tfvars.example terraform.tfvars
terraform init && terraform validate && terraform test      # test runs offline with mocked AWS
terraform plan -out tfplan && terraform apply tfplan        # Plan: 58 to add (63 with GitHub OIDC)
```

Full walkthrough (cluster add-ons, GitHub settings, first deploy, tear-down):
**[docs/AWS-EKS-GUIDE.md](docs/AWS-EKS-GUIDE.md)**. Destroy with `scripts/eks-teardown.sh`:
it removes the Kubernetes-created load balancer and volumes first so `terraform destroy`
completes cleanly. The environment costs about US$0.30/hour.

## 12. Monitoring: Prometheus + Grafana

* The backend exposes `/metrics`: HTTP request counts and latency histograms per endpoint,
  plus business gauges (`stockpilot_products_low_stock`, `stockpilot_inventory_value`, …).
* A **ServiceMonitor** makes Prometheus scrape every backend pod; a **PrometheusRule** defines
  4 alerts (backend down, error rate > 5%, p95 > 500 ms, products out of stock).
* The Grafana dashboard **"StockPilot - Service & Inventory Overview"** is provisioned
  automatically: golden signals, per-endpoint traffic and latency, CPU per pod with HPA
  replicas, and inventory KPIs.

```bash
kubectl get secret kube-prometheus-stack-grafana -n monitoring -o jsonpath='{.data.admin-password}' | base64 -d
```

![Grafana dashboard](docs/images/grafana.png)

More in [monitoring/README.md](monitoring/README.md).

## 13. Autoscaling demo

```bash
kubectl get hpa -n stockpilot -w          # terminal 1
scripts/load-test.sh                      # terminal 2: 6 in-cluster load generators for 3 minutes
```

Measured on the local cluster while building this project (`WORKERS=8`):

```text
t+30s   cpu:   3%/60%  replicas=2
t+45s   cpu: 341%/60%  replicas=2 → 4
t+75s   cpu: 378%/60%  replicas=6      (maxReplicas)
t+210s  cpu:  41%/60%  load stopped → scales back to 2 after the 60 s stabilization window
```

## 14. Troubleshooting lab

[`troubleshooting/`](troubleshooting/README.md) contains four broken workloads and a runbook:
**ImagePullBackOff** (missing tag) · **Service without endpoints** (label mismatch) ·
**CrashLoopBackOff** (bad `DATABASE_URL`) · **Running but not Ready** (wrong probe port).
Each one has symptoms, the `get → describe → logs → events` investigation, root cause
and a verified fix.

## 15. Design decisions

| Decision | Why |
|----------|-----|
| Own domain (inventory) instead of the TaskBoard reference | capstone rules require an original application; the DevOps architecture follows the course |
| Quantity changes only via adjustments | complete audit trail; enables oversell protection with a row lock |
| Traefik as Ingress controller | the community *ingress-nginx* controller was retired in March 2026 (no more security fixes). The Ingress resource is the standard `networking.k8s.io/v1` API, so any controller works |
| PostgreSQL as a StatefulSet in the cluster | simple classroom setup; for production set `postgres.enabled=false` + `externalDatabase.url` to use **Amazon RDS** (managed backups, Multi-AZ, patching) |
| Migrations in the container start-up with an advisory lock | no separate job to orchestrate; safe with N replicas |
| `/health` does not touch the DB, `/ready` does | a DB outage should stop traffic (readiness), not restart healthy pods in a loop (liveness) |
| Image tag = full commit SHA | immutable, traceable deployments; `latest` is never deployed |
| EKS 1.36, AL2023 AMI, EBS CSI + gp3 StorageClass | standard-support pricing; AL2 AMIs are gone for ≥1.33; PVCs otherwise stay `Pending` on new EKS clusters |
| Pinned versions everywhere | reproducible builds (Python/npm lockfiles, Helm chart versions, Terraform lock file, action SHAs) |

Reference-project issues fixed along the way: Ingress pointing at a non-existent Service
name and port, Nginx proxying to a hostname that does not exist in Kubernetes, the frontend
running as root, invalid single-line HCL, an upper-case GHCR owner breaking `docker push`,
no `terraform.tfvars.example`, and missing EBS storage support on EKS.

## 16. Grading checklist and demo script

* [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md): 45 screenshots of the running system, including the real AWS VPC + EKS environment, one section per rubric module (M1–M10).
* [docs/SUBMISSION-CHECKLIST.md](docs/SUBMISSION-CHECKLIST.md): every rubric line → file/evidence → command to capture the screenshot.
* [docs/DEMO-SCRIPT.md](docs/DEMO-SCRIPT.md): a 12–15 minute live presentation flow, including the *commit → pipeline → deployment update* moment.
