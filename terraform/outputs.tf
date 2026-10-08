output "aws_region" {
  description = "Region the infrastructure lives in"
  value       = var.aws_region
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnets (internet-facing load balancers, NAT gateway)"
  value       = module.vpc.public_subnets
}

output "private_subnet_ids" {
  description = "Private subnets (EKS worker nodes)"
  value       = module.vpc.private_subnets
}

output "nat_gateway_public_ips" {
  description = "Egress IPs of the NAT gateway"
  value       = module.vpc.nat_public_ips
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_version" {
  description = "Kubernetes version of the control plane"
  value       = module.eks.cluster_version
}

output "node_group_names" {
  description = "Managed node groups"
  value       = keys(module.eks.eks_managed_node_groups)
}

output "configure_kubectl" {
  description = "Run this to point kubectl at the new cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "github_deploy_role_arn" {
  description = "Set as the AWS_DEPLOY_ROLE_ARN repository variable in GitHub (empty when OIDC is disabled)"
  value       = local.github_oidc_enabled ? aws_iam_role.github_deploy[0].arn : ""
}
