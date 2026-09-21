
import json, math, os, shutil, subprocess, sys, wave, struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
FRAMES = OUTPUT / "frames"
OUTPUT.mkdir(exist_ok=True)
FRAMES.mkdir(exist_ok=True)

W, H = 1280, 720
FPS = 24
SCENE_SECONDS = 3.5

PALETTES = [
    ((95, 205, 255), (205, 245, 255)),
    ((130, 220, 255), (235, 250, 255)),
    ((170, 225, 255), (255, 235, 205)),
    ((125, 220, 180), (230, 250, 205)),
]

def run(cmd):
    subprocess.run([str(x) for x in cmd], check=True)

def font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def text_center(draw, text, y, f, fill, stroke=0, stroke_fill="white"):
    b = draw.textbbox((0,0), text, font=f, stroke_width=stroke)
    x = (W-(b[2]-b[0]))/2
    draw.text((x,y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)

def background(draw, t, idx):
    top, bottom = PALETTES[idx % len(PALETTES)]
    for y in range(H):
        k=y/(H-1)
        c=tuple(int(top[i]*(1-k)+bottom[i]*k) for i in range(3))
        draw.line((0,y,W,y), fill=c)
    # moving clouds
    for bx, by, s in [(150,100,1.0),(610,65,.75),(1050,120,.9)]:
        x=bx+int(25*math.sin(t*.7+bx))
        for dx,dy,r in [(0,18,28),(30,0,35),(65,18,27)]:
            draw.ellipse((x+dx-r*s,by+dy-r*s,x+dx+r*s,by+dy+r*s),fill="white")
    # sun
    pulse=4+int(5*math.sin(t*2))
    draw.ellipse((1080-pulse,35-pulse,1190+pulse,145+pulse),fill=(255,220,70),outline=(255,180,45),width=5)
    # hills and ground
    draw.ellipse((-300,470,700,930),fill=(105,195,105))
    draw.ellipse((400,440,1550,930),fill=(80,180,95))
    # flowers
    for i in range(22):
        x=(i*83+37)%W
        y=585+(i*47)%100
        petal=[(255,105,135),(255,190,55),(255,255,255),(150,110,230)][i%4]
        for a in (0,90,180,270):
            dx=int(8*math.cos(math.radians(a))); dy=int(8*math.sin(math.radians(a)))
            draw.ellipse((x+dx-7,y+dy-7,x+dx+7,y+dy+7),fill=petal)
        draw.ellipse((x-5,y-5,x+5,y+5),fill=(255,210,50))

def child(draw, x, y, s, phase):
    y += int(7*math.sin(phase))
    # shadow
    draw.ellipse((x-75*s,y+185*s,x+75*s,y+215*s),fill=(50,100,80))
    # body
    draw.rounded_rectangle((x-62*s,y+55*s,x+62*s,y+190*s),radius=int(25*s),fill=(50,180,230),outline=(20,100,170),width=max(2,int(4*s)))
    # arms
    draw.line((x-48*s,y+75*s,x-105*s,y+25*s),fill=(225,170,125),width=max(5,int(18*s)))
    draw.line((x+48*s,y+75*s,x+105*s,y+25*s),fill=(225,170,125),width=max(5,int(18*s)))
    # hands
    draw.ellipse((x-120*s,y+5*s,x-90*s,y+35*s),fill=(230,175,130))
    draw.ellipse((x+90*s,y+5*s,x+120*s,y+35*s),fill=(230,175,130))
    # head
    draw.ellipse((x-78*s,y-90*s,x+78*s,y+66*s),fill=(235,180,135),outline=(145,90,65),width=max(2,int(4*s)))
    # hair
    draw.pieslice((x-82*s,y-110*s,x+82*s,y+25*s),180,360,fill=(65,45,35))
    # eyes
    for ex in (-28,28):
        draw.ellipse((x+(ex-9)*s,y-20*s,x+(ex+9)*s,y+3*s),fill="white")
        draw.ellipse((x+(ex-3)*s,y-16*s,x+(ex+4)*s,y-6*s),fill=(35,35,45))
    draw.arc((x-28*s,y+0,x+28*s,y+38*s),10,170,fill=(120,45,45),width=max(2,int(4*s)))
    # legs
    draw.line((x-28*s,y+185*s,x-40*s,y+245*s),fill=(35,80,150),width=max(5,int(18*s)))
    draw.line((x+28*s,y+185*s,x+40*s,y+245*s),fill=(35,80,150),width=max(5,int(18*s)))
    draw.ellipse((x-62*s,y+230*s,x-15*s,y+252*s),fill=(70,70,100))
    draw.ellipse((x+15*s,y+230*s,x+62*s,y+252*s),fill=(70,70,100))

def object_art(draw, word, x, y, s, t):
    w=word.lower()
    if w=="apple":
        draw.ellipse((x-48*s,y-48*s,x+48*s,y+48*s),fill=(235,55,70),outline=(170,30,45),width=4)
        draw.polygon([(x,y-40*s),(x+30*s,y-78*s),(x+6*s,y-8*s)],fill=(70,175,80))
        draw.line((x,y-38*s,x+9*s,y-70*s),fill=(100,65,35),width=max(2,int(6*s)))
    elif w=="ball":
        draw.ellipse((x-58*s,y-58*s,x+58*s,y+58*s),fill=(70,150,245),outline="white",width=5)
        draw.arc((x-58*s,y-58*s,x+58*s,y+58*s),20,160,fill=(255,90,100),width=10)
        draw.arc((x-58*s,y-58*s,x+58*s,y+58*s),200,340,fill=(255,220,70),width=10)
    elif w in {"cat","dog","rabbit","lion","tiger"}:
        colors={"cat":(245,170,180),"dog":(190,140,95),"rabbit":(245,245,245),"lion":(225,170,75),"tiger":(245,150,55)}
        c=colors[w]
        draw.ellipse((x-70*s,y-58*s,x+70*s,y+58*s),fill=c,outline=(100,80,70),width=4)
        draw.polygon([(x-55*s,y-35*s),(x-85*s,y-95*s),(x-20*s,y-55*s)],fill=c)
        draw.polygon([(x+55*s,y-35*s),(x+85*s,y-95*s),(x+20*s,y-55*s)],fill=c)
        for ex in (-25,25):
            draw.ellipse((x+(ex-7)*s,y-18*s,x+(ex+7)*s,y+1*s),fill=(30,30,35))
        draw.ellipse((x-6*s,y+7*s,x+6*s,y+19*s),fill=(120,55,65))
        draw.arc((x-24*s,y+4*s,x+24*s,y+35*s),10,170,fill=(120,55,65),width=3)
    elif w=="elephant":
        c=(165,175,195)
        draw.ellipse((x-78*s,y-55*s,x+78*s,y+55*s),fill=c,outline=(100,110,135),width=4)
        draw.ellipse((x-110*s,y-40*s,x-45*s,y+55*s),fill=(155,165,185))
        draw.ellipse((x+45*s,y-40*s,x+110*s,y+55*s),fill=(155,165,185))
        draw.line((x,y+5*s,x,y+95*s),fill=c,width=max(4,int(24*s)))
    elif w=="giraffe":
        c=(250,195,80)
        draw.ellipse((x-52*s,y-45*s,x+52*s,y+45*s),fill=c,outline=(170,120,45),width=4)
        draw.rectangle((x-24*s,y+28*s,x+24*s,y+135*s),fill=c)
        for dx,dy in [(-28,-2),(22,15),(-16,62),(16,105)]:
            draw.ellipse((x+(dx-10)*s,y+(dy-10)*s,x+(dx+10)*s,y+(dy+10)*s),fill=(150,100,55))
    elif w=="fish":
        draw.ellipse((x-75*s,y-38*s,x+58*s,y+38*s),fill=(80,190,235),outline=(30,120,170),width=4)
        draw.polygon([(x+50*s,y),(x+105*s,y-45*s),(x+105*s,y+45*s)],fill=(255,145,70))
        draw.ellipse((x-42*s,y-12*s,x-27*s,y+3*s),fill=(20,40,60))
    elif w=="kite":
        pts=[(x,y-75*s),(x+65*s,y),(x,y+75*s),(x-65*s,y)]
        draw.polygon(pts,fill=(245,75,110),outline="white")
        draw.line((x-65*s,y,x+65*s,y),fill=(255,220,70),width=5)
        draw.line((x,y+75*s,x+20*s,y+150*s),fill=(90,70,55),width=3)
    elif w in {"orange","sun"}:
        draw.ellipse((x-55*s,y-55*s,x+55*s,y+55*s),fill=(255,160,40),outline=(220,105,30),width=4)
    elif w=="parrot":
        draw.ellipse((x-55*s,y-65*s,x+55*s,y+65*s),fill=(70,185,105),outline=(30,120,70),width=4)
        draw.ellipse((x-20*s,y-45*s,x+28*s,y+3*s),fill=(245,240,180))
        draw.polygon([(x+28*s,y-18*s),(x+78*s,y-4*s),(x+28*s,y+8*s)],fill=(245,180,50))
        draw.ellipse((x,y-27*s,x+13*s,y-14*s),fill=(20,20,20))
    elif w=="queen":
        draw.ellipse((x-58*s,y-58*s,x+58*s,y+58*s),fill=(245,185,190),outline=(130,80,100),width=4)
        draw.polygon([(x-55*s,y-58*s),(x-32*s,y-105*s),(x,y-70*s),(x+32*s,y-105*s),(x+55*s,y-58*s)],fill=(255,205,60))
        for ex in (-22,22): draw.ellipse((x+(ex-6)*s,y-12*s,x+(ex+6)*s,y+2*s),fill=(35,35,45))
    elif w=="umbrella":
        draw.pieslice((x-75*s,y-60*s,x+75*s,y+75*s),180,360,fill=(240,90,130),outline="white")
        draw.line((x,y,x,y+100*s),fill=(80,80,80),width=max(3,int(7*s)))
        draw.arc((x-10*s,y+85*s,x+35*s,y+130*s),0,180,fill=(80,80,80),width=5)
    elif w=="van":
        draw.rounded_rectangle((x-95*s,y-45*s,x+95*s,y+50*s),radius=int(15*s),fill=(255,205,70),outline=(120,100,50),width=4)
        draw.rectangle((x-55*s,y-30*s,x+45*s,y+8*s),fill=(120,205,240))
        for wx in (-55,55): draw.ellipse((x+(wx-22)*s,y+28*s,x+(wx+22)*s,y+72*s),fill=(45,50,60))
    elif w=="whale":
        draw.ellipse((x-105*s,y-45*s,x+90*s,y+45*s),fill=(75,155,220),outline=(35,100,165),width=4)
        draw.polygon([(x+75*s,y),(x+135*s,y-55*s),(x+135*s,y+55*s)],fill=(75,155,220))
        draw.ellipse((x+25*s,y-15*s,x+40*s,y),fill=(20,30,50))
        draw.arc((x-20*s,y-85*s,x+40*s,y-20*s),180,360,fill=(75,155,220),width=10)
    elif w=="xylophone":
        bars=[(255,90,100),(255,175,60),(255,225,70),(90,190,120),(75,150,235),(150,95,220)]
        for i,c in enumerate(bars):
            yy=y-45*s+i*18*s
            draw.rounded_rectangle((x-80*s+i*10*s,yy,x+80*s-i*10*s,yy+14*s),radius=5,fill=c)
    elif w=="yo-yo":
        draw.ellipse((x-45*s,y-45*s,x+45*s,y+45*s),fill=(245,80,100),outline="white",width=4)
        draw.line((x,y-45*s,x+35*s,y-120*s),fill=(80,70,60),width=3)
    elif w=="zebra":
        c=(245,245,245)
        draw.ellipse((x-75*s,y-55*s,x+75*s,y+55*s),fill=c,outline=(70,70,70),width=4)
        for dx in (-45,-20,10,40):
            draw.line((x+dx*s,y-40*s,x+(dx+20)*s,y+40*s),fill=(55,55,65),width=max(3,int(8*s)))
        draw.ellipse((x-25*s,y-12*s,x-10*s,y+3*s),fill=(25,25,25))
    else:
        draw.ellipse((x-55*s,y-55*s,x+55*s,y+55*s),fill=(255,180,80),outline="white",width=4)

def make_music(path, duration):
    rate=22050
    n=int(rate*duration)
    notes=[261.63,329.63,392.00,329.63,293.66,349.23,440.00,349.23]
    with wave.open(str(path),"w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        for i in range(n):
            t=i/rate
            beat=int(t*2)%len(notes)
            f=notes[beat]
            v=0.11*math.sin(2*math.pi*f*t)+0.05*math.sin(2*math.pi*f*2*t)
            fade=min(1,t/0.2,(duration-t)/0.3 if duration-t>0 else 0)
            sample=int(max(-1,min(1,v*fade))*32767)
            wf.writeframes(struct.pack("<h",sample))

def voice(text, path):
    run(["espeak-ng","-s","145","-p","62","-v","en","-w",path,text])

def main():
    script=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/"scripts"/"abc-song.json"
    data=json.loads(script.read_text(encoding="utf-8"))
    # Clean prior generated frames/clips.
    if FRAMES.exists(): shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True,exist_ok=True)
    for p in OUTPUT.glob("clip_*.mp4"): p.unlink()
    for p in OUTPUT.glob("voice_*.wav"): p.unlink()
    for p in OUTPUT.glob("music*.wav"): p.unlink()
    final=OUTPUT/"sharvinkidstv-abc-song-v2.mp4"
    clips=[]
    for si,scene in enumerate(data["scenes"],1):
        frames=FRAMES/f"scene_{si:02d}"
        frames.mkdir()
        for fi in range(int(SCENE_SECONDS*FPS)):
            t=fi/FPS
            im=Image.new("RGB",(W,H))
            d=ImageDraw.Draw(im)
            background(d,t,si)
            # object floats and bounces
            ox=930+int(35*math.sin(t*1.8+si))
            oy=360+int(25*math.sin(t*2.4+si))
            object_art(d,scene["word"],ox,oy,1.55, t)
            # child waves/bounces
            child(d,330,405,1.25,t*2.2)
            # animated letter badge
            scale=1+0.08*math.sin(t*3)
            bx,by=635,170
            r=int(120*scale)
            d.ellipse((bx-r,by-r,bx+r,by+r),fill=(255,240,95),outline=(255,175,45),width=8)
            text_center(d,scene["letter"],115,font(150,True),(235,70,100),6,"white")
            # word/lyrics panel
            rounded(d,(460,520,1220,665),35,(255,255,255),outline=(255,205,70),width=5)
            text_center(d,scene["line"],548,font(38,True),(45,70,120),2,"white")
            # branding
            rounded(d,(25,25,300,78),20,(255,255,255))
            d.text((45,38),"SharvinKidsTV",font=font(28,True),fill=(220,55,95))
            # sparkle animation
            for k in range(10):
                a=t*2+k
                sx=635+int(260*math.cos(a))
                sy=170+int(170*math.sin(a*1.3))
                rr=3+int(3*(1+math.sin(a*3)))
                d.ellipse((sx-rr,sy-rr,sx+rr,sy+rr),fill=(255,255,255))
            im.save(frames/f"{fi:04d}.png",quality=90)
        voice_file=OUTPUT/f"voice_{si:02d}.wav"
        voice(scene["line"],voice_file)
        clip=OUTPUT/f"clip_{si:02d}.mp4"
        run(["ffmpeg","-y","-framerate",FPS,"-i",frames/"%04d.png","-i",voice_file,
             "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
             "-c:a","aac","-shortest",clip])
        clips.append(clip)
    concat=OUTPUT/"concat.txt"
    concat.write_text("\n".join(f"file '{p.resolve()}'" for p in clips)+"\n",encoding="utf-8")
    joined=OUTPUT/"joined.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat,"-c","copy",joined])
    music=OUTPUT/"music.wav"
    make_music(music,len(data["scenes"])*SCENE_SECONDS)
    run(["ffmpeg","-y","-i",joined,"-i",music,"-filter_complex",
         "[1:a]volume=0.18[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]",
         "-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-shortest",final])
    print(f"Created: {final}")

if __name__=="__main__":
    main()
