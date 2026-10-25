# AI Shorts & Reels Automation Pipeline

100% automated, unmetered, zero-cost pipeline for generating and publishing viral 2-part deep-dive shorts to **YouTube Shorts**, **Instagram Reels**, and **Facebook Page Reels**.

## Features
- **No Third-Party Paywalls:** Uses **Edge-TTS** (unlimited neural voiceover) and cloud **FFmpeg** (unlimited video rendering). No Creatomate or ElevenLabs subscriptions required.
- **2-Part Episodic Engine:** Part 1 (Mystery/Setup) and Part 2 (Resolution/Climax) with independent 3-second hooks.
- **Infinite Fresh Topics:** Gemini Flash Lite creates new topics and cross-checks `state.json` to never repeat a topic.
- **MrBeast / Hormozi Subtitles:** High-impact, yellow-highlighted, word-synchronized subtitles burned onto vertical HD clips with top episode badges.
- **Runs 24/7 in the Cloud:** Executes automatically at **9:00 AM, 2:00 PM, and 9:00 PM IST** via GitHub Actions. Your personal computer can be completely powered off.

## Schedule
The workflow runs automatically 3 times a day:
- **09:00 AM IST** (03:30 UTC)
- **02:00 PM IST** (08:30 UTC)
- **09:00 PM IST** (15:30 UTC)

You can also trigger a run manually anytime from the **Actions** tab on GitHub by clicking **Run workflow**.

## Repository Secrets
Go to **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions** $\rightarrow$ **New repository secret**:

| Secret Name | Description |
| :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API key for script generation |
| `PIXABAY_API_KEY` | Pixabay API key for vertical HD B-roll clips |
| `FB_PAGE_ID` | Facebook Page ID (e.g. `1440617492457272`) |
| `FB_PAGE_TOKEN` | Permanent System User Page Access Token |
| `IG_USER_ID` | Instagram Business / Creator User ID |
| `IG_ACCESS_TOKEN` | Instagram Long-Lived Graph API Access Token |
| `N8N_WEBHOOK_URL` | (Optional) n8n Webhook for YouTube Shorts upload |
