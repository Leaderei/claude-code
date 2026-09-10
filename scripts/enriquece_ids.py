import json,os,sys,time,urllib.request
KEY=os.environ["GKEY"]
F=",".join(["id","displayName","nationalPhoneNumber","internationalPhoneNumber","websiteUri","rating","userRatingCount","businessStatus"])
ids=json.load(open(sys.argv[1]))
out=open("dados/raw_detalhes.jsonl","a",encoding="utf-8")
ok=0
for i,pid in enumerate(ids,1):
    url=f"https://places.googleapis.com/v1/places/{pid}?languageCode=pt-BR"
    req=urllib.request.Request(url,headers={"X-Goog-Api-Key":KEY,"X-Goog-FieldMask":F})
    for t in range(3):
        try:
            d=json.loads(urllib.request.urlopen(req,timeout=30).read())
            out.write(json.dumps(d,ensure_ascii=False)+"\n"); out.flush(); ok+=1; break
        except Exception as e:
            if t==2: print("ERR",pid,e)
            else: time.sleep(2**t)
    if i%20==0: print(i,flush=True)
out.close(); print("fim:",ok,"/",len(ids))
