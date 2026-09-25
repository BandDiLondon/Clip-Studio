import numpy as np, subprocess, os, math, json
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from multiprocessing import Pool
os.chdir('/root/av')
W,H = 1920,1080
FPS = 30
DUR = 143.59
NF = int(round(DUR*FPS))
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SM = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
beats = np.load('beats_adapt.npy').tolist()

# case switch events: (time, planche, case_index)
EVENTS = [
 (0.00,'P1',1),(19.32,'P1',1),(22.20,'P1',2),(24.76,'P1',3),(27.16,'P1',4),
 (29.66,'P2',5),(32.04,'P2',6),
 (39.82,'P3',1),(42.02,'P3',2),(44.06,'P3',3),(47.08,'P3',4),
 (49.40,'P2',5),(51.70,'P2',6),
 (70.54,'P4',1),(71.22,'P4',1),(73.52,'P4',2),(75.94,'P4',3),(78.36,'P4',4),
 (81.24,'P2',5),(83.52,'P2',6),
 (103.72,'P5',1),(105.32,'P5',1),(107.98,'P5',2),(110.92,'P5',3),(113.24,'P5',4),
 (115.84,'P2',5),(117.90,'P2',6),
 (123.18,'P6',1),(127.12,'P6',2),(142.14,'P6',2),
]
EVENTS.sort()
def case_for(t):
    cur=('P2',1)
    for tm,p,c in EVENTS:
        if tm<=t: cur=(p,c)
        else: break
    return f'cases/{cur[0].lower()}_c{cur[1]}.jpg'

segs = json.load(open('av_words_fixed.json'))['segments']
def word_at(t):
    for seg in segs:
        if seg['start']<=t<seg['end']:
            cur=''
            for w in seg['words']:
                if w['s']<=t<w['e']: cur=w['w']; break
            return seg['text'], cur
    return None,None

# --- travelling segments: (start, end, solo_image) ---
TRAVEL = [
 (17.16,19.32,'solos/solo1.webp'),
 (35.16,39.82,'solos/solo2.webp'),
 (55.16,70.54,'solos/solo3.webp'),
 (70.54,71.22,'solos/solo4.webp'),
 (87.52,103.72,'solos/solo1.webp'),
 (103.72,105.32,'solos/solo2.webp'),
 (121.92,123.18,'solos/solo3.webp'),
 (128.92,142.14,'solos/solo4.webp'),
 (142.14,143.54,'solos/solo1.webp'),
]
def travel_for(t):
    for s,e,img in TRAVEL:
        if s<=t<e: return (s,e,img)
    return None

CACHE={}
def prep(case):
    if case in CACHE: return CACHE[case]
    im=Image.open(case).convert('RGB')
    cw,ch=im.size
    scale=max(W/cw,H/ch)
    bw,bh=int(round(cw*scale)),int(round(ch*scale))
    base=im.resize((bw,bh),Image.LANCZOS)
    base=base.filter(ImageFilter.UnsharpMask(radius=2,percent=120,threshold=3))
    CACHE[case]=base
    return base

# pano cache for travelling
PCACHE={}
def pano_prep(path):
    if path in PCACHE: return PCACHE[path]
    im=Image.open(path).convert('RGB')
    # upscale x6 for smooth travelling
    im=im.resize((im.width*6, im.height*6), Image.LANCZOS)
    im=im.filter(ImageFilter.UnsharpMask(radius=2,percent=120,threshold=3))
    PCACHE[path]=im
    return im

def load_fonts():
    return ImageFont.truetype(FONT_PATH,44),ImageFont.truetype(FONT_SM,30)

def wrap_words(wlist,font,maxw):
    lines=[]; cur=[]; cw=0
    for w in wlist:
        wl=draw_textlen(w+' ',font)
        if cw+wl>maxw and cur:
            lines.append(cur); cur=[w]; cw=wl
        else:
            cur.append(w); cw+=wl
    if cur: lines.append(cur)
    return lines
def draw_textlen(s,font):
    return ImageDraw.Draw(Image.new('RGB',(10,10))).textlength(s,font=font)

def render_travel_frame(t,start,end,path,fonts):
    pano=pano_prep(path)
    PW,PH=pano.size
    dur=end-start
    # camera glides left->right, then slow reverse (ping-pong), full travel
    ch=PH
    cw=int(ch*16/9)
    max_x=PW-cw
    # ease in-out across the width
    u=(t-start)/dur
    # ping-pong
    period=dur
    # glide left->right once (whole width) with easing
    import math as _m
    ease = (1-_m.cos(u*_m.pi))/2  # 0->1
    x=ease*max_x
    zoom=1.0+0.06*ease
    # beat pulse
    pulse=0.0
    for b in beats:
        d=t-b
        if -0.10<d<0.30:
            pulse=max(pulse,_m.exp(d/-0.09))
    zoom*= (1.0+0.02*pulse)
    cwz=int(cw/zoom); chz=int(ch/zoom)
    y=(PH-chz)//2
    x=int(min(max(x,0),PW-cwz))
    box=(x,y,x+cwz,y+chz)
    crop=pano.crop(box).resize((W,H),Image.LANCZOS)
    frame=crop
    if pulse>0.5:
        flash=Image.new('RGB',(W,H),(255,255,255))
        frame=Image.blend(frame,flash,(pulse-0.5)*0.18)
    return frame

def render_frame(t,fonts):
    tv=travel_for(t)
    if tv:
        return np.asarray(render_travel_frame(t,*tv,fonts)).tobytes()
    case=case_for(t)
    base=prep(case)
    bw,bh=base.size
    pulse=0.0
    for b in beats:
        d=t-b
        if -0.10<d<0.30:
            pulse=max(pulse,math.exp(d/-0.09))
    zoom=1.0+0.05*math.sin(t*0.6)+0.05*pulse
    zw=W/zoom; zh=H/zoom
    if zw>bw or zh>bh:
        z2=min(bw/W,bh/H)
        zw=W*z2; zh=H*z2
    left=(bw-zw)/2; top=(bh-zh)/2
    crop=base.crop((int(left),int(top),int(left+zw),int(top+zh))).resize((W,H),Image.LANCZOS)
    frame=crop
    if pulse>0.5:
        flash=Image.new('RGB',(W,H),(255,255,255))
        frame=Image.blend(frame,flash,(pulse-0.5)*0.22)
    txt,cur=word_at(t)
    if txt:
        font_b,font_s=fonts
        d=ImageDraw.Draw(frame)
        bar=Image.new('RGBA',(W,210),(0,0,0,150)); frame.paste(bar,(0,H-210),bar)
        wl=txt.split(' ')
        lines=wrap_words(wl,font_b,W-120)
        lh=56
        y=H-210+ (210-len(lines)*lh)//2 + 10
        for line in lines:
            total=sum(draw_textlen(w+' ',font_b) for w in line)
            x=(W-total)/2
            for wd in line:
                is_cur=(wd.strip(' ,.;!?\'"')==cur)
                d.text((x,y),wd+' ',font=font_b,
                       fill=(255,220,80) if is_cur else (255,255,255),
                       stroke_width=3,stroke_fill=(0,0,0))
                x+=draw_textlen(wd+' ',font_b)
            y+=lh
    return np.asarray(frame).tobytes()

def gen(args):
    fi=args; t=fi/FPS
    return render_frame(t,FONTS)

FONTS=load_fonts()
def main():
    ff=subprocess.Popen(['ffmpeg','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),
        '-i','-','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','video3.mp4'],
        stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for cs in range(0,NF,8):
            idxs=range(cs,min(cs+8,NF))
            for data in pool.imap(gen,idxs):
                ff.stdin.write(data)
    ff.stdin.close(); ff.wait(); print('done',ff.returncode)
if __name__=='__main__':
    main()
