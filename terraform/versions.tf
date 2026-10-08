terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Local state is fine for a single-student lab. For team use, store state remotely
  # with locking - create the bucket first, then uncomment and run `terraform init -migrate-state`:
  #
  # backend "s3" {
  #   bucket       = "stockpilot-tfstate-<your-account-id>"
  #   key          = "eks/terraform.tfstate"
  #   region       = "ap-south-1"
  #   encrypt      = true
  #   use_lockfile = true
  # }
}
