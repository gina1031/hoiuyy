import numpy as np, wave
SR=44100; DUR=60.5; N=int(SR*DUR); t=np.arange(N)/SR
BPM=100; beat=60/BPM; bar=beat*4
def note(m): return 440*2**((m-69)/12)
prog=[[48,55,64,67],[43,55,62,67],[45,57,60,64],[41,57,60,65]]  # C G Am F
roots=[36,31,33,29]
music=np.zeros(N); 
def add(sig,start):
    i=int(start*SR); j=min(N,i+len(sig)); 
    if i<N: music[i:j]+=sig[:j-i]
# pad
for b in range(int(DUR/bar)+1):
    ch=prog[b%4]; st=b*bar; L=int(bar*SR*1.1); tt=np.arange(L)/SR
    env=np.minimum(1,tt/0.4)*np.minimum(1,np.maximum(0,(bar*1.1-tt)/0.5))
    sig=sum(np.sin(2*np.pi*note(m)*tt*(1+d))*0.5+0.18*np.sin(4*np.pi*note(m)*tt) for m in ch for d in (-0.002,0.002))
    add(sig*env*0.035,st)
    # bass
    for k in (0,2.5):
        L2=int(beat*1.4*SR); t2=np.arange(L2)/SR
        add(np.sin(2*np.pi*note(roots[b%4])*t2)*np.exp(-t2*2.2)*0.22, st+k*beat)
    # pluck arp eighths
    arp=[ch[0]+12,ch[2]+12,ch[1]+12,ch[3]+12,ch[2]+12,ch[1]+12,ch[3]+12,ch[2]+12]
    for k,m in enumerate(arp):
        L3=int(0.5*SR); t3=np.arange(L3)/SR
        add((np.sin(2*np.pi*note(m)*t3)+0.3*np.sin(4*np.pi*note(m)*t3))*np.exp(-t3*9)*0.06, st+k*beat/2)
# drums after 2 bars, stop before final 1.5s
rng=np.random.default_rng(1)
k_t=np.arange(int(0.35*SR))/SR
kick=np.sin(2*np.pi*(45*k_t+ (110/18)*(1-np.exp(-18*k_t))))*np.exp(-k_t*9)*0.55
hat=rng.standard_normal(int(0.05*SR)); hat=np.diff(hat,prepend=0)*np.exp(-np.arange(len(hat))/SR*90)*0.05
clap=rng.standard_normal(int(0.18*SR)); clap=np.diff(clap,prepend=0)*np.exp(-np.arange(len(clap))/SR*25)*0.07
b=0
x=2*bar
while x<DUR-2.5:
    add(kick,x)
    add(hat,x+beat/2)
    bi=round((x)/beat)
    if bi%2==1: add(clap,x)
    x+=beat
# end hit
L=int(2.5*SR); tt=np.arange(L)/SR
add(sum(np.sin(2*np.pi*note(m)*tt) for m in [48,55,64,67,72])*np.exp(-tt*1.5)*0.06, 58.0)
fade=np.minimum(1,t/1.0)*np.clip((DUR-t)/1.2,0,1)
music*=fade
music/=np.abs(music).max()*1.1
# whooshes at scene cuts
cuts=[5.0,9.5,16.3,24.3,30.1,34.9,37.1,46.5,53.9]
sfx=np.zeros(N)
for c in cuts:
    L=int(0.5*SR); n=rng.standard_normal(L)
    # simple swept bandpass via moving-average lowpass of varying width
    out=np.zeros(L); acc=0
    for i in range(L):
        a=0.02+0.4*(i/L)  # cutoff rising
        acc+= a*(n[i]-acc); out[i]=acc
    out=out-np.convolve(out,np.ones(40)/40,'same')
    env=np.sin(np.pi*np.arange(L)/L)**2
    i0=int((c-0.3)*SR); sfx[i0:i0+L]+=out*env
sfx/=np.abs(sfx).max(); sfx*=0.25
def wr(fn,x):
    x=np.clip(x,-1,1); s=(x*32767).astype(np.int16)
    st=np.stack([s,s],1)
    with wave.open(fn,'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
wr('music.wav',music); wr('sfx.wav',sfx)
