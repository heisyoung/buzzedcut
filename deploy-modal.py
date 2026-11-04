from pathlib import Path
import os,modal
ROOT=Path(__file__).resolve().parent if modal.is_local() else Path('/app')
image=(modal.Image.debian_slim(python_version='3.12').apt_install('nodejs','npm','ffmpeg','fonts-liberation').pip_install('pillow','numpy').add_local_dir(ROOT/'backend','/app/backend').add_local_dir(ROOT/'public','/app/public'))
app=modal.App('buzzed-cut-v1')
volume=modal.Volume.from_name('buzzed-cut-v1-data',create_if_missing=True,version=2)
secret=modal.Secret.from_name('buzzed-cut-api-keys')
@app.function(image=image,secrets=[secret],volumes={'/data':volume},cpu=4,memory=4096,timeout=600,scaledown_window=600,min_containers=1,max_containers=1)
@modal.concurrent(max_inputs=40)
@modal.web_server(8000,startup_timeout=60)
def web():
 import subprocess,shutil,threading,time
 from pathlib import Path
 for source in Path('/app/samples').glob('*'):
  dest=Path('/data/shows')/source.name
  if not dest.exists():shutil.copytree(source,dest)
 for repair in Path('/app/repairs').glob('*'):
  dest=Path('/data/shows')/repair.name
  if dest.exists() and (not (dest/'revision.txt').exists() or (dest/'revision.txt').read_text()!=(repair/'revision.txt').read_text()):
   shutil.copytree(repair,dest,dirs_exist_ok=True)
 def sync():
  while True:
   time.sleep(15)
   try:volume.commit()
   except Exception:pass
 threading.Thread(target=sync,daemon=True).start()
 env={**os.environ,'PORT':'8000','BUZZED_DATA':'/data','BUZZED_VOICE_CACHE':'/data/voice-cache','BUZZED_FONT':'/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf','BUZZED_FONT_BOLD':'/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'}
 subprocess.Popen(['node','server.mjs'],cwd='/app/backend',env=env)
