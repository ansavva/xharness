terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # When null, the AWS SDK's default resolution is used (env vars, AWS_PROFILE,
  # SSO, instance role). apply.sh sets AWS_PROFILE, so this can stay null.
  profile = var.aws_profile

  default_tags {
    tags = {
      project   = "xharness"
      component = "seedance-media"
      managedby = "terraform"
    }
  }
}

module "media_bucket" {
  source = "./modules/media-bucket"

  bucket_name        = var.bucket_name
  media_prefix       = var.media_prefix
  versioning_enabled = var.versioning_enabled
}
