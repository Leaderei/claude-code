#!/usr/bin/env python3
"""Enriquece (telefone/site/nota) uma lista de place ids via Place Details.

Resumivel: ignora ids que ja estao em dados/raw_detalhes.jsonl, para que uma
retentativa nunca pague duas vezes pelo mesmo registro.
"""
import json, os, sys, time, urllib.request

DET = "dados/raw_detalhes.jsonl"
CAMPOS = ",".join(["id", "displayName", "nationalPhoneNumber", "internationalPhoneNumber",
                   "websiteUri", "rating", "userRatingCount", "businessStatus"])


def main():
    key = os.environ["GKEY"]
    ids = json.load(open(sys.argv[1]))
    feitos = set()
    if os.path.exists(DET):
        for l in open(DET, encoding="utf-8"):
            try:
                feitos.add(json.loads(l)["id"])
            except Exception:
                pass
    fila = [i for i in ids if i not in feitos]
    print(f"{len(ids)} na lista | {len(ids)-len(fila)} ja feitos | {len(fila)} a consultar", flush=True)
    out = open(DET, "a", encoding="utf-8")
    ok = 0
    for n, pid in enumerate(fila, 1):
        req = urllib.request.Request(
            f"https://places.googleapis.com/v1/places/{pid}?languageCode=pt-BR",
            headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": CAMPOS})
        for t in range(3):
            try:
                d = json.loads(urllib.request.urlopen(req, timeout=30).read())
                out.write(json.dumps(d, ensure_ascii=False) + "\n")
                out.flush()
                ok += 1
                break
            except Exception as e:
                if t == 2:
                    print("ERR", pid, e, flush=True)
                else:
                    time.sleep(2 ** t)
        if n % 200 == 0:
            print(f"  {n}/{len(fila)}", flush=True)
    out.close()
    print(f"fim: {ok}/{len(fila)}", flush=True)


main()
