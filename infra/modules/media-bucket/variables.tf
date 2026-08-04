variable "bucket_name" {
  description = "Globally-unique S3 bucket name that hosts the media assets."
  type        = string
}

variable "media_prefix" {
  description = "Top-level key prefix under which all inputs/outputs live. Mirrors the Google Drive root; keep the trailing slash."
  type        = string
  default     = "media/"

  validation {
    condition     = endswith(var.media_prefix, "/")
    error_message = "media_prefix must end with a trailing slash (e.g. \"media/\")."
  }
}

variable "versioning_enabled" {
  description = "Keep prior revisions of same-named objects (mirrors Drive's update-in-place-with-history behaviour)."
  type        = bool
  default     = true
}

variable "seed_prefixes" {
  description = <<-EOT
    Sub-folders to pre-create under media_prefix as zero-byte folder markers so the
    structure is visible in the console before anything is uploaded. Mirrors the
    Google Drive layout (<character>/{reference,originals,output}/ and misc/output/).
    New prefixes are created automatically on first upload; this list is just a seed.
  EOT
  type        = list(string)
  default = [
    "fred/reference/",
    "fred/originals/",
    "fred/output/",
    "misc/output/",
  ]
}

variable "tags" {
  description = "Tags applied to the bucket."
  type        = map(string)
  default     = {}
}
