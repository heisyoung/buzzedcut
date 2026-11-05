# Buzzed Cut


Everybody deserves an audience.


Upload a short video. Vincent, Rosa and Dante watch it, argue about it and give it a score. Any of them can buzz out. You can ask a question, then download the whole show.


The audience is three cartoons. Still counts.


**[Try it at buzzedcut.com](https://www.buzzedcut.com)**


## What I built


I’m not a professional coder. I developed the characters, studio and show format, then used Claude, Codex, Gemini and Meta’s models to help build it, choosing whichever tool worked best for the task. The research came from studying judging shows, short videos and how people respond to feedback.


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
