terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# The asset bucket. Private by default — hand objects to Replicate/Seedance via
# short-lived presigned URLs (see infra/README.md), not by making the bucket public.
resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
  tags   = var.tags
}

# Disable ACLs — the account that owns the bucket owns every object (modern default).
resource "aws_s3_bucket_ownership_controls" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Block all public access. Presigned URLs still work with this on.
resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = var.versioning_enabled ? "Enabled" : "Suspended"
  }
}

# Server-side encryption at rest (SSE-S3 / AES256 — free, always-on).
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# media/ root marker + the seeded sub-folders, so the Drive-mirroring structure
# is visible in the console immediately. Uploads create any other prefixes on demand.
resource "aws_s3_object" "folders" {
  for_each = toset(concat([var.media_prefix], [for p in var.seed_prefixes : "${var.media_prefix}${p}"]))

  bucket       = aws_s3_bucket.this.id
  key          = each.value
  content      = ""
  content_type = "application/x-directory"

  # Folder markers are cosmetic — don't churn them if content ever drifts.
  lifecycle {
    ignore_changes = [content]
  }

  depends_on = [aws_s3_bucket_ownership_controls.this]
}
