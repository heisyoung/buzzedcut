export const judgeIds=['vincent','rosa','dante'];
export function mouthOpen(cue,elapsed,contract){const p=contract.mouth,duration=Number(cue.dur??cue.duration/1000);if(!(elapsed>=0&&elapsed<duration))return false;const env=cue.env||'',n=Math.floor(elapsed*p.envelope_hz);return n<env.length&&Number(env[n])>=p.threshold&&Math.floor(elapsed*p.cycle_hz)%2===0;}
export function buildPerformance(ep,contract){
 if(!judgeIds.includes(ep.lead))throw Error('Invalid lead judge');
 const cues=[ep.aux?.opening??ep.opening,...(ep.screening||[]),ep.aux?.welcome??ep.welcome,...ep.feedback,...Object.values(ep.aux||{}).filter(c=>!['opening','welcome'].includes(c.id))].filter(Boolean);
 const defaults=Object.fromEntries(judgeIds.map(j=>[j,contract.poses[j].neutral])),directed={};
 for(const cue of cues){if(!judgeIds.includes(cue.judge)||typeof cue.text!=='string'||!cue.text.trim())throw Error('Invalid performance cue');const seconds=Number(cue.dur??cue.duration/1000);if(cue.audio&&(!Number.isFinite(seconds)||seconds<=0||typeof cue.env!=='string'))throw Error('Invalid recorded cue '+cue.id);const listeners={};for(const[j,r]of Object.entries(cue.listener_reactions||{})){if(!judgeIds.includes(j)||j===cue.judge)throw Error('Invalid listener for '+cue.id);const pose=contract.poses[j][r.emotion];if(!pose||contract.banned.includes(pose)||typeof r.reason!=='string'||!r.reason.trim())throw Error('Unapproved listener reaction '+cue.id);listeners[j]={pose,emotion:r.emotion,reason:r.reason,at:Math.max(contract.reaction_delay_min,Math.min(contract.reaction_delay_max,Number(r.at)||.7))};}directed[cue.id]={speaker:cue.judge,listeners};}
 for(const j of judgeIds){const score=ep.scores?.[j];if(!Number.isFinite(score)||score<1||score>10)throw Error('Invalid score');if((ep.screening||[]).some(c=>c.buzz&&c.judge===j)&&score>=5)throw Error('Buzz score must remain below five');}
 return {version:contract.version,defaults,cues:directed,mouth:contract.mouth,questions:contract.questions};
}
export function listenerPose(performance,cue,judge,elapsed){const base=performance.defaults[judge],r=performance.cues[cue?.id]?.listeners[judge];return r&&elapsed>=r.at?r.pose:base;}
