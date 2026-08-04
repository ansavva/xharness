---
name: s3
description: Read from and write to the xharness-assets S3 bucket via the AWS CLI/boto3 — list a prefix, upload local files into the media tree, download files to disk, and mint short-lived presigned HTTPS URLs (how images/videos reach Replicate). The canonical asset store for the studio-* video workflow (replaced Google Drive). Use when a skill or task needs to store, fetch, list, or hand out large media assets (reference images, generated videos) without inlining bytes into the agent context.
---

# S3 skill

The asset layer for xharness. Files move **disk ↔ S3 directly** (never
base64-inlined into the agent context), so it handles full-resolution images and
multi-MB videos cheaply. It replaced the Google Drive layer for the
`studio-*` workflow.

Everything lives in one bucket, **`xharness-assets`**, under a single **`media/`**
key prefix. Paths passed to these scripts are relative *under* `media/`, e.g.
`fred/reference`. The bucket and prefix are provisioned by Terraform in
[`infra/`](../../../infra/README.md).

Bucket / prefix / region are overridable via env: `XHARNESS_S3_BUCKET`
(default `xharness-assets`), `XHARNESS_S3_MEDIA_PREFIX` (default `media/`),
`AWS_REGION` (default `us-east-1`).

## Credentials

No `.env` entry — S3 uses your **AWS CLI login**. Sign in once per session:

```bash
aws login          # or: aws sso login  /  aws configure
```

The scripts resolve whatever the CLI can (the newer `login_session` from
`aws login`, SSO, `credential_process`, or static keys) into boto3 credentials
via `aws configure export-credentials`. This bridge matters because boto3's own
default chain does **not** understand `aws login`. If a script reports it can't
resolve credentials, run `aws login` again (sessions are short-lived).

## The media layout

`media/` mirrors what used to live in Google Drive 1:1 — same sub-paths, same
file names:

```
s3://xharness-assets/media/fred/reference/fred_1.webp … fred_9.webp   # curated set, passed on every generation
s3://xharness-assets/media/fred/originals/fred_1.webp …               # full source archive
s3://xharness-assets/media/fred/output/<clip>.mp4                     # renders
s3://xharness-assets/media/misc/output/<clip>.mp4                     # non-character renders
```

## Scripts

All are `uv` scripts (PEP 723; dependency `boto3`) under
`.claude/skills/s3/scripts/`. `s3_common.py` holds shared auth/helpers and is not
run directly.

| Script | Purpose |
|---|---|
| `s3_upload.py` | Upload local file(s) into `media/<folder>/`. Prints `s3://` URIs; `--presign` also prints HTTPS URLs. |
| `s3_download.py` | List a folder (`--list`), download everything (`--all`) or named files to a dir. |
| `s3_presign.py` | Mint temporary HTTPS GET URLs for objects — **how assets reach Replicate**. |

```bash
S3=.claude/skills/s3/scripts

# List a folder
uv run $S3/s3_download.py --folder fred/reference --list

# Download everything in a folder to a temp dir (JSON map name -> local path)
uv run $S3/s3_download.py --folder fred/reference --all --dest /tmp/refs --json

# Upload files into a folder (created implicitly by the key)
uv run $S3/s3_upload.py --folder fred/output output/fred/clip.mp4

# Presign every reference image, in fred_1..fred_N order, for Replicate
uv run $S3/s3_presign.py --folder fred/reference --json
```

## Handing assets to Replicate / Seedance

The bucket is **private**. To let Replicate fetch an image or video, presign it —
a short-lived (default 1 h) HTTPS URL that carries its own signature. Pass the
resulting URLs straight into a prediction's `reference_images` / `image` inputs.
Only short URLs enter the agent context; the bytes never do. This replaces the
old Drive→local→Replicate-Files-upload dance — no `REPLICATE_API_TOKEN` needed
for references.

## Notes

- Uploads overwrite a same-named key; the bucket is **versioned**, so the prior
  revision is retained (mirrors Drive's update-in-place-with-history).
- `list_prefix` skips zero-byte folder markers and natural-sorts (`fred_2`
  before `fred_10`).
- Provisioning, teardown, and the presigned-URL cheatsheet live in
  [`infra/README.md`](../../../infra/README.md).
