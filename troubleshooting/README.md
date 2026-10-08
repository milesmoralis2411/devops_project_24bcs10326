# Troubleshooting lab

Four deliberately broken workloads, each one a failure you will meet in real clusters.
They run next to the healthy StockPilot release in the `stockpilot` namespace and comply
with its *restricted* Pod Security policy, so the only thing wrong is the bug being taught.

| # | File | Symptom | Root cause |
|---|------|---------|------------|
| 1 | `01-broken-image.yaml` | `ErrImagePull` → `ImagePullBackOff` | image tag does not exist |
| 2 | `02-broken-service.yaml` | Service has **no endpoints**, calls time out | selector label does not match any pod |
| 3 | `03-crashloop-bad-database-url.yaml` | `Error` → `CrashLoopBackOff`, restart count climbing | `DATABASE_URL` points at a non-existent host |
| 4 | `04-failing-readiness-probe.yaml` | `Running` but `0/1` READY, gets no traffic | readiness probe targets the wrong port |

The general method is the same every time:

```text
kubectl get        -> what state is it in?
kubectl describe   -> what does Kubernetes say about it? (Events at the bottom)
kubectl logs       -> what does the application say?
kubectl get events -> what happened, in order?
compare spec with reality -> fix -> verify
```

---

## 1. ImagePullBackOff

```bash
kubectl apply -f troubleshooting/01-broken-image.yaml
kubectl get pods -n stockpilot -l app=lab-broken-image
# lab-broken-image-xxxx   0/1   ImagePullBackOff
kubectl describe pod -n stockpilot -l app=lab-broken-image | tail -15
# Failed to pull image "ghcr.io/stockpilot-demo/stockpilot-backend:does-not-exist": ... not found
kubectl get events -n stockpilot --sort-by=.lastTimestamp | grep lab-broken-image
```

**Diagnosis:** the kubelet cannot download the image. Check the three usual suspects:
wrong repository/tag, private registry without `imagePullSecrets`, or no network path
to the registry (NAT gateway missing on EKS private subnets).

**Fix:** point at a tag that exists (in this project CI pushes `ghcr.io/<owner>/stockpilot-backend:<git-sha>`):

```bash
kubectl set image deployment/lab-broken-image backend="$(kubectl get deploy stockpilot-backend -n stockpilot -o jsonpath='{.spec.template.spec.containers[0].image}')" -n stockpilot
```

The pod pulls the image and starts. (It then cannot reach a database because this lab
deployment has no `DATABASE_URL` - which is scenario 3's lesson.)

---

## 2. Service with no endpoints

```bash
kubectl apply -f troubleshooting/02-broken-service.yaml
kubectl get svc lab-broken-service -n stockpilot           # exists, has a ClusterIP...
kubectl get endpointslices -n stockpilot -l kubernetes.io/service-name=lab-broken-service
# ENDPOINTS <unset>                                          # ...but routes to nothing
kubectl describe svc lab-broken-service -n stockpilot | grep Selector
# Selector: app.kubernetes.io/component=api,app.kubernetes.io/name=stockpilot
kubectl get pods -n stockpilot --show-labels | grep component=
# ... app.kubernetes.io/component=backend ...
```

Prove it from inside the cluster:

```bash
kubectl run curl --rm -it --restart=Never -n stockpilot --image=busybox:1.37 \
  --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":65534,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"curl","image":"busybox:1.37","command":["wget","-T","3","-qO-","http://lab-broken-service:8000/health"],"securityContext":{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}}]}}'
# wget: download timed out / connection refused
```

**Diagnosis:** a Service selects pods **only by labels**. No pod carries
`component=api`, so the Service has zero endpoints and kube-proxy has nowhere to send traffic.

**Fix:**

```bash
kubectl patch svc lab-broken-service -n stockpilot \
  -p '{"spec":{"selector":{"app.kubernetes.io/name":"stockpilot","app.kubernetes.io/component":"backend"}}}'
kubectl get endpointslices -n stockpilot -l kubernetes.io/service-name=lab-broken-service
# now lists the backend pod IPs on port 8000
```

---

## 3. CrashLoopBackOff

```bash
IMAGE=$(kubectl get deploy stockpilot-backend -n stockpilot -o jsonpath='{.spec.template.spec.containers[0].image}')
sed "s#STOCKPILOT_BACKEND_IMAGE#$IMAGE#" troubleshooting/03-crashloop-bad-database-url.yaml | kubectl apply -f -
kubectl get pods -n stockpilot -l app=lab-crashloop -w
# Error -> CrashLoopBackOff, RESTARTS 1, 2, 3 ... (back-off grows 10s, 20s, 40s ...)
kubectl logs -n stockpilot -l app=lab-crashloop --previous | tail -3
# psycopg.OperationalError: failed to resolve host 'postgres-does-not-exist'
```

**Diagnosis:** the image is fine and the container starts; the *application* exits
non-zero (the prestart step cannot reach PostgreSQL), so Kubernetes keeps restarting it.
`describe` tells you it is crashing; only `logs --previous` tells you **why**.

**Fix:** use the real database Service name and credentials, i.e. the Secret the chart creates:

```bash
kubectl set env deployment/lab-crashloop -n stockpilot --from=secret/stockpilot-db --keys=DATABASE_URL
kubectl get pods -n stockpilot -l app=lab-crashloop     # 1/1 Running
```

---

## 4. Running but not Ready

```bash
IMAGE=$(kubectl get deploy stockpilot-frontend -n stockpilot -o jsonpath='{.spec.template.spec.containers[0].image}')
sed "s#STOCKPILOT_FRONTEND_IMAGE#$IMAGE#" troubleshooting/04-failing-readiness-probe.yaml | kubectl apply -f -
kubectl get pods -n stockpilot -l app=lab-not-ready
# lab-not-ready-xxxx   0/1   Running   0
kubectl describe pod -n stockpilot -l app=lab-not-ready | grep -A2 Readiness
kubectl get events -n stockpilot --field-selector reason=Unhealthy | grep lab-not-ready
# Readiness probe failed: Get "http://10.244.x.x:80/healthz": connect: connection refused
```

**Diagnosis:** the process is alive (no restarts - that would be the *liveness* probe),
but the readiness probe never succeeds, so the pod is never added to any Service's
endpoints. The unprivileged Nginx image listens on **8080**, not 80.

**Fix:**

```bash
kubectl patch deployment lab-not-ready -n stockpilot --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/port","value":8080}]'
kubectl get pods -n stockpilot -l app=lab-not-ready     # 1/1 Running
```

---

## Clean up

```bash
kubectl delete deployment lab-broken-image lab-crashloop lab-not-ready -n stockpilot --ignore-not-found
kubectl delete service lab-broken-service -n stockpilot --ignore-not-found
```

## Bonus: a real incident from building this project

While deploying, `helm upgrade --reuse-values -f values-dev.yaml` silently reset the frontend
image tag to `local`, a tag that did not exist on the kind nodes. The new frontend pod went into
`ImagePullBackOff` and `helm upgrade --wait` timed out (`UPGRADE FAILED ... context deadline exceeded`).
**Users saw no outage**: the Deployment uses `maxUnavailable: 0`, so the old pods kept serving until
a healthy replacement existed. `helm history stockpilot -n stockpilot` showed the failed revision; a
corrected `helm upgrade` (or `helm rollback stockpilot <revision>`) fixed it.
