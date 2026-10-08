# Submission checklist (mapped to GRADING.md)

Legend: ✅ implemented and verified in this repo · 📸 evidence *you* capture (command given) ·
👤 needs your own GitHub/AWS account.

Before you start: `docker compose up --build` for M1/M4, `scripts/local-k8s-up.sh` for the
local Kubernetes evidence (M8/M9), and the [AWS guide](AWS-EKS-GUIDE.md) for M7 and the EKS
versions of M8/M9.

---

## M1: Application (10)

| Criterion | Evidence |
|-----------|----------|
| FastAPI starts, `/health` responds (2) | ✅ `curl http://localhost:8000/health` → `{"status":"UP"}` |
| ≥ 4 REST endpoints GET/POST/PUT/DELETE (3) | ✅ 11 `/api` endpoints (+ `/health`, `/ready`, `/metrics`), see README §5; Swagger at `/docs` |
| PostgreSQL table managed by Alembic (2) | ✅ `backend/alembic/versions/0001_*.py`, `0002_*.py`; `docker compose exec postgres psql -U stockpilot -c '\dt'` |
| Frontend renders and calls the API (2) | ✅ React UI calls `/api/products`, `/api/stats`, `/api/movements`, … |
| Responsive, usable UI (1) | ✅ verified at 1440/820/390 px (`docs/images/responsive.png`) |

📸 Browser at http://localhost:3000 with data, plus an adjust-stock or create-product action.

## M2: Testing (10)

| Criterion | Evidence |
|-----------|----------|
| `pytest` runs without errors (3) | ✅ 51 passed |
| ≥ 5 tests covering ≥ 3 endpoints (4) | ✅ 51 tests covering all 13 routes (`backend/tests/`) |
| Test DB / mock, not production (2) | ✅ `tests/conftest.py` forces in-memory SQLite (CI also uses a throw-away PostgreSQL container) |
| `pytest.ini` / `conftest.py` (1) | ✅ both present |

📸 `cd backend && pytest -v` (all green; add `--cov=app` to show 99% coverage).

## M3: Git and GitHub (5)

| Criterion | Evidence |
|-----------|----------|
| Public repository linked (2) | 👤 create the repo and push (`git remote add origin … && git push -u origin main`) |
| Meaningful commit messages (2) | ✅ conventional-commit history (`feat(helm): …`, `test(backend): …`, `ci: …`) |
| `.gitignore` covers `.env`, `__pycache__`, `node_modules`, `.venv` (1) | ✅ root `.gitignore` |

📸 `git log --oneline` or GitHub's *Commits* page (20+ commits).

## M4: Docker (10)

| Criterion | Evidence |
|-----------|----------|
| `backend/Dockerfile` builds (2) | ✅ multi-stage, `docker build ./backend` |
| Frontend multi-stage Node → Nginx (3) | ✅ `node:24-alpine` build → `nginx-unprivileged:1.30-alpine` |
| Images run as non-root (2) | ✅ `docker run --rm --entrypoint id stockpilot-backend:local` → uid 10001; frontend → uid 101 |
| `docker compose up --build` starts all 3 services (3) | ✅ postgres, backend, frontend all `healthy` |

📸 Terminal with `docker compose up --build` + `docker compose ps` (3 × healthy) · browser at http://localhost:3000.

## M5: CI/CD (15)

| Criterion | Evidence |
|-----------|----------|
| Workflow file (1) | ✅ `.github/workflows/ci-cd.yml` (validated with actionlint) |
| Triggers on push to `main` (1) | ✅ `on: push: branches: [main]` (+ PRs, manual) |
| pytest job fails the build (3) | ✅ `backend-test`; every later job `needs:` it |
| Frontend built in pipeline (2) | ✅ `frontend-build`: `npm ci`, `npm test`, `npm run build` |
| Images built for both (3) | ✅ `build-scan-push` matrix: backend + frontend |
| Pushed to GHCR (3) | ✅ `docker push ghcr.io/<owner>/stockpilot-*` (main only) |
| Tag = commit SHA, not latest (2) | ✅ `:${GITHUB_SHA}`; `latest` is never pushed |

📸 👤 Actions run page with all jobs green (URL for the form) · GitHub *Packages* page showing both images with SHA tags.

## M6: Trivy (5)

| Criterion | Evidence |
|-----------|----------|
| Trivy scans both images in CI (3) | ✅ two Trivy steps per matrix image |
| Fails on HIGH/CRITICAL (1) | ✅ `severity: HIGH,CRITICAL`, `exit-code: "1"`, `ignore-unfixed: true` |
| Explain a CVE / clean result (1) | ✅ paragraph + real findings table in [SECURITY.md](SECURITY.md) |

📸 👤 Expand the *Trivy security gate* step in the Actions log.

## M7: Terraform (15) 👤 needs AWS

| Criterion | Evidence |
|-----------|----------|
| Valid HCL in `terraform/` (2) | ✅ `terraform fmt -check` + `terraform validate` pass (also in CI) |
| `terraform init` OK (1) | ✅ |
| `terraform plan` non-empty, no errors (2) | ✅ offline proof: `terraform test` plans 59/64 resources with mocked AWS · 📸 real `terraform plan` |
| VPC with ≥ 2 public subnets (3) | ✅ 2 public + 2 private subnets in 2 AZs |
| EKS with a worker node group (4) | ✅ managed node group `default`, 2 × t3.medium |
| `terraform destroy` clean (2) | ✅ `scripts/eks-teardown.sh` removes Kubernetes-created AWS resources first |
| `terraform.tfvars.example`, no credentials (1) | ✅ present; `terraform.tfvars`/state git-ignored |

📸 `terraform plan` output · AWS Console: VPC + subnets and the EKS cluster/node group in ap-south-1 · `Destroy complete!`.

## M8: Kubernetes + Helm (15)

| Criterion | Evidence |
|-----------|----------|
| `k8s/namespace.yaml` applies (1) | ✅ `kubectl apply -f k8s/namespace.yaml` |
| Chart with `Chart.yaml`, `values.yaml`, templates (3) | ✅ `helm/stockpilot/` (`helm lint` clean) |
| `helm upgrade --install` succeeds (3) | ✅ plus `helm test` passes |
| ≥ 2 replicas for backend and frontend (2) | ✅ `replicaCount: 2` each (HPA min 2) |
| ClusterIP Services (2) | ✅ `stockpilot-backend`, `stockpilot-frontend`, `stockpilot-postgres` |
| Ingress `/` → frontend, `/api` → backend (2) | ✅ `templates/ingress.yaml` (Traefik) |
| All pods Running (2) | ✅ 5/5 Running (2 backend, 2 frontend, 1 postgres) |

📸 `kubectl get pods -n stockpilot` · `kubectl get svc -n stockpilot` · `helm list -n stockpilot` ·
browser via Ingress: http://stockpilot.localtest.me (local) or the AWS load balancer hostname (EKS).
Bonus: `kubectl get hpa -n stockpilot` during `scripts/load-test.sh`.

## M9: Observability (10)

| Criterion | Evidence |
|-----------|----------|
| `/metrics` in Prometheus format (2) | ✅ `curl http://localhost:8000/metrics` |
| Prometheus installed and scraping (3) | ✅ kube-prometheus-stack + ServiceMonitor; target `serviceMonitor/stockpilot/stockpilot-backend/0` UP |
| Grafana installed and accessible (2) | ✅ http://grafana.localtest.me (local) / port-forward (EKS) |
| ≥ 1 panel with live app metrics (3) | ✅ 16-panel dashboard, provisioned automatically |

📸 `/metrics` output · Prometheus *Status → Target health* filtered by `stockpilot` · Grafana dashboard (run `scripts/load-test.sh` first for lively graphs).

## M10: Presentation + documentation (5)

| Criterion | Evidence |
|-----------|----------|
| Root `README.md` explains the app (2) | ✅ |
| Live demo: commit → pipeline → deployment update (3) | 👤 follow [DEMO-SCRIPT.md](DEMO-SCRIPT.md); the UI shows the deployed commit SHA, so the update is visible |

---

## Before you submit

```text
[ ] Repository pushed to GitHub (public, or instructor access granted)
[ ] Actions run green, both images in GHCR with SHA tags
[ ] terraform plan, AWS Console (VPC + EKS) and terraform destroy screenshots
[ ] kubectl get pods / svc, helm list, app via Ingress screenshots
[ ] /metrics, Prometheus targets (UP), Grafana dashboard screenshots
[ ] pytest -v and docker compose screenshots
[ ] AWS resources destroyed (check EC2 → Load Balancers / Volumes are empty)
[ ] No secrets in git history:  git log -p | grep -iE "AKIA|secret_access|password=" (should only hit docs/examples)
```
