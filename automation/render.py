from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,subprocess,math,wave,struct,shutil

def render(directory='run'):
 p=Path(directory); plan=json.loads((p/'plan.json').read_text()); fps=30; duration=8.5
 fonts=[Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),Path('C:/Windows/Fonts/segoeuib.ttf')]
 font_path=next(f for f in fonts if f.exists())
 def font(size): return ImageFont.truetype(str(font_path),size)
 def card(name):
  image=Image.open(p/name).convert('RGB'); crop_height=min(image.height,round(image.width*132/310))
  return image.crop((0,0,image.width,crop_height)).resize((930,396),Image.Resampling.LANCZOS)
 before,after,empty=[card(f) for f in ('before.png','after.png','empty.png')]
 exe=shutil.which('ffmpeg')
 if not exe:
  import imageio_ffmpeg
  exe=imageio_ffmpeg.get_ffmpeg_exe()
 with (p/'encode.log').open('wb') as log:
  proc=subprocess.Popen([exe,'-y','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r','30','-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(p/'silent.mp4')],stdin=subprocess.PIPE,stderr=log,stdout=log)
  for n in range(round(fps*duration)):
   t=n/fps; image=Image.new('RGB',(1080,1920),'#f4f3ed'); d=ImageDraw.Draw(image)
   d.rounded_rectangle((70,130,1010,225),25,fill='#102a27'); d.text((105,146),'PasteGuard',font=font(48),fill='#a1efc6')
   d.text((975,160),'WEBSITE DEMO',font=font(24),fill='white',anchor='rt')
   hook=plan['hook'] if t<2.5 else ('Paste once' if t<3.5 else ('Keep context' if t<5.5 else 'Try free'))
   face=font(90)
   while d.textlength(hook,font=face)>940:face=font(face.size-2)
   d.text((70,270),hook,font=face,fill='#112d2a')
   d.text((74,394),'Link in bio.' if t>=5.5 else plan['example']['subtitle'],font=font(37),fill='#43534e')
   for y,label,color,frame in [(520,'BEFORE','#a23d2e',before),(1080,'AFTER','#1b7154',after)]:
    d.rounded_rectangle((60,y,1020,y+490),28,fill='white',outline='#d7dfd7',width=3)
    demo=label=='AFTER' and 2.5<=t<3.0
    d.text((92,y+23),'PASTE DEMO' if demo else label,font=font(31),fill=color)
    image.paste(empty if demo else frame,(75,y+78))
   if t>=5.5:
    d.rounded_rectangle((70,1610,1010,1710),24,fill='#102a27');d.text((540,1622),'Link in bio',font=font(55),fill='#a1efc6',anchor='mt')
   else:d.text((540,1630),'Fake data · real browser demo',font=font(31),fill='#43534e',anchor='mt')
   d.text((540,1750),'pasteguard.pages.dev',font=font(46),fill='#112d2a',anchor='mt')
   d.text((540,1830),'Can miss secrets. Review before sharing.',font=font(27),fill='#43534e',anchor='mt')
   d.text((540,1870),'Edited comparison · not a speed benchmark',font=font(23),fill='#43534e',anchor='mt')
   if n==0:image.save(p/'cover.jpg',quality=95)
   if n in (0,90,210):image.save(p/f'proof-{n}.jpg',quality=95)
   proc.stdin.write(image.tobytes())
  proc.stdin.close()
  if proc.wait()!=0:raise RuntimeError('Encoding failed')
 sr=48000;pcm=bytearray()
 for n in range(round(sr*duration)):
  t=n/sr;env=min(1,t/.12)*min(1,(duration-t)/.3)
  value=.01*env*sum(math.sin(2*math.pi*f*t)*math.exp(-(t%1.5)*1.2) for f in (220,261.63,329.63))
  pcm.extend(struct.pack('<h',round(value*32767)))
 with wave.open(str(p/'audio.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm)
 subprocess.run([exe,'-y','-i',str(p/'silent.mp4'),'-i',str(p/'audio.wav'),'-c:v','copy','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(p/'video.mp4')],check=True,capture_output=True)
 subprocess.run([exe,'-v','error','-i',str(p/'video.mp4'),'-f','null','-'],check=True,capture_output=True)
 (p/'caption.txt').write_text(plan['caption'],encoding='utf-8')
 (p/'verification.json').write_text(json.dumps({'seconds':duration,'width':1080,'height':1920,'fps':fps,'audio':'Original quiet synthesized chords, no voiceover','decode_passed':True,'source':'Fresh website comparison; real clipboard paste; fake data; edited timing'},indent=2))
if __name__=='__main__':render()
