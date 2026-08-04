output "bucket_name" {
  description = "Name of the created bucket."
  value       = module.media_bucket.bucket_name
}

output "bucket_arn" {
  description = "ARN of the created bucket."
  value       = module.media_bucket.bucket_arn
}

output "media_uri" {
  description = "s3:// URI for the media root."
  value       = module.media_bucket.media_uri
}

output "region" {
  description = "Region the bucket lives in."
  value       = var.aws_region
}
