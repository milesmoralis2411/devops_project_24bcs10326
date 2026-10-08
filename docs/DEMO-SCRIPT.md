# Live demo script (12–15 minutes)

Follows the path the grading rubric asks for: *application → commit → CI → image → scan →
registry → Terraform → Kubernetes → Helm → Ingress → autoscaling → monitoring → troubleshooting*.

## Prepare (before the session)

* EKS running ([AWS guide](AWS-EKS-GUIDE.md) steps 1–6) **or** the local cluster: `scripts/local-k8s-up.sh`.
* Browser tabs: the app (via Ingress) · GitHub repo → *Actions* · GitHub → *Packages* ·
  Grafana dashboard · Prometheus targets · AWS Console (VPC, EKS).
* Terminal in the repo root with a large font. Have `kubectl get hpa -n stockpilot -w` ready in a second terminal.
* Run `scripts/load-test.sh` once ~10 minutes before, so Grafana has history.

---

### 1. The application (2 min)
*"StockPilot is an inventory system: products, stock movements, reorder alerts."*
* Dashboard: KPIs, reorder alerts, activity feed.
* **Restock** a low-stock item from the alerts panel → toast, KPI and feed update.
* Try to **sell more than is on hand**: the UI blocks it; mention the API also returns 409 and uses a row lock.
* Point at the sidebar: *"Build `abc1234`: this is the Git commit currently running."*

### 2. The API and database (1 min)
* `/docs` → `GET /api/stats` → *Try it out*.
* `kubectl exec -n stockpilot stockpilot-postgres-0 -- psql -U stockpilot -c "select sku, quantity from products limit 5;"`
* *"The schema comes from Alembic migrations, not create_all."*

### 3. The change: commit → pipeline → deployment (4 min, the key moment)
Make a visible change, e.g. in `frontend/src/App.jsx` change the dashboard subtitle text:

```bash
git checkout -b demo-change            # optional: show a PR
# edit 'Live stock levels, reorder alerts and recent movements.' -> '... - deployed live in class!'
git commit -am "feat(ui): update dashboard subtitle for the live demo"
git push origin HEAD:main             # or open a PR and merge it
```

While the pipeline runs, walk through it in the *Actions* tab:
1. **backend-test**: ruff, 51 pytest tests on SQLite *and* PostgreSQL, migration round-trip. *"If a test fails, nothing below runs, so no broken image is ever built."*
2. **frontend-build** and **iac-validate** (Terraform test with mocked AWS, Helm lint) run in parallel.
3. **build-scan-push**: Docker build → **Trivy** (open the log: table, then the HIGH/CRITICAL gate) → push to **GHCR** tagged with the commit SHA.
4. **deploy**: OIDC login to AWS (no stored keys) → `helm upgrade --install --set image.tag=<sha>` → `helm test`.

Meanwhile in the terminal: `kubectl get pods -n stockpilot -w`. New pods appear and old ones
terminate, with zero downtime (`maxUnavailable: 0`).

Refresh the app: **new subtitle, and the sidebar build SHA now matches the commit you just pushed.**
GitHub *Packages*: the new SHA tag is there.

### 4. Infrastructure as Code (2 min)
* `terraform/main.tf` + `eks.tf`: VPC, 2 public/2 private subnets, NAT, EKS 1.36, managed node group, EBS CSI.
* AWS Console: the VPC and EKS cluster in ap-south-1. *"None of this was clicked together."*
* `terraform output`.

### 5. Kubernetes and Helm (2 min)
```bash
kubectl get pods,svc,ingress,hpa -n stockpilot
helm list -n stockpilot
helm history stockpilot -n stockpilot      # each CI deploy is a revision; rollback = helm rollback
```
*Ingress: `/` → frontend, `/api` → backend; Traefik implements it (ingress-nginx retired in 2026).*

### 6. Autoscaling (1–2 min)
```bash
scripts/load-test.sh          # terminal 2 shows: cpu 3% → 300%+, replicas 2 → 4 → 6
```

### 7. Monitoring (1 min)
* Prometheus targets: `stockpilot-backend` **UP** for every pod.
* Grafana: request rate climbing, p95 latency, **CPU per pod and HPA replicas rising together**, inventory KPIs.

### 8. Failure simulation (2 min)
```bash
kubectl apply -f troubleshooting/02-broken-service.yaml
kubectl get endpointslices -n stockpilot -l kubernetes.io/service-name=lab-broken-service   # <unset>
kubectl describe svc lab-broken-service -n stockpilot | grep Selector
kubectl get pods -n stockpilot --show-labels | grep component=
kubectl patch svc lab-broken-service -n stockpilot -p '{"spec":{"selector":{"app.kubernetes.io/name":"stockpilot","app.kubernetes.io/component":"backend"}}}'
kubectl get endpointslices -n stockpilot -l kubernetes.io/service-name=lab-broken-service   # pod IPs appear
```
Alternative: `01-broken-image.yaml` (ImagePullBackOff → `describe` → wrong tag).

### Wrap-up (30 s)
*"Every layer is code in one repository; one `git push` tests, scans, publishes and
deploys a traceable version; Kubernetes keeps it healthy and scales it; Prometheus and
Grafana show what it is doing."*

Finally, destroy AWS resources: `scripts/eks-teardown.sh`.

---

## Likely questions

| Question | Short answer |
|----------|--------------|
| Liveness vs readiness? | Liveness = restart if the process is stuck (`/health`, no DB). Readiness = only send traffic when it can serve (`/ready`, checks DB). |
| Why tag images with the SHA? | Immutable and traceable; `latest` changes underneath you and breaks rollbacks. |
| Why does HPA need resource requests? | Utilization is measured as a percentage of the CPU *request*; metrics-server supplies the usage. |
| Database in Kubernetes vs RDS? | StatefulSet + PVC is fine for a lab; RDS gives managed backups, Multi-AZ failover and patching. The chart supports `externalDatabase.url`. |
| What if two pods run migrations at once? | Alembic runs under a PostgreSQL advisory lock, so they migrate one after another. |
| Ingress vs Ingress Controller? | The Ingress is just routing rules; the controller (Traefik) is the proxy that implements them. |
| What does Trivy *not* catch? | Bugs in our code, secrets, misconfigurations at runtime: other layers (lint/SAST, secret scanning, Pod Security) cover those. |
| How do you roll back? | `helm rollback stockpilot <revision> -n stockpilot`, or revert the commit and let the pipeline redeploy. |
