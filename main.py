import os
import sys
import json
import shutil
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
    return {"past_topics": [], "pending_part_2": null}


def save_state(state_file: str, state: dict):
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def main():
    print("=" * 60)
    print("🚀 STARTING AI VIDEO GENERATION & PUBLISHING PIPELINE")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    state_file = os.path.join(base_dir, "state.json")
    work_dir = os.path.join(base_dir, "temp_workspace")
    os.makedirs(work_dir, exist_ok=True)

    # 1. API Keys and Credentials
    gemini_key = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6I04_L_V15FCx_ja18_-KvLZ0jbJDmmW8pI9hJcn2fRBA")
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "58207319-b9e3d9a735144933718a8ea91")
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
    n8n_webhook = os.environ.get("N8N_WEBHOOK_URL", "")
    public_video_url = os.environ.get("PUBLIC_VIDEO_URL", "")

    # 2. Check Queue & Topic State
    state = load_state(state_file)
    pending_p2 = state.get("pending_part_2")

    if pending_p2 and pending_p2.get("voiceover_script"):
        print("\n[STEP 1] Found Pending PART 2 in Queue!")
        active_video = pending_p2
        topic = active_video.get("topic", "Mystery Finale")
        part = 2
        badge = "PART 2 (FINALE)"
        state["pending_part_2"] = None  # Consumed
    else:
        print("\n[STEP 1] Generating Fresh 2-Part Story via Gemini Flash Lite...")
        story = generate_story(gemini_key, state.get("past_topics", []))
        topic = story.get("topic", "Unsolved Mystery")
        part = 1
        badge = "PART 1 OF 2"
        active_video = story.get("part1", {})

        # Queue Part 2 for the next scheduled run
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
    print(f"  Script Word Count: {len(script.split())} words")

    # 3. Generate Unlimited Voiceover & Subtitles (Edge-TTS)
    print("\n[STEP 2] Synthesizing Neural Speech (Edge-TTS)...")
    audio_path = os.path.join(work_dir, "voiceover.mp3")
    srt_path = os.path.join(work_dir, "subtitles.srt")
    ass_path = os.path.join(work_dir, "subtitles.ass")

    generate_voiceover(script, audio_path, srt_path, voice="en-US-ChristopherNeural")
    srt_to_ass(srt_path, ass_path)
    print("  Speech and ASS subtitles generated successfully.")

    # 4. Fetch Dynamic B-Roll Clips (Pixabay)
    print("\n[STEP 3] Fetching Vertical Clips from Pixabay...")
    clips_dir = os.path.join(work_dir, "clips")
    clips = fetch_pixabay_clips(keywords, pixabay_key, clips_dir, target_count=7)
    print(f"  Fetched {len(clips)} vertical video clips.")

    # 5. Render Finished Video (FFmpeg)
    print("\n[STEP 4] Rendering Video with FFmpeg (Audio + Badge + Subtitles)...")
    output_video = os.path.join(base_dir, "final_reel.mp4")
    render_video(clips, audio_path, ass_path, badge, output_video)
    file_size_mb = os.path.getsize(output_video) / (1024 * 1024)
    print(f"  Render complete! Output: {output_video} ({file_size_mb:.2f} MB)")

    # 6. Publishing Across Platforms
    print("\n[STEP 5] Publishing Video to Social Platforms...")

    # Facebook Page Reels (Direct binary upload)
    if fb_page_id and fb_token:
        try:
            print("  Uploading directly to Facebook Page Reels...")
            fb_res = post_to_facebook_reels(fb_page_id, fb_token, output_video, title, description)
            print("  Facebook Reels Result:", fb_res)
        except Exception as e:
            print(f"  Facebook Upload Error: {e}")

    # Instagram Reels (If public video URL is provided)
    if public_video_url and ig_user_id and ig_token:
        try:
            print("  Uploading to Instagram Reels...")
            ig_res = post_to_instagram_reels(ig_user_id, ig_token, public_video_url, title, description)
            print("  Instagram Reels Result:", ig_res)
        except Exception as e:
            print(f"  Instagram Upload Error: {e}")

    # n8n Webhook Notification (For YouTube Shorts and Instagram)
    if n8n_webhook:
        try:
            print("  Notifying n8n Webhook for YouTube Shorts upload...")
            payload = {
                "video_url": public_video_url,
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

    # 7. Update and Save State
    save_state(state_file, state)
    print("\n[STEP 6] State successfully updated in state.json!")
    if part == 1:
        print("  Part 2 is now queued for the next scheduled run.")
    else:
        print("  Part 2 completed. The next run will start a brand new topic.")

    # Clean up temp files
    try:
        shutil.rmtree(work_dir)
    except Exception:
        pass

    print("\n" + "=" * 60)
    print("🎉 EXECUTION COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
