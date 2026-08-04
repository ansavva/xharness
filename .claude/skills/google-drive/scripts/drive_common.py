"""
drive_common.py — shared Google Drive helpers for the `google-drive` skill.

A general Drive API layer (not tied to any one skill): the `drive_auth.py`,
`drive_upload.py`, and `drive_download.py` entry scripts use it to move file
bytes disk<->Drive **directly**, so nothing is base64-inlined into the agent
context (the way the Drive MCP would). A credential comes from `.env`. Other
skills (e.g. the (now S3-based) video, which store reference images and generated
videos in Drive rather than git) call these scripts by path.

Authentication (resolved in this order):
  1. GOOGLE_DRIVE_ACCESS_TOKEN — a ready OAuth access token (handy for quick
     tests; expires in ~1h).
  2. GOOGLE_DRIVE_CLIENT_ID + GOOGLE_DRIVE_CLIENT_SECRET +
     GOOGLE_DRIVE_REFRESH_TOKEN — a user OAuth "installed app" credential. The
     refresh token is exchanged for a short-lived access token on each run.
     This writes into the *user's own* My Drive, which is what we want for
     "a folder in Google Drive".

All names are read from the environment or a `.env` file (searched from the
current directory upward, or an explicit --env PATH), same as
upload_to_replicate.py.

Only the entry scripts carry PEP 723 metadata; their single declared dep
(`requests`) is available here because this module is imported during the run.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
DRIVE_API = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
FOLDER_MIME = "application/vnd.google-apps.folder"

# Env var names (documented in .env.example).
ACCESS_TOKEN = "GOOGLE_DRIVE_ACCESS_TOKEN"
CLIENT_ID = "GOOGLE_DRIVE_CLIENT_ID"
CLIENT_SECRET = "GOOGLE_DRIVE_CLIENT_SECRET"
REFRESH_TOKEN = "GOOGLE_DRIVE_REFRESH_TOKEN"
ROOT_FOLDER = "GOOGLE_DRIVE_ROOT_FOLDER"  # optional; default "xharness"

DEFAULT_ROOT = "xharness"


class DriveError(SystemExit):
    """Raised (as SystemExit) with a clear, actionable message."""


def _read_env_file(env_path: Path | None) -> dict[str, str]:
    """Parse KEY=VALUE lines from a .env file (searched upward if not given)."""
    candidates: list[Path] = [env_path] if env_path else []
    if not env_path:
        d = Path.cwd()
        for parent in [d, *d.parents]:
            candidates.append(parent / ".env")
    values: dict[str, str] = {}
    for c in candidates:
        if c and c.is_file():
            for line in c.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in values:
                    values[key] = val
            break  # first .env found wins
    return values


def _resolve(name: str, env_file: dict[str, str]) -> str | None:
    val = os.environ.get(name)
    if val:
        return val.strip()
    val = env_file.get(name)
    return val.strip() if val else None


def get_root_name(env_path: Path | None = None) -> str:
    env_file = _read_env_file(env_path)
    return _resolve(ROOT_FOLDER, env_file) or DEFAULT_ROOT


def get_access_token(env_path: Path | None = None) -> str:
    """Return a usable Bearer access token, refreshing if necessary."""
    env_file = _read_env_file(env_path)

    direct = _resolve(ACCESS_TOKEN, env_file)
    if direct:
        return direct

    client_id = _resolve(CLIENT_ID, env_file)
    client_secret = _resolve(CLIENT_SECRET, env_file)
    refresh_token = _resolve(REFRESH_TOKEN, env_file)
    if client_id and client_secret and refresh_token:
        resp = requests.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=60,
        )
        if resp.status_code >= 300:
            raise DriveError(
                f"error: Google token refresh failed: {resp.status_code} "
                f"{resp.text[:300]}"
            )
        token = resp.json().get("access_token")
        if not token:
            raise DriveError(f"error: no access_token in token response: {resp.text[:200]}")
        return token

    raise DriveError(
        "error: no Google Drive credential found. Set one in the environment or "
        "a .env file (copy .env.example):\n"
        f"  - {ACCESS_TOKEN} (a ready OAuth access token), or\n"
        f"  - {CLIENT_ID} + {CLIENT_SECRET} + {REFRESH_TOKEN} (recommended).\n"
        "See .env.example for how to obtain a refresh token."
    )


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _escape(name: str) -> str:
    return name.replace("\\", "\\\\").replace("'", "\\'")


def find_child(token: str, name: str, parent_id: str, *, folder: bool | None = None) -> str | None:
    """Return the id of a non-trashed child named `name` under `parent_id`, or None."""
    q = f"name = '{_escape(name)}' and '{parent_id}' in parents and trashed = false"
    if folder is True:
        q += f" and mimeType = '{FOLDER_MIME}'"
    elif folder is False:
        q += f" and mimeType != '{FOLDER_MIME}'"
    resp = requests.get(
        f"{DRIVE_API}/files",
        headers=_auth_headers(token),
        params={"q": q, "fields": "files(id,name)", "pageSize": 1,
                "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"},
        timeout=60,
    )
    if resp.status_code >= 300:
        raise DriveError(f"error: Drive search failed: {resp.status_code} {resp.text[:200]}")
    files = resp.json().get("files", [])
    return files[0]["id"] if files else None


def create_folder(token: str, name: str, parent_id: str) -> str:
    resp = requests.post(
        f"{DRIVE_API}/files",
        headers={**_auth_headers(token), "Content-Type": "application/json"},
        params={"fields": "id", "supportsAllDrives": "true"},
        json={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
        timeout=60,
    )
    if resp.status_code >= 300:
        raise DriveError(f"error: creating folder '{name}' failed: {resp.status_code} {resp.text[:200]}")
    return resp.json()["id"]


def resolve_folder_path(token: str, path: str, *, create: bool, root: str | None = None) -> str:
    """
    Resolve a slash-separated folder path (e.g. "fred/images") under the
    configured root folder (default "xharness") in My Drive. With create=True,
    missing folders are created; otherwise a missing folder is an error.

    Returns the folder id of the final path segment. An empty path returns the
    root folder id itself.
    """
    root_name = root or DEFAULT_ROOT
    segments = [root_name, *[s for s in path.split("/") if s]]
    parent = "root"
    walked: list[str] = []
    for seg in segments:
        walked.append(seg)
        child = find_child(token, seg, parent, folder=True)
        if child is None:
            if not create:
                raise DriveError(
                    f"error: Drive folder '{'/'.join(walked)}' not found. "
                    "Upload something there first, or check GOOGLE_DRIVE_ROOT_FOLDER."
                )
            child = create_folder(token, seg, parent)
        parent = child
    return parent


def upload_file(token: str, local_path: Path, folder_id: str, *, name: str | None = None) -> dict:
    """
    Multipart-upload a local file into `folder_id`. If a file with the same
    name already exists in the folder, it is updated in place (new version)
    rather than duplicated. Returns the file resource (id, name, webViewLink).
    """
    name = name or local_path.name
    existing = find_child(token, name, folder_id, folder=False)

    metadata = {"name": name}
    fields = "id,name,mimeType,size,webViewLink,webContentLink"
    with local_path.open("rb") as fh:
        files = {
            "metadata": ("metadata", _json_bytes(metadata), "application/json"),
            "file": (name, fh, _guess_mime(local_path)),
        }
        if existing:
            # Update contents of the existing file (PATCH, no parents change).
            resp = requests.patch(
                f"{DRIVE_UPLOAD_API}/files/{existing}",
                headers=_auth_headers(token),
                params={"uploadType": "multipart", "fields": fields, "supportsAllDrives": "true"},
                files=files,
                timeout=600,
            )
        else:
            metadata["parents"] = [folder_id]
            files["metadata"] = ("metadata", _json_bytes(metadata), "application/json")
            resp = requests.post(
                f"{DRIVE_UPLOAD_API}/files",
                headers=_auth_headers(token),
                params={"uploadType": "multipart", "fields": fields, "supportsAllDrives": "true"},
                files=files,
                timeout=600,
            )
    if resp.status_code >= 300:
        raise DriveError(f"error: upload of {name} failed: {resp.status_code} {resp.text[:300]}")
    return resp.json()


def list_folder(token: str, folder_id: str, *, folders_only: bool = False,
                files_only: bool = False) -> list[dict]:
    q = f"'{folder_id}' in parents and trashed = false"
    if folders_only:
        q += f" and mimeType = '{FOLDER_MIME}'"
    elif files_only:
        q += f" and mimeType != '{FOLDER_MIME}'"
    out: list[dict] = []
    page_token: str | None = None
    while True:
        params = {"q": q, "fields": "nextPageToken,files(id,name,mimeType,size)",
                  "pageSize": 200, "supportsAllDrives": "true",
                  "includeItemsFromAllDrives": "true", "orderBy": "name"}
        if page_token:
            params["pageToken"] = page_token
        resp = requests.get(f"{DRIVE_API}/files", headers=_auth_headers(token),
                            params=params, timeout=60)
        if resp.status_code >= 300:
            raise DriveError(f"error: listing folder failed: {resp.status_code} {resp.text[:200]}")
        body = resp.json()
        out.extend(body.get("files", []))
        page_token = body.get("nextPageToken")
        if not page_token:
            return out


def download_file(token: str, file_id: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(
        f"{DRIVE_API}/files/{file_id}",
        headers=_auth_headers(token),
        params={"alt": "media", "supportsAllDrives": "true"},
        stream=True,
        timeout=600,
    )
    if resp.status_code >= 300:
        raise DriveError(f"error: download of {file_id} failed: {resp.status_code} {resp.text[:200]}")
    with dest.open("wb") as fh:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            if chunk:
                fh.write(chunk)


def _json_bytes(obj: dict) -> bytes:
    import json

    return json.dumps(obj).encode("utf-8")


def _guess_mime(path: Path) -> str:
    import mimetypes

    mime, _ = mimetypes.guess_type(path.name)
    if mime:
        return mime
    # webp isn't always registered; and default to a safe binary type.
    ext = path.suffix.lower()
    return {".webp": "image/webp", ".mp4": "video/mp4"}.get(ext, "application/octet-stream")
