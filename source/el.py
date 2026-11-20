import json, base64, subprocess, sys, urllib.request, os
VOICE='3SJr1mBO9EjMaZpJooQ1'
L=["Introducing a double storey terrace house, located at Shah Alam, Section 30.",
"A modern and practical home, designed for comfortable family living.",
"Featuring a modern facade, contemporary design, and large windows that bring in natural light.",
"A spacious ground floor with a welcoming living area, and a well-planned dining space. Perfect for family time and entertaining.",
"A practical kitchen with ample storage, and good ventilation, for everyday convenience.",
"Upstairs, find comfortable bedrooms that offer privacy, and a relaxing space for the whole family.",
"Enjoy a strategic location in Shah Alam, Section 30, with easy access to schools, shopping and dining, major highways, and recreational areas.",
"A double storey terrace house in Shah Alam, Section 30. A practical, family-friendly home, in a great location.",
"Interested in this home? Contact us today to find out more, or arrange a viewing."]
speed=float(sys.argv[2]) if len(sys.argv)>2 else 1.0
idx=[int(x) for x in sys.argv[1].split(',')] if len(sys.argv)>1 and sys.argv[1]!='all' else range(1,10)
for i in idx:
    t=L[i-1]
    body=json.dumps({"text":t,"model_id":"eleven_multilingual_v2",
        "voice_settings":{"stability":0.5,"similarity_boost":0.8,"style":0.15,"use_speaker_boost":True,"speed":speed},
        "previous_text": L[i-2] if i>1 else None, "next_text": L[i] if i<9 else None}).encode()
    req=urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128',
        data=body, headers={'xi-api-key':'proxy-injected','Content-Type':'application/json'})
    d=json.load(urllib.request.urlopen(req, timeout=120))
    open(f'el/{i}.mp3','wb').write(base64.b64decode(d['audio_base64']))
    json.dump(d['alignment'],open(f'el/{i}.json','w'))
    dur=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f'el/{i}.mp3'],capture_output=True,text=True).stdout.strip()
    a=d['alignment']; print(i, dur, 'speech end', a['character_end_times_seconds'][-1], flush=True)
