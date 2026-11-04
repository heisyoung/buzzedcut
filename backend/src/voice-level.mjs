import fs from 'node:fs';
import path from 'node:path';
import {spawnSync,execFileSync as run,execFile} from 'node:child_process';
import {promisify} from 'node:util';
const runAsync=promisify(execFile);
function settings(raw,wav,tempo,pad){const shape=`atempo=${tempo},highpass=f=65`;return{measure:['-v','info','-i',raw,'-af',shape+',loudnorm=I=-18:TP=-1:LRA=11:print_format=json','-f','null','-'],finish(gain){return['-y','-v','error','-i',raw,'-af',shape+`,volume=${gain.toFixed(4)}dB,alimiter=limit=0.89125:level=false:latency=true,apad=pad_dur=${pad}`,'-ar','44100','-ac','1','-c:a','pcm_s16le',wav]}};}
function report(stderr){const m=JSON.parse(stderr.slice(stderr.lastIndexOf('{'),stderr.lastIndexOf('}')+1)),input=Number(m.input_i),gain=Number.isFinite(input)?-18-input:0;return{profile:'fixed-gain-v13',target_lufs:-18,measured_input_lufs:input,gain_db:gain,automatic_level_riding:false,peak_protection_only:true};}
// Both paths apply one constant gain for the complete line; no automatic volume riding.
export function normalizeVoice(raw,wav,{tempo=1,pad=.22}={}){const args=settings(raw,wav,tempo,pad);const measured=spawnSync('ffmpeg',args.measure,{encoding:'utf8',maxBuffer:2000000});if(measured.status!==0)throw Error('Could not measure speech level');const level=report(measured.stderr);fs.mkdirSync(path.dirname(wav),{recursive:true});run('ffmpeg',args.finish(level.gain_db));return level;}
export async function normalizeVoiceAsync(raw,wav,{tempo=1,pad=.22}={}){const args=settings(raw,wav,tempo,pad),measured=await runAsync('ffmpeg',args.measure,{encoding:'utf8',maxBuffer:2000000});const level=report(measured.stderr);fs.mkdirSync(path.dirname(wav),{recursive:true});await runAsync('ffmpeg',args.finish(level.gain_db));return level;}
