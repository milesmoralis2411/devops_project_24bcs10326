# Terraform: AWS VPC + EKS

Infrastructure as Code for the production-style environment. Instead of clicking through
*AWS Console → VPC → Subnets → EKS → Node groups*, the desired state is described here and
Terraform creates, changes or destroys real resources to match it.

```text
AWS account (ap-south-1)
└── VPC 10.20.0.0/16                                   main.tf  (terraform-aws-modules/vpc ~> 6.7)
    ├── public subnets  10.20.48.0/24, 10.20.49.0/24   load balancers, NAT gateway  (2 AZs)
    ├── private subnets 10.20.0.0/20,  10.20.16.0/20   worker nodes                 (2 AZs)
    ├── Internet gateway + 1 NAT gateway
    └── EKS cluster "stockpilot-eks" (Kubernetes 1.36)   eks.tf   (terraform-aws-modules/eks ~> 21.29)
        ├── add-ons: vpc-cni, coredns, kube-proxy, pod-identity-agent, aws-ebs-csi-driver
        ├── managed node group "default": 2 x t3.medium (min 2 / max 4), Amazon Linux 2023
        └── IAM role for the EBS CSI driver (EKS Pod Identity) -> PostgreSQL volumes
GitHub OIDC provider + deploy role (optional)           github-oidc.tf
```

| File | Purpose |
|------|---------|
| `versions.tf` | Terraform / provider version constraints (+ commented S3 remote-state backend) |
| `providers.tf` | AWS provider, region, default tags on every resource |
| `variables.tf` | All inputs with types, defaults and validation rules |
| `main.tf` | Availability zones, subnet maths, VPC module |
| `eks.tf` | EKS cluster, node group, add-ons, EBS CSI IAM role |
| `github-oidc.tf` | Keyless GitHub Actions → AWS auth and EKS access entry (optional) |
| `outputs.tf` | Cluster name/endpoint, VPC/subnet IDs, kubectl command, deploy role ARN |
| `terraform.tfvars.example` | Copy to `terraform.tfvars` (git-ignored) |
| `tests/plan.tftest.hcl` | `terraform test` - plans everything against mocked AWS (no credentials) |
| `.terraform.lock.hcl` | Locked provider versions + checksums for linux/windows/macOS |

## Prerequisites

* Terraform ≥ 1.7, AWS CLI v2, kubectl, Helm
* An AWS identity with admin-level rights configured locally: `aws configure` (or `AWS_PROFILE`).
  **Never put access keys in these files.**

## Workflow

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars      # set github_repository = "<you>/<repo>"

terraform init                 # download providers + modules
terraform fmt -recursive       # canonical formatting
terraform validate             # static checks
terraform test                 # offline plan against mocked AWS (3 tests)
terraform plan -out tfplan     # "Plan: 63 to add" (58 without github_repository)
terraform apply tfplan         # 15-20 minutes (EKS control plane + nodes)

$(terraform output -raw configure_kubectl)   # aws eks update-kubeconfig ...
kubectl get nodes                            # 2 Ready nodes
```

Then continue with [docs/AWS-EKS-GUIDE.md](../docs/AWS-EKS-GUIDE.md) (add-ons, GitHub OIDC
deploys, opening the app).

## Cost and tear-down

Roughly **US$0.30 per hour** while running in ap-south-1: EKS control plane $0.10/h,
2 × t3.medium, one NAT gateway, one load balancer, small EBS volumes. Destroy it when
finished:

```bash
scripts/eks-teardown.sh        # removes the load balancer + volumes Kubernetes created, then terraform destroy
```

Plain `terraform destroy` can hang on the VPC because the AWS load balancer and EBS volumes
created *by Kubernetes* are not in Terraform's state - the script deletes them first and
then lists anything still tagged for the cluster (the list should be empty).

## Design notes

* **Kubernetes 1.36** is in EKS *standard* support until Aug 2027. Versions in *extended*
  support (1.31–1.33 at the time of writing) cost $0.60/h instead of $0.10/h.
* **AL2023 node AMI**: EKS stopped publishing Amazon Linux 2 AMIs for 1.33+.
* **EBS CSI driver**: without it, PersistentVolumeClaims (PostgreSQL) stay `Pending` on EKS.
  New clusters also have no default StorageClass, hence `k8s/eks-storageclass-gp3.yaml`.
  Its AWS permissions come through **EKS Pod Identity**, not IRSA, so no IAM OIDC provider
  is needed (`enable_irsa = false`). Some organizations, including the Free-plan account used
  for this project's AWS deployment, block `iam:CreateOpenIDConnectProvider`.
* **Free-plan accounts** only allow free-tier-eligible instance types. `t3.medium` is not one,
  so the deployed environment used `node_instance_types = ["m7i-flex.large"]`
  (2 vCPU / 8 GiB, eligible). List the eligible types with
  `aws ec2 describe-instance-types --filters Name=free-tier-eligible,Values=true`.
* **Single NAT gateway** keeps the lab cheap; production would use one per AZ.
* **GitHub OIDC** replaces long-lived `AWS_ACCESS_KEY_ID` secrets in GitHub with short-lived
  credentials, and only the `main` branch of your repository can assume the role.
