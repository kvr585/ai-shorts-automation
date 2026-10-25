import os
import re
import json
import asyncio
import urllib.request
import urllib.parse
import subprocess
import requests
import edge_tts


def generate_story(api_key: str, past_topics: list) -> dict:
    """
    Calls Gemini Flash Lite to generate a 2-part deep-dive mystery script,
    strictly deduplicating against all past_topics.
    """
    past_topics_str = ", ".join(past_topics[-40:]) if past_topics else "None yet"
    prompt = f"""You are an elite, viral mystery and anomaly documentary creator with millions of subscribers.

Generate a completely fresh, mind-blowing 2-PART deep-dive video series about a real-world bizarre historical enigma, mysterious scientific phenomenon, classified military incident, or unsolved anomaly.

CRITICAL DEDUPLICATION RULE:
You MUST choose a completely unique, fresh topic.
DO NOT use any of the following topics that were ALREADY covered in previous videos:
{past_topics_str}

STRUCTURE FOR THE 2-PART DEEP DIVE:

PART 1 (The Setup & The Incident):
- Opens with an irresistible, scroll-stopping 3-second hook that stops users mid-scroll.
- Densely packed with chilling, factual details about the initial discovery, timeline, or event.
- Closes with a suspenseful cliffhanger teasing the revelation in Part 2.
- Word count: strictly between 120 and 135 words (~48 to 54 seconds spoken pace).
- Write ONLY the spoken words. No stage directions, no speaker tags.

PART 2 (The Climax & Resolution):
- Opens with a high-impact standalone 3-second hook so any new viewer is immediately gripped.
- 2-second rapid bridge: "In Part 1, we explored [brief context]... but when..."
- The shocking evidence, declassified records, and complete mind-blowing payoff.
- Word count: strictly between 120 and 135 words (~48 to 54 seconds spoken pace).
- Write ONLY the spoken words. No stage directions, no speaker tags.

Output STRICT RAW JSON ONLY (no markdown code blocks, no backticks, no introduction):
{{
  "topic": "Concise Topic Name (e.g. The Lost Submarine K-129)",
  "part1": {{
    "title": "PART 1: [Viral Click-Worthy Title under 55 chars] #shorts #mystery",
    "description": "PART 1 of 2: [Compelling summary with hashtags #shorts #viral #mystery]",
    "voiceover_script": "Spoken script for Part 1 (120-135 words)...",
    "scene_keywords": [
      "cinematic visual keyword 1",
      "cinematic visual keyword 2",
      "cinematic visual keyword 3",
      "cinematic visual keyword 4",
      "cinematic visual keyword 5"
    ]
  }},
  "part2": {{
    "title": "PART 2: [The Shocking Conclusion Title under 55 chars] #shorts #mystery",
    "description": "PART 2 (FINALE): [Compelling summary with hashtags #shorts #viral #mystery]",
    "voiceover_script": "Spoken script for Part 2 (120-135 words)...",
    "scene_keywords": [
      "cinematic visual keyword 1",
      "cinematic visual keyword 2",
      "cinematic visual keyword 3",
      "cinematic visual keyword 4",
      "cinematic visual keyword 5"
    ]
  }}
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={api_key}"
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    with urllib.request.urlopen(req, timeout=30) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))

    raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"```$", "", raw_text).strip()

    return json.loads(raw_text)


async def _generate_voiceover_async(text: str, audio_path: str, srt_path: str, voice: str):
    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                submaker.feed(chunk)

    srt_content = submaker.get_srt() if hasattr(submaker, "get_srt") else submaker.generate_subs()
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)


def generate_voiceover(text: str, audio_path: str, srt_path: str, voice: str = "en-US-ChristopherNeural"):
    """
    Generates unlimited, free broadcast neural voiceover via Edge-TTS
    and generates word-synchronized subtitle timestamps.
    """
    asyncio.run(_generate_voiceover_async(text, audio_path, srt_path, voice))


def srt_to_ass(srt_path: str, ass_path: str, badge_text: str = "PART 1 OF 2", duration_sec: float = 55.0):
    """
    Converts standard SRT into stylish vertical short subtitles (.ass format):
    - Top Episode Badge pill (Alignment=8, Top-Center)
    - Bold uppercase spoken text with yellow highlight (#FFE81F) and black outline (Alignment=2, Bottom-Center)
    """
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_text = f.read()

    blocks = re.split(r"\n\s*\n", srt_text.strip())
    dialogue_lines = []

    # 1. Permanent Top Badge
    end_badge_m = int(duration_sec // 60)
    end_badge_s = duration_sec % 60
    end_badge = f"0:{end_badge_m:02d}:{end_badge_s:05.2f}"
    dialogue_lines.append(f"Dialogue: 0,0:00:00.00,{end_badge},BadgeStyle,,0,0,0,,{badge_text}")

    # 2. Spoken Karaoke Subtitles
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            time_match = re.search(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[1])
            if time_match:
                start_str, end_str = time_match.groups()
                start_ass = start_str[:-1].replace(",", ".")
                if start_ass.startswith("00:"):
                    start_ass = "0:" + start_ass[3:]
                end_ass = end_str[:-1].replace(",", ".")
                if end_ass.startswith("00:"):
                    end_ass = "0:" + end_ass[3:]

                spoken_text = " ".join(lines[2:]).strip().upper()
                words = spoken_text.split()
                chunk_size = 4
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i + chunk_size])
                    dialogue_lines.append(f"Dialogue: 1,{start_ass},{end_ass},ReelsStyle,,0,0,0,,{chunk}")

    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BadgeStyle,Arial,32,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,5,3,8,30,30,110,1
Style: ReelsStyle,Arial,48,&H001FE8FF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,3,2,30,30,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(dialogue_lines) + "\n")


def fetch_pixabay_clips(keywords: list, pixabay_key: str, output_dir: str, target_count: int = 7) -> list:
    os.makedirs(output_dir, exist_ok=True)
    downloaded_clips = []

    fallback_urls = [
        "https://cdn.pixabay.com/video/2024/06/02/215018_large.mp4",
        "https://cdn.pixabay.com/video/2022/11/22/140111-774507949_large.mp4",
        "https://cdn.pixabay.com/video/2024/12/03/244754_large.mp4",
        "https://cdn.pixabay.com/video/2020/08/30/48569-454825064_large.mp4"
    ]

    for kw in keywords:
        if len(downloaded_clips) >= target_count:
            break
        try:
            url = f"https://pixabay.com/api/videos/?key={pixabay_key}&q={urllib.parse.quote(str(kw))}&orientation=vertical&per_page=5"
            res = requests.get(url, timeout=10).json()
            hits = res.get("hits", [])
            if hits:
                hit = hits[0]
                v_url = (hit.get("videos", {}).get("large", {}).get("url") or
                         hit.get("videos", {}).get("medium", {}).get("url") or
                         hit.get("videos", {}).get("small", {}).get("url"))
                if v_url:
                    clip_file = os.path.join(output_dir, f"clip_{len(downloaded_clips)}.mp4")
                    r = requests.get(v_url, timeout=20)
                    with open(clip_file, "wb") as f:
                        f.write(r.content)
                    downloaded_clips.append(clip_file)
        except Exception as e:
            print(f"Error fetching clip for keyword '{kw}': {e}")

    for i, fb_url in enumerate(fallback_urls):
        if len(downloaded_clips) >= target_count:
            break
        try:
            clip_file = os.path.join(output_dir, f"fallback_{i}.mp4")
            r = requests.get(fb_url, timeout=20)
            with open(clip_file, "wb") as f:
                f.write(r.content)
            downloaded_clips.append(clip_file)
        except Exception:
            pass

    return downloaded_clips


def get_media_duration(file_path: str, script_words: int = 125) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    try:
        out = subprocess.check_output(cmd).decode().strip()
        val = float(out)
        if val > 5.0:
            return val
    except Exception:
        pass
    # Estimated speech duration fallback
    return max(48.0, min(56.0, script_words / 2.4))


def render_video(clips: list, audio_path: str, ass_path: str, output_path: str, script_words: int = 125):
    """
    Renders vertical 720x1280 MP4 using FFmpeg and libass.
    """
    audio_duration = get_media_duration(audio_path, script_words)
    clip_dur = audio_duration / max(1, len(clips))

    concat_list_path = os.path.join(os.path.dirname(output_path), "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for clip in clips:
            clean_path = os.path.abspath(clip).replace("\\", "/")
            f.write(f"file '{clean_path}'\n")
            f.write(f"duration {clip_dur:.2f}\n")
        if clips:
            last_clip_path = os.path.abspath(clips[-1]).replace("\\", "/")
            f.write(f"file '{last_clip_path}'\n")

    clean_ass = os.path.abspath(ass_path).replace("\\", "/").replace(":", "\\:")
    vf = f"scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,subtitles='{clean_ass}'"

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-i", audio_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{audio_duration:.2f}",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    subprocess.check_call(cmd)
