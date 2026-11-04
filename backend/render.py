import sys,json,subprocess,math,hashlib,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageEnhance,ImageOps
ROOT=Path(os.environ.get('BUZZED_PUBLIC','../public')).resolve();PUB=ROOT/'live-show-expressions';LAY=ROOT/'viewing/layers';W,H,FPS=390,844,20
inp=Path(sys.argv[1]);out=Path(sys.argv[2]);data=json.loads(subprocess.check_output(['node',str(Path(__file__).with_name('validate-performance.mjs')),str(inp)]));ep=data['episode'];policy=ep['performance'];questions=data.get('questions',[]);acting=None
if data.get('includeExample'):questions=[{'judge':ep['example_question']['judge'],'question':ep['example_question']['text'],'cue':ep['aux']['example_answer']}]
EPDIR=Path(data['episode_dir']).resolve()
def audio_path(c):return Path(data.get('data_root',EPDIR.parent.parent))/c['audio'].removeprefix('/media/') if c['audio'].startswith('/media/') else EPDIR/c['audio']
clip=EPDIR/'reel.mp4';probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','json',str(clip)]));clipdur=float(probe['format']['duration']);vstream=next(s for s in probe['streams'] if s.get('codec_type')=='video');video_aspect=vstream['width']/vstream['height'];landscape=video_aspect>1.05
opening=ep['aux']['opening'];line=[{**opening,'start':3,'stage':'screen'}];screenstart=3+opening['dur']+opening.get('pause_after',.8);screenend=screenstart+clipdur
prev=0
for c in ep['screening']:
 start=max(screenstart+c['at'],prev+.12);line.append({**c,'start':start,'stage':'screen'});prev=start+c['dur']
transitionstart=max(screenend,prev);transitionend=transitionstart+2.5;t=transitionend+1;segments=[];effects=[{'kind':'transition-clicks','start':transitionstart}]+[{'kind':'buzzer','start':screenstart+c.get('buzz_at',c['at'])}for c in ep['screening']if c.get('buzz')]
welcome=ep['aux']['welcome'];line.append({**welcome,'start':t,'stage':'welcome'});t+=welcome['dur']+.25
previous_feedback=None
for c in ep['feedback']:
 if previous_feedback is not None:t=previous_feedback['start']+previous_feedback['dur']+c.get('gap_before',previous_feedback.get('pause_after',.65))
 event={**c,'start':t,'stage':'feedback'};line.append(event);previous_feedback=event;segments.append((t,t+c['dur'],'feedback',c))
 if c.get('reaction_after'):effects.append({'kind':c['reaction_after'],'start':t+c['dur']+.1})
 t+=c['dur']+c.get('pause_after',.65)
windows=[]
skip_questions=bool(data.get('skip_questions'))
if questions or not skip_questions:
 c=ep['aux']['invite'];line.append({**c,'start':t,'stage':'invite'});segments.append((t,t+c['dur']+.8,'invite',c));t+=c['dur']+c.get('pause_after',.8)
 wait=5.2 if questions else policy['questions']['offer_seconds'];windows.append((t,t+wait));tease=ep['aux'].get('countdown_tease')
 if tease:line.append({**tease,'start':t+.3,'stage':'invite'})
 t+=wait
 for qi,q in enumerate(questions):
  segments.append((t,t+4.2,'question',q));t+=4.2;c=q['cue'];line.append({**c,'start':t,'stage':'feedback'});segments.append((t,t+c['dur'],'feedback',c));t+=c['dur']+c.get('pause_after',.7)
  if qi+1<len(questions):
   c=ep['aux']['followup_invite'];line.append({**c,'start':t,'stage':'invite'});segments.append((t,t+c['dur'],'invite',c));t+=c['dur']+c.get('pause_after',.6);windows.append((t,t+5.2));t+=5.2
if not skip_questions:
 if len(questions)==1:
  c=ep['aux']['followup_invite'];line.append({**c,'start':t,'stage':'invite'});segments.append((t,t+c['dur'],'invite',c));t+=c['dur']+c.get('pause_after',.6)
  windows.append((t,t+policy['questions']['offer_seconds']));tease=ep['aux'].get('countdown_tease_alt')
  if tease:line.append({**tease,'start':t+.3,'stage':'invite'})
  t+=policy['questions']['offer_seconds']
 for key in ['tag','sendoff','closing']:
  c=ep['aux'].get(key)
  if c:
   line.append({**c,'start':t,'stage':'closing'if key=='closing'else'feedback'});segments.append((t,t+c['dur'],'closing'if key=='closing'else'feedback',c));t+=c['dur']+c.get('pause_after',.45)
scorestart=t;total=t+8.5
if '--timeline-only' in sys.argv:
 print(json.dumps({'duration':total,'screen_start':screenstart,'score_start':scorestart,'lines':line}));sys.exit(0)
effects.append({"kind":"score-lounge","start":scorestart});effects.extend({'kind':'score-hit','start':scorestart+1.10+i*.95}for i in range(3));effects.append({'kind':'score-hit','start':scorestart+3.9})
framesdir=out.parent/('native-clipframes-'+hashlib.sha256(clip.read_bytes()).hexdigest()[:12]);framesdir.mkdir(parents=True,exist_ok=True)
if not list(framesdir.glob('*.jpg')):subprocess.run(['ffmpeg','-y','-v','error','-i',str(clip),'-vf',f'fps={FPS},scale=390:844:force_original_aspect_ratio=decrease','-q:v','3',str(framesdir/'%04d.jpg')],check=True)
video_frames=list(sorted(framesdir.glob('*.jpg')));cache={};asset_ids={};scaled={}
def img(path):
 path=str(path)
 if path not in cache:cache[path]=Image.open(path).convert('RGBA');asset_ids[id(cache[path])]=path
 return cache[path]
fonts={}
def font(n,bold=False):
 key=(n,bold)
 if key not in fonts:fonts[key]=ImageFont.truetype(os.environ.get('BUZZED_FONT_BOLD' if bold else 'BUZZED_FONT', '/System/Library/Fonts/Supplemental/Arial'+(' Bold' if bold else '')+'.ttf'),n)
 return fonts[key]
def put(canvas,source,box):
 x,y,w,h=map(round,box);key=(asset_ids.get(id(source)),w,h)
 if key[0] is not None:
  if key not in scaled:scaled[key]=source.resize((max(1,w),max(1,h)),Image.Resampling.LANCZOS)
  im=scaled[key]
 else:im=source.resize((max(1,w),max(1,h)),Image.Resampling.LANCZOS)
 canvas.alpha_composite(im,(x,y))
def video_at(t):return img(video_frames[min(len(video_frames)-1,max(0,int(t*FPS)))])
from functools import lru_cache
@lru_cache(maxsize=512)
def balanced(text,limit,size=0):
 words=text.split();n=len(words)
 if not n:return ['']
 d=ImageDraw.Draw(Image.new('RGB',(1,1)))
 def width(t):return d.textlength(t,font=font(size,size>=23))if size else len(t)
 spans={(i,j):' '.join(words[i:j])for i in range(n)for j in range(i+1,n+1)}
 for groups in range(1,n+1):
  dp={(0,0):0};back={};target=n/groups
  for g in range(1,groups+1):
   for end in range(g,n+1):
    for start in range(g-1,end):
     count=end-start;chunk=spans[start,end]
     if width(chunk)>limit and count>1:continue
     cost=dp.get((g-1,start),float('inf'))+(count-target)**2+(24*(4-count)if n>3 and count<4 else 0)
     if cost<dp.get((g,end),float('inf')):dp[g,end]=cost;back[g,end]=start
  if (groups,n)in dp:
   result=[];end=n
   for g in range(groups,0,-1):start=back[g,end];result.insert(0,spans[start,end]);end=start
   return result
 return words
def wrapped(text,maxwidth,n):return balanced(text,maxwidth,n)
def caption(canvas,text,box,n=17):
 x,y,w,h=map(round,box);overlay=Image.new('RGBA',(w,h));dr=ImageDraw.Draw(overlay)
 for yy in range(h):dr.line((0,yy,w,yy),fill=(29,19,12,round(235*min(1,yy/20))))
 canvas.alpha_composite(overlay,(x,y));d=ImageDraw.Draw(canvas);lines=wrapped(text,w-16,n);height=len(lines)*round(n*1.3);ty=y+h-height-10
 for l in lines:d.text((x+w/2,ty),l,font=font(n),fill='#fff7e5',anchor='mt');ty+=round(n*1.3)
studio=img(LAY/'studio-top-clean-old-bottom-v13.png').resize((W,H),Image.Resampling.LANCZOS);logo=img(ROOT/'home-assets/brand-logo-black-larger-cut-v20.png')
def logo_on(canvas,x,y,w):put(canvas,logo,(x,y,w,w*logo.height/logo.width))
name={'vincent':'Vincent','dante':'Dante','rosa':'Rosa'}
def mouth(c,t):
 local=t-c['start'];env=c.get('env','');p=policy['mouth'];idx=int(local*p['envelope_hz']);return 1 if 0<=local<c['dur'] and 0<=idx<len(env) and int(env[idx])>=p['threshold'] and int(local*p['cycle_hz'])%2==0 else 0

def screening(t,c):
 canvas=studio.copy();logo_on(canvas,54.35,52.38,280.8)
 for j in ['dante','vincent','rosa']:
  state='watch';cue=next((q for q in ep['screening']if q['judge']==j and q.get('buzz')),None);vt=t-screenstart
  if cue and cue.get('buzz_at',cue['at'])-.3<=vt<cue.get('buzz_at',cue['at']):state='ready'
  if cue and cue.get('buzz_at',cue['at'])<=vt<cue.get('buzz_at',cue['at'])+.7:state='buzz'
  if c and c['judge']==j and mouth(c,t)and state=='watch'and j!='rosa':state='watch'
  if j=='vincent':file=f'vincent-{state}-smile-v9.png'if state!='talk'else'vincent-talk.png';box=(-52,169,242,242)
  elif j=='dante':file=f'dante-{state if state!="ready"else"watch"}.png';box=(207,187,240,240)
  else:file={'watch':'rosa-exact-reference-cutout-v7-smile-v9.png','ready':'rosa-left-ready-v13.png','buzz':'rosa-left-contact-v13.png'}[state];box=(110,220,171,216)
  if state=='watch' and c and c['judge']==j:
   mode='open'if mouth(c,t)else'closed';put(canvas,img(PUB/f'art-rig/watch-{j}-{mode}.webp'),box)
  else:put(canvas,img(LAY/file),box)
 canvas.alpha_composite(studio.crop((0,415,W,H)),(0,415))
 for i,j in enumerate(['vincent','rosa','dante']):
  put(canvas,img(LAY/f'mic-mounted-{j}-v13.png'),([86.8,218.7,321][i],[344,344,339][i],62.4,70.2));put(canvas,img(LAY/f'buzzer-ivory-{i+1}-v14.png'),([37,167,297][i],396,44,19))
  cue=next((q for q in ep['screening']if q['judge']==j and q.get('buzz')),None)
  if cue and t-screenstart>=cue.get('buzz_at',cue['at']):
   glow=Image.new('RGBA',(W,H));gd=ImageDraw.Draw(glow);cx=[59,189,319][i];gd.text((cx,159),'×',font=font(60,True),anchor='mm',fill='#ff3434',stroke_width=3,stroke_fill='#fff6db');blur=glow.filter(ImageFilter.GaussianBlur(6));canvas.alpha_composite(blur);canvas.alpha_composite(glow);top=Image.new('RGBA',(W,H));td=ImageDraw.Draw(top);td.ellipse((cx-16,394,cx+16,403),fill='#ff2424');canvas.alpha_composite(top.filter(ImageFilter.GaussianBlur(3)));canvas.alpha_composite(top)
 bw=min(W*.90-4,(H*.43-4)*video_aspect);bh=bw/video_aspect;bx,by=round((W-bw)/2),round(H*.53);bw,bh=round(bw),round(bh)
 v=studio.crop((bx,by,bx+bw,by+bh));fit=ImageOps.contain(video_at(max(0,t-screenstart)),(bw,bh),Image.Resampling.LANCZOS);v.alpha_composite(fit,((bw-fit.width)//2,(bh-fit.height)//2));mask=Image.new('L',(bw,bh));ImageDraw.Draw(mask).rounded_rectangle((0,0,bw-1,bh-1),radius=12,fill=255);canvas.paste(v,(bx,by),mask);ImageDraw.Draw(canvas).rounded_rectangle((bx-2,by-2,bx+bw+1,by+bh+1),radius=14,outline='#e7c99b',width=2)
 if t<screenstart:
  d=ImageDraw.Draw(canvas);angle=int(t*260)%360;d.arc((182,616,208,642),angle,angle+285,fill='#fff7e5',width=3)
 c=next((q for q in reversed(line) if q['stage']=='screen' and q['start']<=t<q['start']+q['dur']+1),None)
 if c:
  lines=wrapped(c['text'],374,24);chars=sum(map(len,lines));at=min(.999,max(0,(t-c['start'])/c['dur']))*chars;totalchars=0;selected=lines[-1]
  for l in lines:
   totalchars+=len(l)
   if totalchars>at:selected=l;break
  ImageDraw.Draw(canvas).text((195,431),selected,font=font(24,True),fill='#fff7e5',anchor='mm',stroke_width=1,stroke_fill='#392015')
 return canvas
lead=ep['lead']
def directed_poses(t):
 latest=next((l for l in reversed(line)if l['stage']!='screen' and l['start']<=t),None)
 poses=dict(policy['defaults'])
 if latest:
  for j,r in policy['cues'].get(latest.get('id'),{}).get('listeners',{}).items():
   if t-latest['start']>=r['at']:poses[j]=r['pose']
 return poses
rigstates={}
def rig_face(j,pose,t,active,level,frontal=False):
 if j=='rosa'and pose=='R04':pose='R01'
 defaults={'vincent':'V07','rosa':'R01','dante':'D10'};state=rigstates.setdefault(j,{'pose':defaults[j],'smoke':None})
 if pose=='smoke':
  if state['smoke'] is None:state['smoke']=t
  pose='V07'
 else:state['pose']=pose if (PUB/f'art-stable-v9/{pose}-closed.webp').exists()else defaults[j]
 pose=state['pose'] if pose!='V07' else pose;mode='open'if active and level>.075 else'closed';source=img(PUB/f'art-frontal-v10/{j}-{mode}.webp')if frontal else img(PUB/f'art-stable-v9/{pose}-closed.webp')
 if j=='vincent' and state['smoke'] is not None and not active and ep.get('audience',{}).get('band')not in ['under_10','10_13']:
  age=t-state['smoke'];up=age/.4 if age<.4 else 1 if age<1.25 else max(0,1-(age-1.25)/.6)
  if up>0:
   source=source.copy()
   hand=img(PUB/'art-stable-v9/vincent-cigarette-arm.webp').resize(source.size);hand.putalpha(hand.getchannel('A').point(lambda v:round(v*min(1,up*3))));source.alpha_composite(hand,(0,round((1-up)*source.height*.5)))
 return source

def transition(t):
 canvas=studio.copy();tm=t-transitionstart;clock=img(PUB/'stopwatch.png');z=1+tm*.025;w=round(300*z);h=round(w*clock.height/clock.width);x=(W-w)//2;y=240-(h-330)//2;clock=clock.resize((w,h),Image.Resampling.LANCZOS);canvas.alpha_composite(clock,(x,y));cx=x+w*.5;cy=y+h*.565;a=math.floor(tm/.125)*.30-math.pi/2;d=ImageDraw.Draw(canvas);d.line([(cx-math.cos(a)*10,cy-math.sin(a)*10),(cx+math.cos(a)*w*.305,cy+math.sin(a)*w*.305)],fill='#b4261d',width=4);d.ellipse((cx-6,cy-6,cx+6,cy+6),fill='#e64126');return canvas

@lru_cache(maxsize=8)
def panel_background(w,h):return ImageEnhance.Brightness(studio.crop((0,85,W,650)).resize((w,h),Image.Resampling.LANCZOS)).enhance(.7)
def frame_face(canvas,j,box,speaking=False,leadframe=False,pose='rest'):
 x,y,w,h=map(round,box);panel=panel_background(w,h).copy()
 active=next((l for l in reversed(line)if l['stage']!='screen' and l['judge']==j and l['start']<=t<l['start']+l['dur']),None)
 frontal=any(l['stage']!='screen'and l['judge']==j and l['start']-policy['mouth']['hold_before']<=t<l['start']+l['dur']+policy['mouth']['hold_after'] for l in line)or pose=='smoke'
 source=rig_face(j,pose,t,active is not None,float(speaking),frontal)
 scale=min(w/source.width,h/source.height);iw=round(source.width*scale);ih=round(source.height*scale);key=(asset_ids.get(id(source)),iw,ih)
 if key[0] is not None:
  if key not in scaled:scaled[key]=source.resize((iw,ih),Image.Resampling.LANCZOS)
  face=scaled[key]
 else:face=source.resize((iw,ih),Image.Resampling.LANCZOS)
 panel.alpha_composite(face,((w-iw)//2,h-ih))
 mask=Image.new('L',(w,h));ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=18,fill=255);canvas.paste(panel,(x,y),mask);ImageDraw.Draw(canvas).rounded_rectangle((x,y,x+w,y+h),radius=18,outline='#fff7e5'if active else'#e9c68c',width=4 if active else 3)
def feedback(t,c,question=None):
 global lead
 previous_lead=lead
 # Lead and supporting judges remain in their assigned frames.

 if lead!=previous_lead and 'vincent' in rigstates:rigstates['vincent']['cigarette']=False
 canvas=studio.copy();logo_on(canvas,105,17,180);others=[j for j in ['dante','rosa','vincent']if j!=lead];boxes=[(20,97,350,310),(20,420,169,183),(202,420,169,183)]
 poses=directed_poses(t)
 for j,box in zip([lead]+others,boxes):frame_face(canvas,j,box,max([mouth(l,t)for l in line if l['judge']==j and l['start']<=t<l['start']+l['dur']],default=0),j==lead,poses.get(j,'rest'))
 if c:
  groups=balanced(c['text'],85);progress=min(len(groups)-1,int((t-c['start'])/max(.1,c['dur'])*len(groups)))
  d=ImageDraw.Draw(canvas);d.text((195,626),name[c['judge']].upper(),font=font(10,True),fill='#ffe0ac',anchor='mm',stroke_width=1,stroke_fill='#382015')
  ls=wrapped(groups[progress],336,17)
  for n,l in enumerate(ls):d.text((195,650+n*23),l,font=font(17,True),fill='#fff9e9',anchor='mm',stroke_width=1,stroke_fill='#382015')
 if question:
  d=ImageDraw.Draw(canvas)
  for n,l in enumerate(wrapped(ep.get('creator_name','You')+': '+question['question'],340,23)):d.text((195,700+n*30),l,font=font(23,True),fill='#fff7e5',anchor='mm',stroke_width=1,stroke_fill='#392015')
 elif c and c.get('stage')=='invite':ImageDraw.Draw(canvas).rounded_rectangle((100,727,290,784),radius=15,fill='#ffcc41',outline='#4c2412',width=3);ImageDraw.Draw(canvas).text((195,755),'ASK!',font=font(26,True),fill='#3b210f',anchor='mm')
 waiting=next((a,b)for a,b in windows if a<=t<b)if any(a<=t<b for a,b in windows)else None
 if waiting:
  d=ImageDraw.Draw(canvas);d.rounded_rectangle((100,727,290,784),radius=15,fill='#ffcc41',outline='#4c2412',width=3);d.text((195,755),'ASK!  '+str(max(0,math.ceil(6-(t-waiting[0])))),font=font(26,True),fill='#3b210f',anchor='mm')
 return canvas
def scorecard(t):
 dt=t-scorestart;canvas=studio.copy();fit=ImageOps.contain(video_at(dt%clipdur),(W,H),Image.Resampling.LANCZOS);canvas.alpha_composite(fit,((W-fit.width)//2,(H-fit.height)//2));canvas.alpha_composite(Image.new('RGBA',(W,H),(43,23,12,110)));d=ImageDraw.Draw(canvas)
 d.text((195,90),'THE VERDICT',font=font(39,True),fill='#fff0ce',anchor='mm',stroke_width=2,stroke_fill='#2b150b')
 for i,j in enumerate(['vincent','dante','rosa']):
  elapsed=dt-(.45+i*.95)
  if elapsed<0:continue
  cx=72+i*123;put(canvas,ImageOps.fit(img(PUB/f'art-rig/canonical-{j}-closed.png'),(61,81),centering=(.5,.15)),(cx-30,177,61,81));d.rounded_rectangle((cx-31,176,cx+31,259),radius=8,outline='#edcda1',width=3)
  value=str(ep['scores'][j])if elapsed>=.65 else f'{int(elapsed/.65*37)%10:.1f}';d.text((cx,294),value,font=font(42,True),fill='#fff3d4',anchor='mm',stroke_width=2,stroke_fill='#2b150b');d.text((cx,330),'/10 · '+name[j],font=font(10),fill='#ffedcc',anchor='mm')
  if any(c.get('buzz')and c['judge']==j for c in ep['screening']):d.text((cx+35,176),'×',font=font(39,True),fill='#ff3434',anchor='mm',stroke_width=2,stroke_fill='#fff6db')
 if dt>=3.9:
  points=[]
  for k in range(28):
   a=k*math.pi/14-math.pi/2;r=1 if k%2==0 else .73;points.append((195+120*r*math.cos(a),468+85*r*math.sin(a)))
  d.polygon(points,fill='#eaa945',outline='#30190b',width=3);d.text((195,431),'THE PANEL’S SCORE',font=font(12,True),fill='#30190c',anchor='mm');d.text((187,481),f'{sum(ep["scores"].values())/3:.1f}',font=font(76,True),fill='#fff4dc',anchor='mm',stroke_width=2,stroke_fill='#30190b');d.text((274,499),'/10',font=font(20,True),fill='#fff4dc',anchor='mm',stroke_width=1,stroke_fill='#30190b')
 return canvas
def progress(percent,phase):
 if data.get('progress_file'):
  p=Path(data['progress_file']);tmp=p.with_suffix('.progress-tmp');tmp.write_text(json.dumps({'percent':percent,'phase':phase}));tmp.replace(p)
progress(1,'Preparing pictures')
out.parent.mkdir(parents=True,exist_ok=True);silent=out.with_suffix('.silent.mp4');cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',str(silent)];proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for f in range(math.ceil(total*FPS)):
 if f%FPS==0:progress(round(5+f/(total*FPS)*85),'Assembling your show')
 t=f/FPS;c=next((l for l in reversed(line)if l['start']<=t<l['start']+l['dur']),None)
 if t<transitionstart:canvas=screening(t,c)
 elif t<transitionend:canvas=transition(t)
 elif t>=scorestart:canvas=scorecard(t)
 else:
  segment=next((seg for seg in segments if seg[0]<=t<seg[1]),None);q=segment[3]if segment and segment[2]=='question'else None;canvas=feedback(t,c,q)
 proc.stdin.write(canvas.convert('RGB').tobytes())
proc.stdin.close();assert proc.wait()==0
progress(94,'Adding voices and sound')
cmd=['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(EPDIR/'source-audio.mp3')];filters=[f'[1:a]volume=0.30,adelay={round(screenstart*1000)}|{round(screenstart*1000)}[music]'];labels=['[music]']
for i,l in enumerate(line):cmd+=['-i',str(audio_path(l))];label=f'a{i}';filters.append(f'[{i+2}:a]adelay={round(l["start"]*1000)}|{round(l["start"]*1000)}[{label}]');labels.append(f'[{label}]')
for k,eff in enumerate(effects):
 i=len(line)+2+k;cmd+=['-i',str(ROOT/'sfx'/f"{eff['kind']}.mp3")];label=f'fx{k}';filters.append(f'[{i}:a]adelay={round(eff["start"]*1000)}|{round(eff["start"]*1000)}[{label}]');labels.append(f'[{label}]')
filters.append(''.join(labels)+f'amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95:level=false,afade=t=out:st={total-2}:d=2[mix]');cmd+=['-filter_complex',';'.join(filters),'-map','0:v','-map','[mix]','-c:v','copy','-c:a','aac','-b:a','256k','-t',str(total),'-movflags','+faststart',str(out)];subprocess.run(cmd,check=True);silent.unlink();progress(100,'Ready');print('Rendered',out,'duration',round(total,2))
