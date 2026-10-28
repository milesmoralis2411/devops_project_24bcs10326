# Demo

| File | What it is |
|------|------------|
| [StockPilot-demo.mp4](StockPilot-demo.mp4) | Narrated demo video, 9 min 20 s, 1920×1080, English subtitles (embedded track) |
| [StockPilot-demo.pdf](StockPilot-demo.pdf) | Slide deck, 19 slides |
| [StockPilot-demo.pptx](StockPilot-demo.pptx) | The same deck as PowerPoint |

The video was recorded on the running system on 28 Oct 2026: the local three-node kind cluster
(app, Ingress, HPA, Prometheus, Grafana), GitHub Actions and GHCR. The Terraform section shows
the real AWS run in ap-southeast-2 from 9 Oct 2026, captured before that environment was destroyed.

## Live demo: commit → pipeline → deployment update

| Step | Evidence in the video |
|------|-----------------------|
| Commit | `feat(ui): update dashboard subtitle` ([`44fae08`](https://github.com/milesmoralis2411/devops_project_24bcs10326/commit/44fae08e4f337cc0b42a342c5e88ee5158636422)), pushed to `main` |
| Pipeline | [CI run #12](https://github.com/milesmoralis2411/devops_project_24bcs10326/actions/runs/40734964365): tests, frontend build and IaC checks, then build → Trivy gate → push; green in 2 m 25 s |
| Registry | `ghcr.io/milesmoralis2411/stockpilot-{backend,frontend}:44fae08e4f33…` |
| Security | Trivy on both pushed images: 0 fixable HIGH/CRITICAL vulnerabilities |
| Deploy | `helm upgrade` with both image tags set to the SHA, rolling update, Helm revision 10 |
| Verify | new subtitle in the UI; sidebar build, `kubectl get deploy` and `/api/info` all show `44fae08` |

## Chapters

| Time | Section |
|------|---------|
| 0:00 | Introduction, the application, architecture |
| 1:13 | M1 Application: dashboard, restock, oversell protection, movement log |
| 2:14 | M1 REST API (Swagger), health/readiness/metrics, HTTP 409 on oversell, Alembic tables |
| 2:58 | M2 Testing: 51 pytest tests, 99% coverage |
| 3:20 | M4 Docker: multi-stage non-root images, Docker Compose with health checks |
| 3:49 | M5 CI/CD and the live demo: commit, pipeline run, GHCR |
| 5:25 | M6 Security: Trivy gate on the pushed images |
| 5:38 | Deployment update: `helm upgrade`, rolling update, verification in the UI |
| 6:34 | M7 Terraform: VPC + EKS code, `terraform test`, the real AWS run |
| 7:28 | M8 Kubernetes + Helm: workloads, Ingress, PDBs, `helm test` |
| 7:48 | M8 Autoscaling: load test, HPA 2 → 4 → 6 pods |
| 8:09 | M9 Observability: Prometheus targets and alert rules, Grafana dashboard under load |
| 8:42 | Troubleshooting: Service with no endpoints, diagnosed and fixed |
| 9:06 | Summary |
