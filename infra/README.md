# infra — Terraform

Provisions AWS infrastructure for xharness. Currently: the **`xharness-assets`**
S3 bucket that hosts the Seedance video-generation media (reference images in,
generated videos out) — replacing Google Drive as the asset store.

## Layout

```
infra/
├── main.tf / variables.tf / outputs.tf   — root config (instantiates the module)
├── apply.sh                              — wrapper: init + apply against an AWS profile
└── modules/
    └── media-bucket/                     — reusable S3 asset-bucket module
        ├── main.tf variables.tf outputs.tf
```

## What it creates

- S3 bucket **`xharness-assets`** (`var.bucket_name`), region `us-east-1` by default.
- **Private** — all public access blocked, ACLs disabled (BucketOwnerEnforced).
- **Versioned** — re-uploading a same-named object keeps the prior revision
  (mirrors Drive's update-in-place-with-history).
- **Encrypted** at rest (SSE-S3 / AES256).
- A **`media/`** key prefix with the Drive-mirroring structure seeded as empty
  folder markers.

## The `media/` layout

`media/` is the bucket root for all assets and mirrors the Google Drive layout
1:1 — the Drive root folder `xharness/` becomes the `media/` prefix, same
sub-paths, **same file names**:

```
Google Drive                     S3
xharness/<name>/reference/<name>_1.webp   →  s3://xharness-assets/media/<name>/reference/<name>_1.webp
xharness/<name>/originals/<name>_1.webp   →  s3://xharness-assets/media/<name>/originals/<name>_1.webp
xharness/<name>/output/<clip>.mp4       →  s3://xharness-assets/media/<name>/output/<clip>.mp4
xharness/misc/output/<clip>.mp4       →  s3://xharness-assets/media/misc/output/<clip>.mp4
```

New characters/prefixes are created automatically on first upload; the seeded
markers just make the structure visible in the console immediately. Adjust the
seed list via `seed_prefixes` in `modules/media-bucket/variables.tf`.

## Run it

```bash
cd infra
./apply.sh                 # profile "default", region us-east-1
./apply.sh -p myprofile    # a specific AWS profile
./apply.sh --plan          # dry run, no changes
./apply.sh --destroy       # tear down (bucket must be empty first)
```

The script checks credentials with `aws sts get-caller-identity` before doing
anything, then runs `terraform init` + `apply`. State is stored **locally**
(`terraform.tfstate`, git-ignored) — fine for a single personal bucket.

## Handing objects to Replicate / Seedance

The bucket is **private**; do not make it public. Give Replicate a **presigned
URL** (short-lived, no credentials leak) — it just needs a fetchable HTTPS URL
for the duration of the job:

```bash
# reference image → temporary HTTPS URL Replicate can fetch (1 h)
aws s3 presign s3://xharness-assets/media/<name>/reference/<name>_1.webp --expires-in 3600

# upload a local file into the media tree
aws s3 cp ./<name>_1.webp s3://xharness-assets/media/<name>/reference/<name>_1.webp

# download a generated video back out
aws s3 cp s3://xharness-assets/media/<name>/output/clip.mp4 ./clip.mp4
```
