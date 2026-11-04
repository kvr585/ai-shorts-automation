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

    # Curated offline mystery pool with guaranteed high retention and perfect duration
    offline_pool = [
        {
            "topic": "The Secret Vault of Mount Weather",
            "part1": {
                "title": "PART 1: The Mountain That Hides a City #shorts #mystery",
                "description": "PART 1 of 2: Deep beneath the Blue Ridge Mountains lies a classified bunker built for the end of the world. #shorts #viral #mystery",
                "voiceover_script": "Deep inside the granite bedrock of Virginia lies a facility so secret the government denied its existence for decades. Mount Weather is not just an emergency bunker. It is an entire subterranean metropolis spanning six hundred thousand square feet, complete with its own underground hospital, television broadcast studios, and autonomous power grid. Declassified Cold War blueprints confirm this underground citadel was designed to shelter executive and military leadership in the event of an apocalyptic nuclear war. But during the chaotic evacuation of September eleventh, high-ranking officials were rushed inside, only to discover something chilling in the lowest sub-levels. The classified revelation will leave you stunned. Part two reveals what was really waiting in the dark.",
                "scene_keywords": ["mountain bunker tunnel", "dark subterranean corridor", "classified military document", "glowing control room screens", "cold war bunker blast door"]
            },
            "part2": {
                "title": "PART 2: The Parallel Government Truth #shorts #mystery",
                "description": "PART 2 (FINALE): Declassified records expose the alternate government operating deep inside Mount Weather. #shorts #viral #mystery",
                "voiceover_script": "In Part 1, we explored the massive underground city of Mount Weather, but declassified memos reveal a far more terrifying reality. Mount Weather does not merely house human survivors. It operates an entirely separate, unelected shadow bureaucracy known as the Federal Relocation Arc, complete with duplicate government agencies authorized to suspend constitutional law during national crises. When investigators examined budget appropriations, they uncovered millions in untraceable funds directed into deep subterranean excavation projects that continue expanding to this day. Even more disturbing, local residents frequently report high-voltage electromagnetic surges and unmarked military convoys vanishing directly into the mountain face under the dead of night. What are they preparing for beneath the stone?",
                "scene_keywords": ["underground bunker vault", "secret government meeting", "military convoy night", "radar terminal glowing", "apocalyptic survival bunker"]
            }
        },
        {
            "topic": "The Lost Colony of Roanoke",
            "part1": {
                "title": "PART 1: The Island Where 115 People Vanished #shorts",
                "description": "PART 1 of 2: In 1587, 115 English colonists vanished without a single trace. #shorts #viral #mystery",
                "voiceover_script": "In fifteen eighty-seven, one hundred and fifteen English settlers landed on Roanoke Island to build a new world. Three years later, when their governor finally returned with supplies, the entire settlement had completely vanished. There were no signs of a struggle, no burned houses, and not a single grave. Every man, woman, and child had disappeared into thin air. The only clue left behind was a single cryptic word carved into a wooden palisade post: Croatoan. For centuries, historians insisted the colonists simply starved or integrated with local tribes. But modern ground-penetrating radar and newly discovered colonial letters have uncovered a dark secret the history books left out. Part two reveals the terrifying truth behind their disappearance.",
                "scene_keywords": ["ancient misty forest", "abandoned wooden settlement", "carved wooden post", "foggy ocean shore ship", "dark historical documents"]
            },
            "part2": {
                "title": "PART 2: The Secret Map of Roanoke #shorts #mystery",
                "description": "PART 2 (FINALE): Invisible ink on a 400-year-old map reveals the truth of Roanoke. #shorts #viral #mystery",
                "voiceover_script": "In Part 1, we explored the mysterious disappearance of Roanoke's one hundred and fifteen colonists, but newly analyzed British Museum artifacts have rewritten the story. When scientists examined Governor John White's original fifteen eighty-five map under specialized ultraviolet light, they discovered a hidden symbol concealed beneath two layers of paper. Covered in invisible starch ink was the exact military symbol for a secret inland fort fifty miles away from the coast. Excavations at that precise inland coordinate recently unearthed sixteenth-century English firearm rings and European ceramic fragments. But why did the English crown deliberately hide their fortress location from the world for over four centuries? What were they fleeing from on that desolate coastline?",
                "scene_keywords": ["ancient map ultraviolet", "secret fortress ruins", "excavation artifacts", "foggy wilderness trail", "shadowy historical archive"]
            }
        },
        {
            "topic": "The Oak Island Money Pit",
            "part1": {
                "title": "PART 1: The Trap Built 200 Feet Underground #shorts",
                "description": "PART 1 of 2: For two centuries, treasure hunters have died trying to breach the Money Pit. #shorts #viral #mystery",
                "voiceover_script": "In seventeen ninety-five, three teenagers on a remote Nova Scotia island discovered an unnatural depression beneath an ancient oak tree. When they began digging, they found something impossible: a meticulously engineered shaft featuring oak platforms every ten feet, sealed with layers of charcoal, coconut fiber, and putty. At ninety feet, they unearthed a stone slab inscribed with coded symbols. But as soon as they tried to dig deeper, the entire pit flooded with ocean water. Whoever engineered the Money Pit did not just bury something valuable; they created an ingenious hydraulic booby trap fed by artificial sea-water tunnels. Part two reveals what modern sonar finally detected at two hundred feet.",
                "scene_keywords": ["mysterious island forest", "deep excavation pit", "ancient coded stone", "underground water rush", "historical treasure map"]
            },
            "part2": {
                "title": "PART 2: The Sonar Secret of Oak Island #shorts #mystery",
                "description": "PART 2 (FINALE): High-tech deep sonar reveals what lies at the bottom of the Money Pit. #shorts #viral #mystery",
                "voiceover_script": "In Part 1, we saw how an ingenious tidal booby trap protected the legendary Oak Island shaft for centuries. Over six men have lost their lives trying to breach its depths. But recently, heavy drilling rigs and deep seismic tomography penetrated two hundred feet through solid bedrock, and what they discovered shocked geologists worldwide. Scanners detected human bone fragments, sixteenth-century Spanish copper coins, and parchment paper containing traces of gold leaf. Even more unbelievable, bore-hole cameras captured what appears to be a vaulted wooden chamber reinforced with iron hinges. Who possessed the advanced engineering skills to construct a complex hydraulic vault centuries before modern machinery? Some secrets were never meant to surface.",
                "scene_keywords": ["seismic scanner screen", "ancient gold coins macro", "underground flooded cavern", "iron hinges underwater", "mysterious ocean horizon"]
            }
        },
        {
            "topic": "The Cicada 3301 Mystery",
            "part1": {
                "title": "PART 1: The Internet's Most Dangerous Puzzle #shorts",
                "description": "PART 1 of 2: In 2012, an anonymous puzzle appeared online that terrified intelligence agencies. #shorts #viral #mystery",
                "voiceover_script": "On January fourth, twenty twelve, a cryptic black-and-white image appeared on an anonymous web forum. The text read: Hello. We are looking for highly intelligent individuals. To find them, we have devised a test. There is a message hidden in this image. What began as a curiosity quickly morphed into the most complex global scavenger hunt in history. To solve it, participants needed mastery over classical cryptography, Anglo-Saxon runes, Mayan numerology, and high-level quantum computing mathematics. But when the clues suddenly shifted from computer screens to physical telephone poles across five continents, the world realized this was not a game. Part two reveals what happened to those who solved it.",
                "scene_keywords": ["cryptic matrix code", "cicada insect neon", "dark server room glowing", "physical street coordinates", "mysterious shadowy hacker"]
            },
            "part2": {
                "title": "PART 2: Who Was Behind Cicada 3301? #shorts #mystery",
                "description": "PART 2 (FINALE): The chilling fate of the hackers who reached the final room of Cicada 3301. #shorts #viral #mystery",
                "voiceover_script": "In Part 1, we examined the global cryptographic gauntlet known as Cicada 3301. Only a tiny fraction of the world's most elite hackers managed to decipher the coordinates scattered across Paris, Seoul, and Sydney. Those who completed the final step were directed to a private dark-web portal. A final message appeared: We want the best, not the followers. The door then closed forever. Decades later, a few winners broke their non-disclosure agreements. They revealed that Cicada was an ultra-secret collective developing uncrackable privacy algorithms and anti-censorship software, suspected by analysts to be operated by a rogue intelligence agency or military cyber command. The organizers vanished without a trace, leaving behind only their winged digital insignia.",
                "scene_keywords": ["dark web terminal screen", "global digital network map", "secret cyber headquarters", "encryption cipher breaking", "mysterious neon emblem"]
            }
        }
    ]

    # Attempt dynamic AI generation via Gemini Flash Lite if API key is provided and not expired
    if api_key and not api_key.startswith("AQ."):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={api_key}"
            payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

            with urllib.request.urlopen(req, timeout=25) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))

            raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            parsed = None
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except Exception:
                    pass
            if not parsed:
                parsed = json.loads(raw_text)

            if parsed and "part1" in parsed and "part2" in parsed:
                print(f"[SUCCESS] Gemini Flash Lite generated new story: '{parsed.get('topic')}'")
                return parsed
        except Exception as err:
            print(f"[WARN] Gemini API call failed ({err}). Falling back to curated offline mystery pool.")
    else:
        print("[INFO] No external Gemini API key provided. Selecting fresh story from curated pool.")

    # Select the first topic in the curated pool that has not yet been covered
    for story in offline_pool:
        if story["topic"] not in past_topics:
            print(f"[POOL] Selected fresh mystery from curated pool: '{story['topic']}'")
            return story

    # If all curated topics were exhausted, return the first one
    return offline_pool[0]


def format_ass_time(srt_time_str: str) -> str:
    clean = srt_time_str.replace(',', '.')[:-1]
    if clean.startswith("00:"):
        clean = "0:" + clean[3:]
    return clean


async def _generate_voiceover_async(text: str, audio_path: str, srt_path: str, voice: str):
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
            submaker = edge_tts.SubMaker()
            with open(audio_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        submaker.feed(chunk)

            srt_content = submaker.get_srt() if hasattr(submaker, "get_srt") else submaker.generate_subs()
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            return
        except Exception as err:
            if attempt < 2:
                print(f"  [Edge-TTS] Warning: {err}. Retrying in 3s (attempt {attempt + 2}/3)...")
                await asyncio.sleep(3)
            else:
                raise err


def generate_voiceover(text: str, audio_path: str, srt_path: str, voice: str = "en-US-ChristopherNeural"):
    """
    Generates unlimited, free broadcast neural voiceover via Edge-TTS
    and generates word-synchronized subtitle timestamps.
    """
    asyncio.run(_generate_voiceover_async(text, audio_path, srt_path, voice))


def srt_to_ass(srt_path: str, ass_path: str, badge_text: str = "PART 1 OF 2", duration_sec: float = 55.0):
    """
    Converts word-level SRT into modern, viral short-form captions (.ass format):
    - Top Episode Badge (Alignment=8, Top-Center)
    - High-impact dynamic 2-3 words per display with bold outline and zero block clutter
    """
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_text = f.read()

    blocks = re.split(r"\n\s*\n", srt_text.strip())
    words_data = []
    for b in blocks:
        lines = b.strip().split("\n")
        if len(lines) >= 3:
            time_m = re.search(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[1])
            if time_m:
                start_s, end_s = time_m.groups()
                word = lines[2].strip()
                if word:
                    words_data.append({
                        "start": format_ass_time(start_s),
                        "end": format_ass_time(end_s),
                        "word": word
                    })

    end_badge_m = int(duration_sec // 60)
    end_badge_s = duration_sec % 60
    end_badge = f"0:{end_badge_m:02d}:{end_badge_s:05.2f}"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BadgeStyle,DejaVu Sans,30,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,1,8,30,30,90,1
Style: ReelsStyle,DejaVu Sans,52,&H0000FFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,2,2,30,30,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,{end_badge},BadgeStyle,,0,0,0,,{badge_text}
"""
    dialogues = []
    chunk_size = 3
    if words_data:
        for i in range(0, len(words_data), chunk_size):
            chunk = words_data[i:i + chunk_size]
            start_time = chunk[0]["start"]
            end_time = chunk[-1]["end"]
            phrase = " ".join(w["word"] for w in chunk).upper()
            dialogues.append(f"Dialogue: 1,{start_time},{end_time},ReelsStyle,,0,0,0,,{phrase}")
    else:
        for b in blocks:
            lines = b.strip().split("\n")
            if len(lines) >= 3:
                time_m = re.search(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[1])
                if time_m:
                    start_s, end_s = time_m.groups()
                    phrase = " ".join(lines[2:]).strip().upper()
                    dialogues.append(f"Dialogue: 1,{format_ass_time(start_s)},{format_ass_time(end_s)},ReelsStyle,,0,0,0,,{phrase}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(dialogues) + "\n")


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

    # Filter out empty or missing clips
    valid_clips = [c for c in clips if os.path.exists(c) and os.path.getsize(c) > 1024]
    if not valid_clips:
        print("[WARN] No valid stock clips found. Generating dark cinematic background fallback.")
        fallback_clip = os.path.join(os.path.dirname(output_path), "bg_fallback.mp4")
        cmd_bg = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=c=0x0a0a14:s=720x1280:r=30",
            "-t", f"{audio_duration:.2f}",
            "-pix_fmt", "yuv420p",
            fallback_clip
        ]
        subprocess.check_call(cmd_bg)
        valid_clips = [fallback_clip]
    clips = valid_clips

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
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{audio_duration:.2f}",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    subprocess.check_call(cmd)
