// One pausable timebase for speech gaps, transitions, reveals and question timers.
export function createShowClock({now=()=>performance.now(),setTimeout:later=globalThis.setTimeout.bind(globalThis),clearTimeout:cancel=globalThis.clearTimeout.bind(globalThis)}={}){
 let offset=0,pausedAt=null,nativeTimer=null,sequence=0;const jobs=new Map();
 const time=()=>pausedAt===null?now()-offset:pausedAt;
 function arm(){if(nativeTimer!==null)cancel(nativeTimer);nativeTimer=null;if(pausedAt!==null||!jobs.size)return;const first=Math.min(...[...jobs.values()].map(j=>j.at));nativeTimer=later(run,Math.max(0,first-time()));}
 function run(){nativeTimer=null;if(pausedAt!==null)return;const due=[...jobs.entries()].filter(([,j])=>j.at<=time()+.1).sort((a,b)=>a[1].at-b[1].at);for(const[id,j]of due){if(pausedAt!==null)break;if(!jobs.has(id))continue;if(j.interval)j.at=time()+j.interval;else jobs.delete(id);try{j.fn(...j.args)}catch(error){later(()=>{throw error},0)}}arm();}
 function add(fn,delay,args,interval=0){const id=++sequence;jobs.set(id,{fn,args,at:time()+Math.max(0,Number(delay)||0),interval});arm();return id;}
 const clear=id=>{jobs.delete(id);arm()};
 return {now:time,get paused(){return pausedAt!==null},setTimeout:(fn,delay,...args)=>add(fn,delay,args),clearTimeout:clear,setInterval:(fn,delay,...args)=>add(fn,delay,args,Math.max(1,Number(delay)||1)),clearInterval:clear,pause(){if(pausedAt!==null)return;pausedAt=time();arm()},resume(){if(pausedAt===null)return;offset=now()-pausedAt;pausedAt=null;arm()},dispose(){jobs.clear();if(nativeTimer!==null)cancel(nativeTimer);nativeTimer=null}};
}
