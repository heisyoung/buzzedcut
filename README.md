# Buzzed Cut

Everybody deserves an audience.

Upload a short video. Vincent, Rosa and Dante watch it, argue about it and give it a score. Any of them can buzz out. You can ask a question, then download the whole show.

The audience is three cartoons. Still counts.

**[Try it at buzzedcut.com](https://www.buzzedcut.com)**

## What I built

I worked out the characters, the studio and the show format, then built the app with Codex. The research came from watching and studying judging shows, short video performance and how people respond to feedback.

The result is a website built for phones that also works on desktop. No install needed. Videos can be up to 30 seconds and 100 MB. The finished show includes the original clip, judges, subtitles, questions and scores.

## What Meta does

- **Muse Spark 1.3** watches the uploaded video and returns structured observations. It also writes the director plan, dialogue, buzz decisions, scores and follow-up answers.
- **Muse Voice Transcribe** transcribes the clip's speech.
- **Muse Spark Open on Modal** is the fallback for dialogue generation.
- **Muse Wonder and Muse Spark** helped review the research, code, scripts and sample performances during development. Those reviews are separate from the live show.

ElevenLabs supplies the voices. The approved cast is James for Vincent, Nayva for Rosa and Jerry B for Dante.

## Stack

The browser uses HTML, CSS, JavaScript and Canvas. The server is Node.js. Python, Pillow and NumPy assemble the pictures; FFmpeg and ffprobe handle video, audio and MP4 exports.

Modal runs the app and stores uploads and exports on a persistent volume. A Cloudflare Worker connects the custom domain to Modal. Keys stay on the server.

There is no frontend build step and no Node package install.

## Run it locally

You need Node 18 or newer, Python 3.12 or newer, FFmpeg and ffprobe.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example backend/.env
```

Fill in your own Meta and ElevenLabs keys in `backend/.env`. The Modal model endpoint and proxy credentials are optional, for the fallback. Change `backend/cast.json` to voice IDs available in your ElevenLabs account. Voice IDs are configuration, not API keys.

```sh
npm start
```

Open [localhost:8795](http://127.0.0.1:8795). The local server saves generated shows under `backend/data/`. Keep that folder private.

## Deploy to Modal

Authenticate the Modal CLI and create a secret called `buzzed-cut-api-keys` with the variables from `.env.example`.

```sh
modal deploy deploy-modal.py
```

The deployment keeps one container warm. You can change `min_containers` in the deployment file.

The deployment uses a volume called `buzzed-cut-v1-data`. Keep the volume if you want existing uploads and downloads to survive a deployment. The fresh source checkout starts with an empty Saved shows list.

For a custom domain, deploy `cloudflare/worker.mjs` as a Cloudflare Worker and set `UPSTREAM` to your Modal app URL. Connect the domain to that Worker.

## How a show runs

1. Validate and prepare the upload.
2. Transcribe speech and ask Muse Spark to analyze the actual clip.
3. Generate the panel's conversation from those observations and the active director guide.
4. Record the voices, measure their levels and prepare mouth timing.
5. Play the screening, review, optional questions and score reveal.
6. Render a downloadable MP4 on the server.

The lead judge stays in the large frame. Listening expressions come from an approved set. Speaking uses matched open and closed mouth images. The pause button stops the video, voices, animations and question timer together. The playback border follows the video's proportions.

A buzzed judge stays below five. Questions cannot change the scores. An exact-file repeat keeps its result while allowing a new conversation. Three buzzes stop screening. Skipping the question offer goes straight to the result.

Uploads and exports can be retried without starting from scratch. Download jobs keep running when you return to the upload page.

## What gave us trouble

The mouths drifted when expressions changed, so speaking now uses matched image pairs and one shared performance policy for the browser and export.

Voice levels were uneven. Each recorded line now gets a measured fixed gain, and speech is packed without another lossy encode.

The judges kept falling into the same roles. Vincent rejected, Rosa defended and Dante said something odd. We are still tuning the director to give each one a reason to react to the actual clip.

Startup time depends on the models, voice calls and connection. A measured production run took about 62 seconds. That is a measurement from one release, not a speed guarantee.

We also investigated intermittent noise through Bluetooth headphones. The same downloaded file played cleanly through laptop speakers. We have not claimed a complete Bluetooth fix.

## Checks

```sh
node tests/show-clock.test.mjs
node tests/video-layout.test.mjs
node tests/performance.test.mjs
```

These cover pause/resume timing, portrait and landscape sizing, approved reactions, mouth silence boundaries and question policy. They do not prove perfect lip sync or cover every phone and audio device.

## What is in this repo

Runtime code, the active director instructions and the illustrated assets needed to run it. Original research documents, API keys, uploaded videos, generated private shows, caches and logs are excluded.

The current director lives in `backend/direction.md`. The runtime research brief is `backend/research-brief.md`.
