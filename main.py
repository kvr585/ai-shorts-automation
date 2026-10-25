import os
import sys
import json
import shutil
import argparse
from video_engine import (
    generate_story,
    generate_voiceover,
    srt_to_ass,
    fetch_pixabay_clips,
    render_video
)
from uploader import (
    post_to_facebook_reels,
    post_to_instagram_reels,
    notify_n8n_webhook
)


def load_state(state_file: str) -> dict:
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"past_topics": [], "pending_part_2": None}


def save_state(state_file: str, state: dict):
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def render_phase(base_dir: str):
    print("=" * 60)
    print("🚀 PHASE 1: GENERATING & RENDERING VIDEO (EDGE-TTS + FFMPEG)")
    print("=" * 60)

    state_file = os.path.join(base_dir, "state.json")
    work_dir = os.path.join(base_dir, "temp_workspace")
    meta_file = os.path.join(base_dir, "metadata.json")
    os.makedirs(work_dir, exist_ok=True)

    gemini_key = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6I04_L_V15FCx_ja18_-KvLZ0jbJDmmW8pI9hJcn2fRBA")
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "58207319-b9e3d9a735144933718a8ea91")

    state = load_state(state_file)
    pending_p2 = state.get("pending_part_2")

    if pending_p2 and pending_p2.get("voiceover_script"):
        print("\n[STEP 1] Found Pending PART 2 in Queue!")
        active_video = pending_p2
        topic = active_video.get("topic", "Mystery Finale")
        part = 2
        badge = "PART 2 (FINALE)"
        state["pending_part_2"] = None  # Mark consumed
    else:
        print("\n[STEP 1] Generating Fresh 2-Part Story via Gemini Flash Lite...")
        story = generate_story(gemini_key, state.get("past_topics", []))
        topic = story.get("topic", "Unsolved Mystery")
        part = 1
        badge = "PART 1 OF 2"
        active_video = story.get("part1", {})

        p2_data = story.get("part2", {})
        p2_data["topic"] = topic
        state["pending_part_2"] = p2_data
        if topic not in state["past_topics"]:
            state["past_topics"].append(topic)

    title = active_video.get("title", f"The Shocking Truth About {topic} #shorts")
    description = active_video.get("description", f"Uncovering {topic}. #shorts #viral #mystery")
    script = active_video.get("voiceover_script", "")
    keywords = active_video.get("scene_keywords", ["mystery", "ocean", "dark night"])

    print(f"  Topic: {topic}")
    print(f"  Episode: {badge}")
    print(f"  Title: {title}")
    print(f"  Script Length: {len(script.split())} words")

    # 1. Edge-TTS Audio & Subtitles
    print("\n[STEP 2] Synthesizing Neural Voiceover (Edge-TTS)...")
    audio_path = os.path.join(work_dir, "voiceover.mp3")
    srt_path = os.path.join(work_dir, "subtitles.srt")
    ass_path = os.path.join(work_dir, "subtitles.ass")

    generate_voiceover(script, audio_path, srt_path, voice="en-US-ChristopherNeural")
    srt_to_ass(srt_path, ass_path)

    # 2. Pixabay B-Roll
    print("\n[STEP 3] Downloading Pixabay Vertical Clips...")
    clips_dir = os.path.join(work_dir, "clips")
    clips = fetch_pixabay_clips(keywords, pixabay_key, clips_dir, target_count=7)

    # 3. FFmpeg Assembly
    print("\n[STEP 4] Rendering Vertical Video via FFmpeg...")
    output_video = os.path.join(base_dir, "final_reel.mp4")
    render_video(clips, audio_path, ass_path, badge, output_video)
    file_size_mb = os.path.getsize(output_video) / (1024 * 1024)
    print(f"  Render finished: {output_video} ({file_size_mb:.2f} MB)")

    # Save metadata for publishing step
    metadata = {
        "title": title,
        "description": description,
        "topic": topic,
        "part": part,
        "badge": badge
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    save_state(state_file, state)
    print("\n  State updated in state.json.")

    # Cleanup temp workspace
    try:
        shutil.rmtree(work_dir)
    except Exception:
        pass


def publish_phase(base_dir: str, video_url: str):
    print("=" * 60)
    print("🚀 PHASE 2: MULTI-PLATFORM PUBLISHING")
    print("=" * 60)

    meta_file = os.path.join(base_dir, "metadata.json")
    local_video = os.path.join(base_dir, "final_reel.mp4")

    if not os.path.exists(meta_file):
        raise FileNotFoundError(f"Missing {meta_file}")

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    title = meta["title"]
    description = meta["description"]
    topic = meta["topic"]
    part = meta["part"]
    badge = meta["badge"]

    fb_page_id = os.environ.get("FB_PAGE_ID", "1440617492457272")
    fb_token = os.environ.get(
        "FB_PAGE_TOKEN",
        "EAAQQKJgvpssBS32M4feMABMng9AzLuo6mBxDskh1ZBGeI3Itj7SpWqqP7nxW4gZBtSXNxPNR5N8zhBui5kM3oCgNXLTGlYdlw3dAHQvvE3dAJOOrJS80HuzNlNFiXtJbKap9F6Bs2MHcojRXlkBDQhiSCwD9V0XtWqutQ6ZC9Lr4BcWeXxr1996u4sngf2rZCzNl"
    )
    ig_user_id = os.environ.get("IG_USER_ID", "28802795232755143")
    ig_token = os.environ.get(
        "IG_ACCESS_TOKEN",
        "IGAAZAaSgZAv4SpBZAGFkd2pZAXzVqYTZAGYnZANNU5JWlF1VUFyeGVzWndVdnhyQV9rbGVDUWlnSXhHOThEUjctTl9CT25vSXNIMnhFeGNtVTV0RU5pcTMyeGp5X1FMVGZAnMWx1ZAlRiSlBjZAHBkdEt3QzhGZA0pB"
    )
    n8n_webhook = os.environ.get("N8N_WEBHOOK_URL", "https://veerabhadhra.app.n8n.cloud/webhook/publish-rendered-reel")

    # 1. Direct Facebook Page Reels Upload
    if fb_page_id and fb_token and os.path.exists(local_video):
        try:
            print("[1] Uploading to Facebook Page Reels...")
            fb_res = post_to_facebook_reels(fb_page_id, fb_token, local_video, title, description)
            print("  Facebook Reels Result:", fb_res)
        except Exception as e:
            print(f"  Facebook Upload Error: {e}")

    # 2. Direct Instagram Reels Upload
    if video_url and ig_user_id and ig_token:
        try:
            print("\n[2] Uploading to Instagram Reels...")
            ig_res = post_to_instagram_reels(ig_user_id, ig_token, video_url, title, description)
            print("  Instagram Reels Result:", ig_res)
        except Exception as e:
            print(f"  Instagram Upload Error: {e}")

    # 3. Notify n8n Webhook for YouTube Shorts Upload
    if n8n_webhook and video_url:
        try:
            print("\n[3] Triggering n8n Webhook for YouTube Shorts upload...")
            payload = {
                "video_url": video_url,
                "title": title,
                "description": description,
                "topic": topic,
                "part": part,
                "badge": badge
            }
            n8n_res = notify_n8n_webhook(n8n_webhook, payload)
            print("  n8n Webhook Result:", n8n_res)
        except Exception as e:
            print(f"  n8n Webhook Error: {e}")

    print("\n" + "=" * 60)
    print("🎉 PUBLISHING PHASE COMPLETED!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="AI Video Pipeline")
    parser.add_argument("--render-only", action="store_true", help="Only generate and render video")
    parser.add_argument("--publish-only", type=str, help="Publish with provided video URL")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))

    if args.publish_only:
        publish_phase(base_dir, args.publish_only)
    elif args.render_only:
        render_phase(base_dir)
    else:
        render_phase(base_dir)
        video_url = os.environ.get("PUBLIC_VIDEO_URL", "")
        publish_phase(base_dir, video_url)


if __name__ == "__main__":
    main()
