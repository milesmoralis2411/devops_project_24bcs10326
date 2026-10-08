# `terraform test` - plans the whole stack against MOCKED providers, so it runs in CI
# (and on any laptop) without AWS credentials and without creating anything.

mock_provider "aws" {
  override_data {
    target = data.aws_availability_zones.available
    values = {
      names = ["ap-south-1a", "ap-south-1b", "ap-south-1c"]
    }
  }

  # The AWS provider validates ARNs and policy JSON even during plan, so mocked
  # values must look real.
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
      arn        = "arn:aws:iam::123456789012:user/student"
      user_id    = "AIDAMOCKSTUDENT"
    }
  }
  mock_data "aws_iam_session_context" {
    defaults = {
      issuer_arn = "arn:aws:iam::123456789012:user/student"
    }
  }
  mock_data "aws_partition" {
    defaults = {
      partition  = "aws"
      dns_suffix = "amazonaws.com"
    }
  }
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }
  mock_resource "aws_iam_role" {
    defaults = {
      arn = "arn:aws:iam::123456789012:role/mock-role"
    }
  }
  mock_resource "aws_iam_policy" {
    defaults = {
      arn = "arn:aws:iam::123456789012:policy/mock-policy"
    }
  }
  mock_resource "aws_iam_openid_connect_provider" {
    defaults = {
      arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
    }
  }
  mock_resource "aws_kms_key" {
    defaults = {
      arn = "arn:aws:kms:ap-south-1:123456789012:key/00000000-0000-0000-0000-000000000000"
    }
  }
  mock_resource "aws_eks_cluster" {
    defaults = {
      arn      = "arn:aws:eks:ap-south-1:123456789012:cluster/stockpilot-eks"
      endpoint = "https://MOCK.gr7.ap-south-1.eks.amazonaws.com"
      identity = [{ oidc = [{ issuer = "https://oidc.eks.ap-south-1.amazonaws.com/id/MOCK" }] }]
    }
  }
}
mock_provider "tls" {}
mock_provider "cloudinit" {}
mock_provider "null" {}
mock_provider "time" {}

run "network_has_two_public_and_two_private_subnets" {
  command = plan

  assert {
    condition     = length(local.azs) == 2
    error_message = "Expected subnets in two availability zones"
  }

  assert {
    condition     = local.public_subnets == ["10.20.48.0/24", "10.20.49.0/24"]
    error_message = "Unexpected public subnet CIDRs: ${jsonencode(local.public_subnets)}"
  }

  assert {
    condition     = local.private_subnets == ["10.20.0.0/20", "10.20.16.0/20"]
    error_message = "Unexpected private subnet CIDRs: ${jsonencode(local.private_subnets)}"
  }

  assert {
    condition     = length(aws_iam_role.github_deploy) == 0
    error_message = "GitHub OIDC role must not be created when github_repository is empty"
  }
}

run "github_oidc_deploy_role_is_optional" {
  command = plan

  variables {
    github_repository = "student/stockpilot"
  }

  assert {
    condition     = length(aws_iam_role.github_deploy) == 1 && length(aws_eks_access_entry.github_deploy) == 1
    error_message = "Expected a deploy role and EKS access entry when github_repository is set"
  }
}

run "rejects_single_availability_zone" {
  command = plan

  variables {
    az_count = 1
  }

  expect_failures = [var.az_count]
}
