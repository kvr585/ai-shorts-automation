import os
import time
import requests


def post_to_facebook_reels(page_id: str, page_token: str, video_path: str, title: str, description: str) -> dict:
    """
    Directly uploads a local MP4 file to Facebook Page Reels via the Graph API
    using a 3-phase resumable upload.
    """
    caption = f"{title}\n\n{description}"
    file_size = os.path.getsize(video_path)

    # Phase 1: Initialize session
    init_res = requests.post(
        f"https://graph.facebook.com/v21.0/{page_id}/video_reels",
        json={"upload_phase": "start", "access_token": page_token},
        timeout=30
    ).json()

    video_id = init_res.get("video_id")
    upload_url = init_res.get("upload_url")
    if not video_id or not upload_url:
        raise RuntimeError(f"Failed to start Facebook upload session: {init_res}")

    # Phase 2: Upload binary bytes
    with open(video_path, "rb") as f:
        file_bytes = f.read()

    upload_headers = {
        "Authorization": f"OAuth {page_token}",
        "offset": "0",
        "file_size": str(file_size)
    }
    upload_res = requests.post(upload_url, headers=upload_headers, data=file_bytes, timeout=120).json()
    if not upload_res.get("success"):
        raise RuntimeError(f"Failed to transfer Facebook video bytes: {upload_res}")

    # Phase 3: Publish Reel
    finish_res = requests.post(
        f"https://graph.facebook.com/v21.0/{page_id}/video_reels",
        json={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
            "access_token": page_token
        },
        timeout=30
    ).json()

    if "error" in finish_res:
        raise RuntimeError(f"Facebook publish failed: {finish_res['error'].get('message', finish_res['error'])}")

    return {
        "platform": "Facebook Reels",
        "success": finish_res.get("success", False),
        "post_id": finish_res.get("post_id") or finish_res.get("id"),
        "video_id": video_id
    }


def post_to_instagram_reels(ig_user_id: str, ig_token: str, video_url: str, title: str, description: str) -> dict:
    """
    Publishes a video to Instagram Reels via the Instagram Graph API.
    Requires a public video URL (e.g. from GitHub Releases or temporary host).
    """
    caption = f"{title}\n\n{description}"

    # Step 1: Create media container
    create_url = f"https://graph.instagram.com/v21.0/{ig_user_id}/media"
    res = requests.post(
        create_url,
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": ig_token
        },
        timeout=30
    ).json()

    creation_id = res.get("id")
    if not creation_id:
        raise RuntimeError(f"Failed to create Instagram container: {res}")

    # Step 2: Poll container status with network retry
    status_url = f"https://graph.instagram.com/v21.0/{creation_id}"
    status_code = None
    for _ in range(30):
        time.sleep(5)
        try:
            status_res = requests.get(
                status_url,
                params={"fields": "status_code", "access_token": ig_token},
                timeout=15
            ).json()
            status_code = status_res.get("status_code")
            if status_code == "FINISHED":
                break
            elif status_code == "ERROR":
                raise RuntimeError(f"Instagram media processing failed: {status_res}")
        except requests.exceptions.RequestException as req_err:
            print(f"  [Instagram] Polling network warning: {req_err}, retrying...")
            continue

    if status_code != "FINISHED":
        raise RuntimeError(f"Instagram container did not reach FINISHED status in time (last status: {status_code})")

    # Step 3: Publish container
    publish_url = f"https://graph.instagram.com/v21.0/{ig_user_id}/media_publish"
    pub_res = requests.post(
        publish_url,
        params={"creation_id": creation_id, "access_token": ig_token},
        timeout=30
    ).json()

    if "error" in pub_res:
        raise RuntimeError(f"Instagram publish failed: {pub_res['error'].get('message', pub_res['error'])}")

    return {
        "platform": "Instagram Reels",
        "success": bool(pub_res.get("id")),
        "media_id": pub_res.get("id")
    }
