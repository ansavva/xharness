variable "aws_region" {
  description = "AWS region for the bucket."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Named AWS profile to use. Leave null to rely on AWS_PROFILE / default credential resolution (apply.sh sets this)."
  type        = string
  default     = null
}

variable "bucket_name" {
  description = "Globally-unique S3 bucket name."
  type        = string
  default     = "xharness-assets"
}

variable "media_prefix" {
  description = "Top-level key prefix all media inputs/outputs live under (mirrors the Drive root)."
  type        = string
  default     = "media/"
}

variable "versioning_enabled" {
  description = "Keep prior revisions of same-named objects."
  type        = bool
  default     = true
}
