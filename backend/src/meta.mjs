// Thin clients for Meta Model API (Muse Spark, Muse Voice Transcribe) and any
// OpenAI-compatible host (Baseten / Modal running Muse Spark Open). No dependencies.
import { readFile } from 'node:fs/promises';
import { existsSync, readFileSync, appendFileSync, mkdirSync } from 'node:fs';
import { basename } from 'node:path';

// tiny .env loader (no dotenv dependency)
export function loadEnv(path = '.env') {
  if (!existsSync(path)) return;
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (m && !line.trim().startsWith('#') && process.env[m[1]] == null) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
}

const META = () => process.env.META_BASE_URL || 'https://api.meta.ai/v1';
const metaKey = () => {
  const k = process.env.MODEL_API_KEY;
  if (!k) throw new Error('MODEL_API_KEY is not set (put it in .env)');
  return k;
};

export function logUsage(raw,operation,provider='Meta'){try{const file=process.env.BUZZED_USAGE_LOG;if(!file)return;const row={at:new Date().toISOString(),provider,operation,model:raw.model||null,usage:raw.usage||null};appendFileSync(file,JSON.stringify(row)+'\n');}catch{}}
async function asJson(r, what) {
  const text = await r.text();
  if (!r.ok) throw new Error(`${what} failed: HTTP ${r.status} ${text.slice(0, 800)}`);
  try { return JSON.parse(text); } catch { throw new Error(`${what}: not JSON: ${text.slice(0, 300)}`); }
}

export async function uploadFile(path, mime) {
  const fd = new FormData();
  fd.append('purpose', 'user_data');
  fd.append('file', new Blob([await readFile(path)], { type: mime }), basename(path));
  const r = await fetch(`${META()}/files`, { method: 'POST', headers: { Authorization: `Bearer ${metaKey()}` }, body: fd });
  return asJson(r, 'file upload');
}

export async function responses(body) {
  const r = await fetch(`${META()}/responses`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${metaKey()}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const raw=await asJson(r,'responses');logUsage(raw,'responses');return raw;
}

export function outputText(resp) {
  if (typeof resp.output_text === 'string') return resp.output_text;
  const parts = [];
  for (const item of resp.output || []) for (const c of item.content || []) if (c.type === 'output_text' && c.text) parts.push(c.text);
  return parts.join('');
}

// Muse Voice Transcribe, batch. Needs mono 16-bit PCM WAV at 16/24 kHz, <=10 min, <=32 MB.
export async function transcribe(wavPath, { keywords } = {}) {
  const req = { mode: 'DIARIZATION', model: 'muse-voice-transcribe-1.0', audioEncoding: 'WAV' };
  if (keywords?.length) req.keywords = keywords;
  const fd = new FormData();
  fd.append('request', new Blob([JSON.stringify(req)], { type: 'application/json' }));
  fd.append('audio', new Blob([await readFile(wavPath)], { type: 'audio/wav' }), 'audio.wav');
  const r = await fetch(`${META()}/asr/transcribe`, { method: 'POST', headers: { Authorization: `Bearer ${metaKey()}` }, body: fd });
  return asJson(r, 'transcribe');
}

// OpenAI-compatible chat completions (Meta, Baseten, Modal...)
export async function chat({ baseUrl, apiKey, body }) {
  const r = await fetch(`${baseUrl.replace(/\/$/, '')}/chat/completions`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return asJson(r, `chat (${baseUrl})`);
}

// pull the first JSON object out of a model reply (handles ```json fences / stray text)
export function parseJson(text) {
  try { return JSON.parse(text); } catch {}
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fenced) try { return JSON.parse(fenced[1]); } catch {}
  const a = text.indexOf('{'), b = text.lastIndexOf('}');
  if (a >= 0 && b > a) return JSON.parse(text.slice(a, b + 1));
  throw new Error('no JSON in model output');
}
