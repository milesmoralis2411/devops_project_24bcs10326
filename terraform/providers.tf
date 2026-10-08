# Credentials come from the standard AWS chain (aws configure / AWS_PROFILE /
# environment variables) - never from this repository.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.tags
  }
}
