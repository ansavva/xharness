#!/usr/bin/env bash
#
# apply.sh — provision the xharness-assets S3 bucket with Terraform.
#
# Runs `terraform init` + `apply` against a named AWS profile. Idempotent:
# re-running reconciles the bucket to the config, it does not recreate it.
#
# Usage:
#   ./apply.sh                      # profile "default", region us-east-1
#   ./apply.sh -p myprofile         # a specific AWS profile
#   ./apply.sh -p prod -r us-west-2 # profile + region
#   ./apply.sh --plan               # dry run (terraform plan, no changes)
#   ./apply.sh --destroy            # tear the bucket down (must be empty)
#
set -euo pipefail

cd "$(dirname "$0")"

AWS_PROFILE_ARG="${AWS_PROFILE:-default}"
AWS_REGION_ARG="${AWS_REGION:-us-east-1}"
ACTION="apply"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--profile) AWS_PROFILE_ARG="$2"; shift 2 ;;
    -r|--region)  AWS_REGION_ARG="$2";  shift 2 ;;
    --plan)       ACTION="plan";        shift   ;;
    --destroy)    ACTION="destroy";     shift   ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

command -v terraform >/dev/null || { echo "terraform not found — install it (brew install terraform)"; exit 1; }
command -v aws        >/dev/null || { echo "aws CLI not found — install it (brew install awscli)"; exit 1; }

export AWS_PROFILE="$AWS_PROFILE_ARG"
export AWS_REGION="$AWS_REGION_ARG"

echo "==> profile : $AWS_PROFILE"
echo "==> region  : $AWS_REGION"

# Fail early with a readable message if the profile has no valid creds.
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "ERROR: AWS profile '$AWS_PROFILE' has no valid credentials." >&2
  echo "       Run 'aws login', 'aws configure --profile $AWS_PROFILE', or 'aws sso login --profile $AWS_PROFILE' first." >&2
  exit 1
fi
echo "==> account : $(aws sts get-caller-identity --query Account --output text)"

# Bridge the CLI's credential resolution to Terraform's SDK. The CLI understands
# `aws login` (login_session), SSO, and credential_process; the Terraform AWS
# provider does not. Resolve them to plain AWS_ACCESS_KEY_ID/SECRET/SESSION_TOKEN
# env vars that the provider reads directly. Then drop AWS_PROFILE so the provider
# uses these explicit creds instead of re-resolving the (SDK-unreadable) profile.
echo "==> resolving credentials for Terraform"
if creds="$(aws configure export-credentials --format env 2>/dev/null)"; then
  eval "$creds"
  unset AWS_PROFILE
else
  echo "WARN: 'aws configure export-credentials' unavailable; relying on AWS_PROFILE." >&2
  echo "      (Needs AWS CLI v2. If Terraform then reports 'No valid credential sources', upgrade the CLI.)" >&2
fi

terraform init -input=false

case "$ACTION" in
  plan)
    terraform plan -input=false -var "aws_region=$AWS_REGION"
    ;;
  apply)
    terraform apply -input=false -auto-approve -var "aws_region=$AWS_REGION"
    echo
    echo "Done. Media root:"
    terraform output -raw media_uri
    echo
    ;;
  destroy)
    echo "This deletes the bucket. It must be empty first (versioned objects included)."
    terraform destroy -input=false -var "aws_region=$AWS_REGION"
    ;;
esac
