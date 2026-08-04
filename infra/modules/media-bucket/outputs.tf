output "bucket_name" {
  description = "Name (id) of the created bucket."
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "ARN of the created bucket."
  value       = aws_s3_bucket.this.arn
}

output "bucket_domain_name" {
  description = "Regional domain name of the bucket."
  value       = aws_s3_bucket.this.bucket_regional_domain_name
}

output "media_prefix" {
  description = "Root key prefix all inputs/outputs live under."
  value       = var.media_prefix
}

output "media_uri" {
  description = "Convenience s3:// URI for the media root."
  value       = "s3://${aws_s3_bucket.this.id}/${var.media_prefix}"
}
