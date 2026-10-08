# AWS EKS: end-to-end guide

From an empty AWS account to StockPilot running on EKS, deployed automatically by every
push to `main`, and back to zero cost.

> **Cost:** about US$0.30/hour while the cluster exists. Do steps 1–6 in one sitting,
> capture your screenshots, then run step 8.

## 0. Prerequisites

| Tool | Check |
|------|-------|
| AWS account + IAM user/role with admin rights | `aws sts get-caller-identity` |
| AWS CLI v2 configured for `ap-south-1` | `aws configure` |
| Terraform ≥ 1.7 | `terraform version` |
| kubectl, Helm ≥ 3.14 (v4 tested) | `kubectl version --client`, `helm version` |
| The project pushed to **your** GitHub repository | see step 4 |

## 1. Provision the VPC and EKS cluster

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
#   github_repository = "<your-github-user>/<your-repo>"   (enables keyless CI deploys)
#   create_github_oidc_provider = false   only if your account already has the GitHub OIDC provider
terraform init
terraform plan -out tfplan        # 📸 screenshot: "Plan: 64 to add, 0 to change, 0 to destroy"
terraform apply tfplan            # 15-20 min
terraform output                  # cluster name, VPC/subnet IDs, deploy role ARN
```

📸 **AWS Console screenshots** (region *Asia Pacific (Mumbai) ap-south-1*):
* *VPC → Your VPCs*: `stockpilot-vpc`; *Subnets*: 2 public + 2 private
* *EKS → Clusters → stockpilot-eks*: Active, version 1.36; *Compute* tab: node group `default`, 2 nodes

## 2. Connect kubectl

```bash
aws eks update-kubeconfig --region ap-south-1 --name stockpilot-eks
kubectl get nodes -o wide         # 2 nodes Ready
```

## 3. Install cluster add-ons

```bash
kubectl apply -f k8s/eks-storageclass-gp3.yaml   # default StorageClass for PostgreSQL volumes
scripts/bootstrap-cluster.sh eks                  # Traefik (AWS NLB), metrics-server, Prometheus + Grafana
kubectl get svc traefik -n traefik                # EXTERNAL-IP = the public load balancer DNS name
```

The NLB DNS name takes 2–3 minutes to start resolving.

## 4. Push the code to GitHub

```bash
git remote add origin https://github.com/<your-github-user>/<your-repo>.git
git push -u origin main
```

The first pipeline run tests, builds, scans and pushes the images. The **deploy job is
skipped** because the repository is not configured for AWS yet.

## 5. Allow GitHub Actions to deploy

1. **Repository variables** (*Settings → Secrets and variables → Actions → Variables*):

   | Variable | Value |
   |----------|-------|
   | `AWS_DEPLOY_ROLE_ARN` | `terraform -chdir=terraform output -raw github_deploy_role_arn` |
   | `AWS_REGION` | `ap-south-1` |
   | `EKS_CLUSTER_NAME` | `stockpilot-eks` |

   These are *variables*, not secrets: an IAM role ARN is not a credential. Only
   workflows on the `main` branch of this exact repository can assume the role.

2. **Image visibility.** GHCR packages are private by default. Either make both packages
   public (*your profile → Packages → stockpilot-backend → Package settings → Change
   visibility → Public*, same for `stockpilot-frontend`), or keep them private and give the
   cluster a pull secret:

   ```bash
   kubectl create namespace stockpilot --dry-run=client -o yaml | kubectl apply -f -
   kubectl create secret docker-registry ghcr-pull -n stockpilot --docker-server=ghcr.io \
     --docker-username=<github-user> --docker-password=<PAT with read:packages>
   # then add to helm/stockpilot/values-prod.yaml:  imagePullSecrets: [{name: ghcr-pull}]
   ```

3. *(Optional)* *Settings → Environments → production*: add yourself as a required reviewer
   to get a manual approval gate before every production deploy.

## 6. Deploy by pushing a commit

```bash
git commit --allow-empty -m "chore: trigger first EKS deployment"
git push
```

*Actions* tab → the `deploy` job runs `helm upgrade --install` with
`backend.image.tag=<commit SHA>`, waits for the rollout and runs `helm test`.

```bash
kubectl get pods,svc,ingress,hpa -n stockpilot      # 📸 all Running
helm list -n stockpilot                             # 📸
echo "http://$(kubectl get svc traefik -n traefik -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
```

Open that URL: the UI sidebar shows the commit SHA you just pushed. 📸

Monitoring on EKS (kept private, no public Ingress):

```bash
kubectl port-forward svc/kube-prometheus-stack-grafana 3001:80 -n monitoring        # http://localhost:3001
kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring   # http://localhost:9090/targets
```

## 7. Optional: deploy manually without the pipeline

```bash
OWNER=<your-github-user-in-lowercase>; SHA=<a commit SHA that CI has pushed>
kubectl apply -f k8s/namespace.yaml
helm upgrade --install stockpilot ./helm/stockpilot -n stockpilot -f helm/stockpilot/values-prod.yaml \
  --set backend.image.repository=ghcr.io/$OWNER/stockpilot-backend  --set backend.image.tag=$SHA \
  --set frontend.image.repository=ghcr.io/$OWNER/stockpilot-frontend --set frontend.image.tag=$SHA \
  --wait --timeout 10m
```

## 8. Tear everything down

```bash
scripts/eks-teardown.sh      # 📸 "Destroy complete! Resources: 64 destroyed."
```

The script uninstalls the Helm releases first, which deletes the AWS load balancer and
EBS volumes that Kubernetes created outside Terraform's state. It then runs
`terraform destroy` and lists anything still tagged for the cluster (should be nothing).
Finally, check *EC2 → Load Balancers* and *EC2 → Volumes* in the console for leftovers.

## Common problems

| Symptom | Cause / fix |
|---------|-------------|
| `deploy` job skipped | `AWS_DEPLOY_ROLE_ARN` repository variable not set |
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | `github_repository` in tfvars does not exactly match `owner/repo`, or the run is not on `main` |
| Pods `ImagePullBackOff` with `403`/`denied` | GHCR packages are private, see step 5.2 |
| `stockpilot-postgres-0` `Pending` | gp3 StorageClass missing (`kubectl apply -f k8s/eks-storageclass-gp3.yaml`) or EBS CSI add-on not ready |
| Ingress has no address / site unreachable | Traefik not installed (step 3) or NLB still provisioning |
| HPA shows `<unknown>` | metrics-server not installed or still starting (1–2 min) |
| `terraform destroy` hangs on subnets/IGW | a Kubernetes LoadBalancer still exists, so use `scripts/eks-teardown.sh` |
