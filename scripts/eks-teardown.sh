#!/usr/bin/env bash
# Clean, cost-safe teardown of the AWS environment.
#
# Why not just `terraform destroy`? Kubernetes itself creates AWS resources that are NOT
# in Terraform's state: the Network Load Balancer for the Traefik Service and the EBS
# volumes behind PersistentVolumeClaims. If they still exist, destroying the VPC hangs or
# fails (their network interfaces keep the subnets/security groups in use) and leftover
# volumes keep costing money. So: remove them first, then let Terraform destroy the rest.
#
# Usage: scripts/eks-teardown.sh            (terraform asks for confirmation)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGION="${AWS_REGION:-ap-south-1}"
CLUSTER="${CLUSTER_NAME:-stockpilot-eks}"

if aws eks describe-cluster --name "$CLUSTER" --region "$REGION" >/dev/null 2>&1; then
  echo "==> Connecting to $CLUSTER"
  aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER" >/dev/null

  echo "==> Removing the application and its persistent volumes (EBS)"
  helm uninstall stockpilot -n stockpilot --wait 2>/dev/null || true
  kubectl delete pvc --all -n stockpilot --wait=true 2>/dev/null || true

  echo "==> Removing monitoring and the ingress controller (deletes the AWS load balancer)"
  helm uninstall kube-prometheus-stack -n monitoring --wait 2>/dev/null || true
  kubectl delete pvc --all -n monitoring --wait=true 2>/dev/null || true
  helm uninstall traefik -n traefik --wait 2>/dev/null || true

  echo "==> Waiting for LoadBalancer Services to disappear"
  for _ in $(seq 1 30); do
    remaining="$(kubectl get svc -A -o jsonpath='{range .items[?(@.spec.type=="LoadBalancer")]}{.metadata.name}{"\n"}{end}' | grep -c . || true)"
    [[ "$remaining" -eq 0 ]] && break
    sleep 10
  done
  echo "    giving AWS 60s to release load balancer network interfaces..."
  sleep 60
else
  echo "==> Cluster $CLUSTER not found in $REGION - skipping Kubernetes cleanup"
fi

echo "==> terraform destroy"
# cd instead of -chdir: on Windows (Git Bash) a native terraform.exe cannot resolve /c/... paths.
(cd "$ROOT/terraform" && terraform destroy "$@")

echo "==> Leftover check - anything Kubernetes tagged for this cluster (should print nothing):"
aws resourcegroupstaggingapi get-resources --region "$REGION" \
  --tag-filters "Key=kubernetes.io/cluster/$CLUSTER" \
  --query 'ResourceTagMappingList[].ResourceARN' --output text || true
