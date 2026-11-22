"""TikTok Content Posting API v2 (Inbox/Drafts) client and refresh-token rotation."""

import base64
import os
from pathlib import Path

import requests
from nacl.public import PublicKey, SealedBox

API_BASE = "https://open.tiktokapis.com"
CHUNK_SIZE = 10 * 1024 * 1024


def _required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _update_github_secret(secret_name, secret_value):
    repository = _required("GITHUB_REPOSITORY")
    token = _required("GH_PAT")
    api_root = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"{api_root}/repos/{repository}/actions/secrets"
    response = requests.get(f"{url}/public-key", headers=headers, timeout=30)
    response.raise_for_status()
    public_key = response.json()
    sealed = SealedBox(PublicKey(base64.b64decode(public_key["key"]))).encrypt(secret_value.encode())
    response = requests.put(
        f"{url}/{secret_name}",
        headers=headers,
        json={"encrypted_value": base64.b64encode(sealed).decode(), "key_id": public_key["key_id"]},
        timeout=30,
    )
    response.raise_for_status()


def refresh_access_token():
    response = requests.post(
        f"{API_BASE}/v2/oauth/token/",
        data={
            "client_key": _required("TIKTOK_CLIENT_KEY"),
            "client_secret": _required("TIKTOK_CLIENT_SECRET"),
            "grant_type": "refresh_token",
            "refresh_token": _required("TIKTOK_REFRESH_TOKEN"),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    payload = response.json()
    result = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    access_token = result.get("access_token")
    if not access_token:
        raise RuntimeError(f"TikTok token refresh failed: {payload}")
    rotated_refresh_token = result.get("refresh_token")
    if rotated_refresh_token:
        _update_github_secret("TIKTOK_REFRESH_TOKEN", rotated_refresh_token)
    return access_token


def publish_video(video_path, caption):
    access_token = refresh_access_token()
    video_path = Path(video_path)
    size = video_path.stat().st_size
    if size <= 0:
        raise ValueError("Video file is empty")
    chunk_size = min(CHUNK_SIZE, size)
    chunks = (size + chunk_size - 1) // chunk_size
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    response = requests.post(
        f"{API_BASE}/v2/post/publish/inbox/video/init/",
        headers=headers,
        json={
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": chunk_size,
                "total_chunk_count": chunks,
            },
        },
        timeout=30,
    )
    init_payload = response.json()
    if not response.ok:
        raise RuntimeError(f"TikTok inbox init failed ({response.status_code}): {init_payload}")
    data = init_payload.get("data", {})
    upload_url = data.get("upload_url")
    publish_id = data.get("publish_id")
    if not upload_url or not publish_id:
        raise RuntimeError(f"TikTok did not return upload_url/publish_id: {init_payload}")

    with video_path.open("rb") as file:
        for index in range(chunks):
            chunk = file.read(chunk_size)
            start = index * chunk_size
            end = start + len(chunk) - 1
            upload_response = requests.put(
                upload_url,
                data=chunk,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end}/{size}",
                },
                timeout=120,
            )
            upload_response.raise_for_status()
    return publish_id
