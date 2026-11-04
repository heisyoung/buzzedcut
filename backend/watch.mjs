#!/usr/bin/env node
// Step 1: Muse Spark watches a reel and returns timed observations.
// Speech comes from Muse Voice Transcribe (Spark 1.3 audio is flagged as degraded by Meta).
//
//   node scripts/watch.mjs clips/myreel.mp4                 # tries file upload -> data URL -> frames
//   node scripts/watch.mjs clips/myreel.mp4 --mode frames   # force a mode
//   node scripts/watch.mjs clips/myreel.mp4 --dry           # build requests, no API calls
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { basename, extname, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadEnv, uploadFile, responses, outputText, transcribe, parseJson } from './src/meta.mjs';

const ROOT = process.env.BUZZED_JOB_ROOT || dirname(fileURLToPath(import.meta.url));
loadEnv(join(ROOT, '.env'));

const args = process.argv.slice(2);
const clip = args.find((a) => !a.startsWith('--'));
const flag = (n, d) => { const i = args.indexOf(`--${n}`); return i < 0 ? d : args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true; };
const DRY = !!flag('dry', false);
const MODE = flag('mode', 'auto');
const MODEL = process.env.WATCH_MODEL || 'muse-spark-1.3'; // never the -contributor tier for other people's clips
if (!clip) { console.error('usage: node scripts/watch.mjs <clip.mp4> [--mode auto|file|url|frames] [--dry]'); process.exit(1); }

const stem = basename(clip, extname(clip));
const out = join(ROOT, 'out', stem);
mkdirSync(out, { recursive: true });
const log = (...m) => console.log('[watch]', ...m);
const save = (name, data) => writeFileSync(join(out, name), typeof data === 'string' ? data : JSON.stringify(data, null, 2));

// --- probe
const probe = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height', '-of', 'json', clip]).toString());
const duration = +(+probe.format.duration).toFixed(2);
const hasAudio = probe.streams.some((s) => s.codec_type === 'audio');
log(`${stem}: ${duration}s, audio: ${hasAudio}`);
if (duration > 30.5) log(`WARNING: ${duration}s is over the 30s limit`);
if (extname(clip).toLowerCase() !== '.mp4') log('WARNING: Meta video input only lists mp4');

const earlyUpload=!DRY&&['auto','file'].includes(MODE)?uploadFile(clip,'video/mp4').then(value=>({value}),error=>({error})):null;

// --- transcript
let transcript = null;
const transcriptTask=(async()=>{if (hasAudio) {
  const wav = join(out, 'audio.wav');
  execFileSync('ffmpeg', ['-y', '-v', 'error', '-i', clip, '-vn', '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', '-map_metadata', '-1', wav]);
  if (DRY) log('dry: would transcribe audio.wav');
  else {
    try {
      transcript = await transcribe(wav);
      save('transcript.json', transcript);
      log(`transcript: ${transcript.turns?.length ?? 0} turns`);
    } catch (e) { log('transcribe failed, continuing without:', e.message); }
  }
}})();

// --- prompt
const schema = JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'schema/observations.schema.json'), 'utf8'));
const turns = transcript?.turns?.length
  ? transcript.turns.map((t) => `${(t.startMs / 1000).toFixed(1)}-${(t.endMs / 1000).toFixed(1)}s ${t.speaker ? `[${t.speaker}] ` : ''}${t.transcript}`).join('\n')
  : transcript?.transcript || (hasAudio ? '(no speech detected or transcript unavailable)' : '(video has no audio track)');
const promptText = `${readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'prompts/watcher.md'), 'utf8')}\nReturn 6–8 concise high-signal observations maximum, focused on performance, changes and the experience. Avoid repetitive inventories.\nDURATION: ${duration}s\n\nTRANSCRIPT:\n${turns}\n`;

function body(mediaParts, modeNote = '') {
  return {
    model: MODEL,
    reasoning: { effort: 'minimal' },
    max_output_tokens: 4000,
    input: [{ type: 'message', role: 'user', content: [{ type: 'input_text', text: promptText + modeNote }, ...mediaParts] }],
    text: { format: { type: 'json_schema', name: 'reel_observations', schema, strict: true } },
  };
}

function frameParts() {
  const dir = join(out, 'frames');
  mkdirSync(dir, { recursive: true });
  execFileSync('ffmpeg', ['-y', '-v', 'error', '-i', clip, '-vf', 'fps=2,scale=512:-2', '-q:v', '5', join(dir, 'f_%03d.jpg')]);
  const files = readdirSync(dir).filter((f) => f.endsWith('.jpg')).sort();
  const parts = [];
  files.forEach((f, i) => {
    parts.push({ type: 'input_text', text: `frame at ${(i * 0.5).toFixed(1)}s` });
    parts.push({ type: 'input_image', image_url: `data:image/jpeg;base64,${readFileSync(join(dir, f)).toString('base64')}` });
  });
  return parts;
}

const modes = MODE === 'auto' ? ['file', 'url', 'frames'] : [MODE];
const attempts = [];
let result = null;
for (const mode of modes) {
  try {
    let req;
    if (mode === 'file') {
      if (DRY) req = body([{ type: 'input_file', file_id: '<uploaded>' }]);
      else {
        const prepared=earlyUpload?await earlyUpload:{value:await uploadFile(clip,'video/mp4')};if(prepared.error)throw prepared.error;const f=prepared.value;
        log('uploaded', f.id);
        req = body([{ type: 'input_file', file_id: f.id }]);
      }
    } else if (mode === 'url') {
      const size = statSync(clip).size;
      if (size > 20e6) throw new Error(`clip is ${(size / 1e6).toFixed(1)} MB, too big for an inline data URL`);
      req = body([{ type: 'input_video', video_url: `data:video/mp4;base64,${DRY ? '<b64>' : readFileSync(clip).toString('base64')}` }]);
    } else if (mode === 'frames') {
      req = body(frameParts(), '\nYou are given still frames at 2 per second instead of the video. Cuts and motion between frames are inferred.\n');
    } else throw new Error(`unknown mode ${mode}`);

    if (DRY) {
      save(`request_${mode}.json`, JSON.stringify(req, (k, v) => (typeof v === 'string' && v.startsWith('data:') ? v.slice(0, 40) + '...' : v), 2));
      attempts.push({ mode, ok: 'dry' });
      continue;
    }
    const t0 = Date.now();
    const resp = await responses(req);
    save(`response_${mode}.json`, resp);
    const obs = parseJson(outputText(resp));
    if (!obs.observations?.length) throw new Error('no observations in reply');
    obs.duration_s = duration; // trust ffprobe over the model
    attempts.push({ mode, ok: true, secs: (Date.now() - t0) / 1000, usage: resp.usage ?? null });
    result = { mode, obs };
    break;
  } catch (e) {
    attempts.push({ mode, ok: false, error: e.message });
    log(`mode ${mode} failed: ${e.message.slice(0, 300)}`);
  }
}
save('video_check.json', { clip: stem, model: MODEL, duration, attempts, checked_at: new Date().toISOString() });

if (DRY) { log(`dry run done, requests in ${out}`); process.exit(0); }
if (!result) { log('all modes failed - see video_check.json'); process.exit(1); }

await transcriptTask;
if(transcript)result.obs.transcript=transcript;

// --- sanity checks on timestamps
const bad = result.obs.observations.filter((o) => o.t_start < 0 || o.t_end > duration + 0.5 || o.t_end < o.t_start);
if (bad.length) log(`WARNING: ${bad.length} observations have impossible times:`, bad.map((o) => o.id).join(', '));
save('observations.json', result.obs);
log(`OK via "${result.mode}": ${result.obs.observations.length} observations -> out/${stem}/observations.json`);
for (const o of result.obs.observations) console.log(`  ${o.id.padEnd(4)} ${o.t_start.toFixed(1)}-${o.t_end.toFixed(1)}  [${o.kind}] ${o.what}`);
