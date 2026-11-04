// Balance reading chunks instead of leaving a tiny final phrase.
function balancedSubtitleChunks(text,limit,measure=s=>s.length){
 const words=text.trim().split(/\s+/).filter(Boolean),n=words.length;if(!n)return[];
 const spans=Array.from({length:n},(_,i)=>Array.from({length:n+1},(_,j)=>j>i?words.slice(i,j).join(' '):''));
 for(let groups=1;groups<=n;groups++){
  const target=n/groups,dp=Array.from({length:groups+1},()=>Array(n+1).fill(Infinity)),back=Array.from({length:groups+1},()=>Array(n+1));dp[0][0]=0;
  for(let g=1;g<=groups;g++)for(let end=g;end<=n;end++)for(let start=g-1;start<end;start++){
   const chunk=spans[start][end],count=end-start;if(measure(chunk)>limit&&count>1)continue;
   const short=n>3&&count<4?24*(4-count):0;
   const score=dp[g-1][start]+(count-target)**2+short+(end<n&&!/[,.!?;:]$/.test(words[end-1])?.15:0);
   if(score<dp[g][end]){dp[g][end]=score;back[g][end]=start;}
  }
  if(Number.isFinite(dp[groups][n])){const result=[];let end=n;for(let g=groups;g>0;g--){const start=back[g][end];result.unshift(spans[start][end]);end=start;}return result;}
 }
 return words;
}
