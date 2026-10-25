import os
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def upload_youtube_short(video_path: str, title: str, description: str, client_id: str, client_secret: str, refresh_token: str) -> dict:
    """
    Uploads a short-form vertical video directly to YouTube Shorts via YouTube Data API v3
    using OAuth2 refresh token authentication.
    """
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": f"{description}\n\n#shorts #viral",
            "tags": ["shorts", "mystery", "viral"],
            "categoryId": "28"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()

    return {
        "platform": "YouTube Shorts",
        "video_id": response.get("id"),
        "url": f"https://youtube.com/shorts/{response.get('id')}",
        "success": bool(response.get("id"))
    }
