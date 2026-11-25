import os
import sys
import json
import time
import shutil
import argparse
from video_engine import (
    generate_story,
    generate_promo_story,
    generate_voiceover,
    srt_to_ass,
    fetch_pixabay_clips,
    render_video
)
from uploader import (
    post_to_facebook_reels,
    post_to_instagram_reels
)
from youtube_uploader import upload_youtube_short


def load_state(state_file: str) -> dict:
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("past_topics", [])
                    data.setdefault("pending_part_2", None)
                    data.setdefault("reel_count", 0)
                    data.setdefault("promo_history", [])
                    data.setdefault("last_promo_angle_idx", -1)
                    return data
        except Exception as e:
            print(f"[WARN] Error loading {state_file}: {e}. Initializing fresh state.")
    return {
        "past_topics": [],
        "pending_part_2": None,
        "reel_count": 0,
        "promo_history": [],
        "last_promo_angle_idx": -1
    }


def save_state(state_file: str, state: dict):
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def render_phase(base_dir: str, force_promo: bool = False):
    print("=" * 60)
    print("🚀 PHASE 1: GENERATING & RENDERING VIDEO (EDGE-TTS + FFMPEG)")
    print("=" * 60)

    state_file = os.path.join(base_dir, "state.json")
    work_dir = os.path.join(base_dir, "temp_workspace")
    meta_file = os.path.join(base_dir, "metadata.json")
    os.makedirs(work_dir, exist_ok=True)

    gemini_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    pixabay_key = os.environ.get("PIXABAY_API_KEY") or "58207319-b9e3d9a735144933718a8ea91"

    state = load_state(state_file)
    current_count = state.get("reel_count", 0)
    pending_p2 = state.get("pending_part_2")

    # Strict 2:1 Cadence Rule:
    # Reel 1, 2 = Standard niche content
    # Reel 3 = PROMO REEL for Virtual Meeting Assistant
    # Reel 4, 5 = Standard niche content
    # Reel 6 = PROMO REEL for Virtual Meeting Assistant
    is_promo = force_promo or (((current_count + 1) % 3 == 0) and not (pending_p2 and pending_p2.get("voiceover_script")))

    if is_promo:
        print(f"\n[STEP 1] Generating PROMO REEL for Virtual Meeting Assistant (2:1 Ratio Cadence | Reel #{current_count + 1})...")
        promo_data = generate_promo_story(
            gemini_key,
            state.get("promo_history", []),
            state.get("last_promo_angle_idx", -1)
        )
        topic = promo_data.get("topic", "Virtual Meeting Assistant")
        part = 0
        badge = promo_data.get("badge", "AI COPILOT")
        active_video = promo_data

        # Update promo tracking
        state["last_promo_angle_idx"] = promo_data.get("angle_idx", 1)
        promo_record = {
            "angle_idx": promo_data.get("angle_idx", 1),
            "angle_name": promo_data.get("angle_name", ""),
            "hook": promo_data.get("hook_text", ""),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        history = state.get("promo_history", [])
        history.append(promo_record)
        state["promo_history"] = history[-6:]
    elif pending_p2 and pending_p2.get("voiceover_script"):
        print(f"\n[STEP 1] Found Pending PART 2 in Queue! (Reel #{current_count + 1})")
        active_video = pending_p2
        topic = active_video.get("topic", "Mystery Finale")
        part = 2
        badge = "PART 2 (FINALE)"
        state["pending_part_2"] = None  # Mark consumed
    else:
        print(f"\n[STEP 1] Generating Fresh 2-Part Story via Gemini Flash Lite (Reel #{current_count + 1})...")
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

    # Increment Reel counter
    new_reel_count = current_count + 1
    state["reel_count"] = new_reel_count

    title = active_video.get("title", f"The Shocking Truth About {topic} #shorts")
    description = active_video.get("description", f"Uncovering {topic}. #shorts #viral #mystery")
    script = active_video.get("voiceover_script", "")
    keywords = active_video.get("scene_keywords", ["technology", "coding", "meeting"])

    print(f"  Reel Count: #{new_reel_count} (Type: {'PROMO' if is_promo else 'STANDARD'})")
    print(f"  Topic: {topic}")
    print(f"  Episode Badge: {badge}")
    print(f"  Title: {title}")
    print(f"  Script Length: {len(script.split())} words")

    # 1. Edge-TTS Audio & Subtitles
    print("\n[STEP 2] Synthesizing Neural Voiceover (Edge-TTS)...")
    audio_path = os.path.join(work_dir, "voiceover.mp3")
    srt_path = os.path.join(work_dir, "subtitles.srt")
    ass_path = os.path.join(work_dir, "subtitles.ass")

    words_count = len(script.split())
    # Promo reels follow 25-40s duration; standard mystery deep-dives follow 48-56s duration
    if is_promo:
        estimated_duration = max(26.0, min(38.0, words_count / 2.4))
    else:
        estimated_duration = max(48.0, min(56.0, words_count / 2.4))

    generate_voiceover(script, audio_path, srt_path, voice="en-US-ChristopherNeural")
    srt_to_ass(srt_path, ass_path, badge_text=badge, duration_sec=estimated_duration)

    # 2. Pixabay B-Roll
    target_clips = 12 if is_promo else 15
    print(f"\n[STEP 3] Downloading Pixabay Vertical Clips ({target_clips} Clips for Fast Pacing)...")
    clips_dir = os.path.join(work_dir, "clips")
    clips = fetch_pixabay_clips(keywords, pixabay_key, clips_dir, target_count=target_clips)

    # 3. FFmpeg Assembly
    print("\n[STEP 4] Rendering Vertical Video via FFmpeg...")
    output_video = os.path.join(base_dir, "final_reel.mp4")
    render_video(clips, audio_path, ass_path, output_video, script_words=words_count)
    file_size_mb = os.path.getsize(output_video) / (1024 * 1024)
    print(f"  Render finished: {output_video} ({file_size_mb:.2f} MB)")

    # Save metadata for publishing step
    metadata = {
        "title": title,
        "description": description,
        "topic": topic,
        "part": part,
        "badge": badge,
        "is_promo": is_promo,
        "reel_count": new_reel_count,
        "pinned_comment": active_video.get("pinned_comment", "")
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    save_state(state_file, state)
    print(f"\n  State updated in state.json (REEL_COUNT = {new_reel_count}).")

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

    fb_page_id = os.environ.get("FB_PAGE_ID") or "1440617492457272"
    fb_token = os.environ.get(
        "FB_PAGE_TOKEN"
    ) or "EAAQQKJgvpssBS32M4feMABMng9AzLuo6mBxDskh1ZBGeI3Itj7SpWqqP7nxW4gZBtSXNxPNR5N8zhBui5kM3oCgNXLTGlYdlw3dAHQvvE3dAJOOrJS80HuzNlNFiXtJbKap9F6Bs2MHcojRXlkBDQhiSCwD9V0XtWqutQ6ZC9Lr4BcWeXxr1996u4sngf2rZCzNl"
    ig_user_id = os.environ.get("IG_USER_ID") or "28802795232755143"
    ig_token = os.environ.get(
        "IG_ACCESS_TOKEN"
    ) or "IGAAZAaSgZAv4SpBZAGFkd2pZAXzVqYTZAGYnZANNU5JWlF1VUFyeGVzWndVdnhyQV9rbGVDUWlnSXhHOThEUjctTl9CT25vSXNIMnhFeGNtVTV0RU5pcTMyeGp5X1FMVGZAnMWx1ZAlRiSlBjZAHBkdEt3QzhGZA0pB"

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

    # 3. Direct YouTube Shorts Upload
    yt_client_id = os.environ.get("YOUTUBE_CLIENT_ID") or "53102647410-rmlfl4q59p7vthc64fieufmh8vqdic2d.apps.googleusercontent.com"
    yt_client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET") or "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"
    yt_refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN") or "1//0gDkudJijHs11CgYIARAAGBASNwF-L9IrbJ3cbVYNtQhY1KuR1zlJOg3XG3i8alPzVngTNXkAZTY75rERmqqlbsdP_1-5SUm7DuA"

    if yt_refresh_token and os.path.exists(local_video):
        try:
            print("\n[3] Uploading directly to YouTube Shorts...")
            yt_res = upload_youtube_short(local_video, title, description, yt_client_id, yt_client_secret, yt_refresh_token)
            print("  YouTube Shorts Result:", yt_res)
        except Exception as e:
            print(f"  YouTube Upload Error: {e}")

    if meta.get("is_promo"):
        print("\n" + "=" * 60)
        print(f"🎯 PROMO REEL PUBLISHED (Reel #{meta.get('reel_count')})")
        print(f"📌 PINNED COMMENT CTA: {meta.get('pinned_comment')}")
        print("=" * 60)

    print("\n" + "=" * 60)
    print("🎉 PUBLISHING PHASE COMPLETED!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="AI Video Pipeline")
    parser.add_argument("--render-only", action="store_true", help="Only generate and render video")
    parser.add_argument("--publish-only", type=str, help="Publish with provided video URL")
    parser.add_argument("--promo", action="store_true", help="Force generating a Promo Reel for Virtual Meeting Assistant")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))

    if args.publish_only:
        publish_phase(base_dir, args.publish_only)
    elif args.render_only:
        render_phase(base_dir, force_promo=args.promo)
    else:
        render_phase(base_dir, force_promo=args.promo)
        video_url = os.environ.get("PUBLIC_VIDEO_URL", "")
        publish_phase(base_dir, video_url)


if __name__ == "__main__":
    main()
