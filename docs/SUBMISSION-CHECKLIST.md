# Grading evidence map (GRADING.md)

Each rubric criterion with how the project meets it and where the proof is. All screenshots
are indexed in [SCREENSHOTS.md](SCREENSHOTS.md).

| | |
|---|---|
| Repository | https://github.com/milesmoralis2411/devops_project_24bcs10326 (public) |
| Pipeline run | [run 37837734675](https://github.com/milesmoralis2411/devops_project_24bcs10326/actions/runs/37837734675) (green) |
| Images | `ghcr.io/milesmoralis2411/stockpilot-backend` and `stockpilot-frontend`, tagged with the commit SHA |

---

## M1: Application (10)

| Criterion | How it is met |
|-----------|---------------|
| FastAPI starts, `/health` responds (2) | `GET /health` → `{"status":"UP"}`, [m1-api-health-and-crud.png](screenshots/m1-api-health-and-crud.png) |
| ≥ 4 REST endpoints GET/POST/PUT/DELETE (3) | 11 `/api` endpoints plus `/health`, `/ready`, `/metrics`; README Section 5, [m1-swagger-docs.png](screenshots/m1-swagger-docs.png) |
| PostgreSQL table managed by Alembic (2) | `backend/alembic/versions/0001_create_products.py`, `0002_create_stock_movements.py`; [m1-postgres-alembic-tables.png](screenshots/m1-postgres-alembic-tables.png) |
| Frontend renders and calls the API (2) | React UI calls `/api/products`, `/api/stats`, `/api/movements`, …; [m1-app-docker-compose.png](screenshots/m1-app-docker-compose.png) |
| Responsive, usable UI (1) | verified at 1440 / 820 / 390 px, [responsive.png](images/responsive.png) |

## M2: Testing (10)

| Criterion | How it is met |
|-----------|---------------|
| `pytest` runs without errors (3) | 51 passed, 99% coverage, [m2-pytest-v.png](screenshots/m2-pytest-v.png) |
| ≥ 5 tests covering ≥ 3 endpoints (4) | 51 tests covering all 13 routes (`backend/tests/`) |
| Test DB / mock, not production (2) | `tests/conftest.py` forces an in-memory SQLite database; CI additionally uses a throw-away PostgreSQL container |
| `pytest.ini` / `conftest.py` (1) | `backend/pytest.ini`, `backend/tests/conftest.py` |

## M3: Git and GitHub (5)

| Criterion | How it is met |
|-----------|---------------|
| Public GitHub repository (2) | [m3-github-repository.png](screenshots/m3-github-repository.png) |
| Meaningful commit messages (2) | conventional-commit history (`feat(helm): …`, `test(backend): …`, `ci: …`), [m3-github-commits.png](screenshots/m3-github-commits.png), [m3-git-log.png](screenshots/m3-git-log.png) |
| `.gitignore` excludes `.env`, `__pycache__`, `node_modules`, `.venv` (1) | root [`.gitignore`](../.gitignore) |

## M4: Docker (10)

| Criterion | How it is met |
|-----------|---------------|
| `backend/Dockerfile` builds (2) | multi-stage build, [m4-docker-compose-up-build.png](screenshots/m4-docker-compose-up-build.png) |
| Frontend multi-stage Node → Nginx (3) | `node:24-alpine` build → `nginxinc/nginx-unprivileged:1.30-alpine` runtime |
| Images run as non-root (2) | backend uid 10001, frontend uid 101, [m4-non-root-images.png](screenshots/m4-non-root-images.png) |
| `docker compose up --build` starts all 3 services (3) | postgres, backend and frontend all `healthy`, [m4-docker-compose-up-build.png](screenshots/m4-docker-compose-up-build.png) |

## M5: CI/CD (15)

| Criterion | How it is met |
|-----------|---------------|
| Workflow file (1) | [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml) |
| Triggers on push to `main` (1) | `on: push: branches: [main]` (plus pull requests and manual runs), [m5-github-actions-runs.png](screenshots/m5-github-actions-runs.png) |
| pytest job fails the build (3) | `backend-test`; the build jobs `needs:` it, [m5-ci-pytest-step.png](screenshots/m5-ci-pytest-step.png) |
| Frontend built in pipeline (2) | `frontend-build`: `npm ci`, `npm test`, `npm run build` |
| Images built for both (3) | `build-scan-push` matrix: backend + frontend, [m5-github-actions-run-green.png](screenshots/m5-github-actions-run-green.png) |
| Pushed to GHCR (3) | [m5-ci-push-backend-sha-tag.png](screenshots/m5-ci-push-backend-sha-tag.png), [m5-ghcr-backend-sha-tags.png](screenshots/m5-ghcr-backend-sha-tags.png) |
| Tag = commit SHA, not latest (2) | `:${GITHUB_SHA}`; `latest` is never pushed, [m5-ghcr-frontend-sha-tags.png](screenshots/m5-ghcr-frontend-sha-tags.png) |

## M6: Trivy (5)

| Criterion | How it is met |
|-----------|---------------|
| Trivy scans both images in CI (3) | a report step and a gate step per image, [m6-ci-trivy-gate-backend.png](screenshots/m6-ci-trivy-gate-backend.png), [m6-ci-trivy-gate-frontend.png](screenshots/m6-ci-trivy-gate-frontend.png) |
| Fails on HIGH/CRITICAL (1) | `severity: HIGH,CRITICAL`, `exit-code: "1"`, `ignore-unfixed: true` |
| CVE explanation (1) | CVE-2025-8869 (pip) and CVE-2026-85091 (zlib): found, explained and remediated, [SECURITY.md](SECURITY.md) |

## M7: Terraform (15)

| Criterion | How it is met |
|-----------|---------------|
| Valid HCL in `terraform/` (2) | `terraform fmt -check` and `terraform validate` pass (also in CI), [m7-terraform-fmt-init-validate.png](screenshots/m7-terraform-fmt-init-validate.png) |
| `terraform init` OK (1) | [m7-terraform-fmt-init-validate.png](screenshots/m7-terraform-fmt-init-validate.png) |
| `terraform plan` non-empty, no errors (2) | `Plan: 64 to add` against AWS, [m7-aws-terraform-plan.png](screenshots/m7-aws-terraform-plan.png) |
| VPC with ≥ 2 public subnets (3) | `stockpilot-vpc` with 2 public + 2 private subnets in 2 AZs, [VPC](screenshots/m7-aws-console-vpc.png), [subnets](screenshots/m7-aws-console-subnets.png), [routes](screenshots/m7-aws-vpc-subnets-routes.png) |
| EKS with a worker node group (4) | `stockpilot-eks` (1.36, Active) with a managed node group of 2 nodes, [cluster](screenshots/m7-aws-console-eks-cluster.png), [node group](screenshots/m7-aws-console-eks-nodegroup.png), [nodes](screenshots/m7-aws-eks-cluster-nodes.png) |
| `terraform destroy` clean (2) | `Destroy complete! Resources: 58 destroyed`, nothing left in the account, [m7-aws-terraform-destroy.png](screenshots/m7-aws-terraform-destroy.png) |
| `terraform.tfvars.example`, no credentials (1) | [`terraform.tfvars.example`](../terraform/terraform.tfvars.example); `terraform.tfvars` and state files are git-ignored |

## M8: Kubernetes + Helm (15)

| Criterion | How it is met |
|-----------|---------------|
| `k8s/namespace.yaml` applies (1) | [m8-kubectl-get-pods.png](screenshots/m8-kubectl-get-pods.png) |
| Chart with `Chart.yaml`, `values.yaml`, templates (3) | [`helm/stockpilot/`](../helm/stockpilot/) (`helm lint` clean) |
| `helm upgrade --install` succeeds (3) | deployed, `helm test` passes, [m8-helm-list-and-test.png](screenshots/m8-helm-list-and-test.png) |
| ≥ 2 replicas for backend and frontend (2) | `replicaCount: 2` each (HPA minimum 2) |
| ClusterIP Services (2) | `stockpilot-backend`, `stockpilot-frontend`, `stockpilot-postgres`, [m8-kubectl-svc-ingress-hpa.png](screenshots/m8-kubectl-svc-ingress-hpa.png) |
| Ingress `/` → frontend, `/api` → backend (2) | `templates/ingress.yaml` (Traefik), [m8-app-via-ingress.png](screenshots/m8-app-via-ingress.png) |
| All pods Running (2) | 5/5 Running (2 backend, 2 frontend, 1 postgres), [m8-kubectl-get-pods.png](screenshots/m8-kubectl-get-pods.png) |

## M9: Observability (10)

| Criterion | How it is met |
|-----------|---------------|
| `/metrics` in Prometheus format (2) | [m9-metrics-endpoint.png](screenshots/m9-metrics-endpoint.png) |
| Prometheus installed and scraping (3) | kube-prometheus-stack + ServiceMonitor; `serviceMonitor/stockpilot/stockpilot-backend/0` UP, [m9-prometheus-targets-up.png](screenshots/m9-prometheus-targets-up.png) |
| Grafana installed and accessible (2) | http://grafana.localtest.me (local), port-forward on EKS |
| ≥ 1 panel with live app metrics (3) | 16-panel dashboard provisioned from the chart, [m9-grafana-dashboard.png](screenshots/m9-grafana-dashboard.png) |

## M10: Presentation + documentation (5)

| Criterion | How it is met |
|-----------|---------------|
| Root `README.md` explains the app (2) | [README.md](../README.md) |
| Live demo: commit → pipeline → deployment update (3) | the UI sidebar and `GET /api/info` show the deployed commit SHA, so each update is visible; release flow in README Section 8 |

---

## Submission checklist

**Application**
- [x] GitHub repository URL submitted
- [x] Application runs via `docker compose up --build`
- [x] At least 4 REST API endpoints implemented
- [x] Alembic migration file present

**Testing**
- [x] pytest passes (screenshot)
- [x] At least 5 test cases present

**Docker**
- [x] `backend/Dockerfile` builds
- [x] `frontend/Dockerfile` uses multi-stage build
- [x] Non-root user in both Dockerfiles

**CI/CD**
- [x] GitHub Actions workflow present
- [x] Pipeline runs on push to main
- [x] pytest runs in pipeline
- [x] Images pushed to GHCR with SHA tags

**Security**
- [x] Trivy scan in pipeline
- [x] No secrets committed to Git

**Terraform**
- [x] terraform plan output
- [x] VPC + EKS provisioned (AWS Console screenshots)
- [x] terraform destroy output

**Kubernetes + Helm**
- [x] kubectl get pods (all Running)
- [x] helm list
- [x] Application accessible via Ingress

**Observability**
- [x] /metrics endpoint
- [x] Prometheus Targets page (UP)
- [x] Grafana dashboard

**Documentation**
- [x] README.md present
- [x] Presentation completed or recording submitted
