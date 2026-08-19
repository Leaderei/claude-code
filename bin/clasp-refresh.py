#!/usr/bin/env python3
"""Renova o access_token do clasp usando o refresh_token guardado.

O clasp nao regrava ~/.clasprc.json depois de renovar o token em memoria, entao
o arquivo em disco envelhece ate o access_token vencer -- e ai ele pede
`clasp login` de novo. Este script faz o refresh e *persiste* o resultado.

Enquanto o refresh_token continuar valido, `clasp login` deixa de ser necessario.

Uso:
    clasp-refresh.py              # renova se faltar menos de 10 min pro vencimento
    clasp-refresh.py --force      # renova sempre
    clasp-refresh.py --status     # so mostra o estado, nao escreve nada
    clasp-refresh.py --file PATH  # usa outro arquivo de credenciais

Saida: 0 = tudo certo (ou nao precisava renovar)
       3 = refresh_token morto, precisa de `clasp login` de verdade
       1 = outro erro
"""

import argparse
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://oauth2.googleapis.com/token"
MARGEM_MS = 10 * 60 * 1000  # renova quando faltar menos de 10 minutos
BACKUP_DIR = os.path.expanduser("~/.claude/clasp")


def log(msg):
    print(f"[clasp-refresh] {msg}", file=sys.stderr)


def achar_dicts(node):
    """Percorre a arvore JSON e devolve todo dict encontrado.

    O formato do .clasprc.json mudou entre as versoes do clasp (v2 usa
    {token, oauth2ClientSettings}, v3 reorganizou tudo), entao em vez de assumir
    um formato a gente procura as chaves onde elas estiverem.
    """
    encontrados = []
    if isinstance(node, dict):
        encontrados.append(node)
        for v in node.values():
            encontrados.extend(achar_dicts(v))
    elif isinstance(node, list):
        for v in node:
            encontrados.extend(achar_dicts(v))
    return encontrados


def primeira_chave(dicts, *nomes):
    """Devolve (dict, chave, valor) da primeira chave encontrada."""
    for d in dicts:
        for nome in nomes:
            if isinstance(d.get(nome), str) and d[nome]:
                return d, nome, d[nome]
    return None, None, None


def carregar(caminho):
    with open(caminho, "r", encoding="utf-8") as fh:
        return json.load(fh)


def gravar_atomico(caminho, dados):
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(dados, fh, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, caminho)


def salvar_backup(caminho):
    """Guarda uma copia da credencial boa, caso o arquivo original suma."""
    try:
        os.makedirs(BACKUP_DIR, mode=0o700, exist_ok=True)
        destino = os.path.join(BACKUP_DIR, "clasprc.backup.json")
        shutil.copy2(caminho, destino)
        os.chmod(destino, 0o600)
    except OSError as err:
        log(f"aviso: nao consegui gravar o backup ({err})")


def trocar_refresh_token(client_id, client_secret, refresh_token, timeout):
    corpo = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=corpo,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--file", default=os.path.expanduser("~/.clasprc.json"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--timeout", type=float, default=20.0)
    args = ap.parse_args()

    caminho = os.path.expanduser(args.file)

    if not os.path.exists(caminho):
        restaurado = os.path.join(BACKUP_DIR, "clasprc.backup.json")
        if os.path.exists(restaurado):
            log(f"{caminho} sumiu -- restaurando do backup")
            shutil.copy2(restaurado, caminho)
            os.chmod(caminho, 0o600)
        else:
            log(f"{caminho} nao existe. Rode `clasp login` uma vez.")
            return 3

    try:
        dados = carregar(caminho)
    except (OSError, ValueError) as err:
        log(f"nao consegui ler {caminho}: {err}")
        return 1

    dicts = achar_dicts(dados)
    d_refresh, _, refresh_token = primeira_chave(dicts, "refresh_token", "refreshToken")
    _, _, client_id = primeira_chave(dicts, "client_id", "clientId")
    _, _, client_secret = primeira_chave(dicts, "client_secret", "clientSecret")

    if not refresh_token:
        log("nenhum refresh_token no arquivo -- `clasp login` e inevitavel.")
        return 3
    if not (client_id and client_secret):
        log("client_id/client_secret ausentes no .clasprc.json.")
        log("Rode `clasp login` uma vez para regravar o arquivo completo.")
        return 3

    agora_ms = int(time.time() * 1000)
    expiry = d_refresh.get("expiry_date")
    if not isinstance(expiry, (int, float)):
        expiry = None
    restante_ms = (expiry - agora_ms) if expiry else None

    if args.status:
        if restante_ms is None:
            print("expiry_date: ausente (nao da pra saber; use --force)")
        else:
            mins = restante_ms / 60000
            estado = "valido" if restante_ms > 0 else "VENCIDO"
            print(f"access_token: {estado} ({mins:.1f} min)")
        print(f"refresh_token: presente ({len(refresh_token)} chars)")
        print(f"arquivo: {caminho}")
        return 0

    if not args.force and restante_ms is not None and restante_ms > MARGEM_MS:
        if not args.quiet:
            log(f"token ainda valido por {restante_ms / 60000:.0f} min -- nada a fazer")
        return 0

    try:
        novo = trocar_refresh_token(client_id, client_secret, refresh_token, args.timeout)
    except urllib.error.HTTPError as err:
        detalhe = err.read().decode("utf-8", "replace")
        if "invalid_grant" in detalhe:
            log("o refresh_token foi revogado ou expirou de vez.")
            log("Este e um dos poucos casos em que `clasp login` e mesmo necessario.")
            log("Rode `clasp-doctor.sh` para ver por que ele foi revogado.")
            return 3
        if "invalid_client" in detalhe:
            log("o client_id/client_secret do .clasprc.json nao vale mais.")
            log("Rode `clasp login` uma vez para regravar o arquivo.")
            return 3
        log(f"HTTP {err.code} do Google: {detalhe}")
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        log(f"falha de rede: {err}")
        return 1

    if "access_token" not in novo:
        log(f"resposta inesperada do Google: {novo}")
        return 1

    # Regrava no mesmo dict onde o refresh_token mora, preservando o formato.
    d_refresh["access_token"] = novo["access_token"]
    d_refresh["expiry_date"] = agora_ms + int(novo.get("expires_in", 3600)) * 1000
    for opcional in ("id_token", "scope", "token_type"):
        if opcional in novo:
            d_refresh[opcional] = novo[opcional]
    # O Google so devolve refresh_token novo quando gira a credencial.
    if novo.get("refresh_token"):
        d_refresh["refresh_token"] = novo["refresh_token"]

    try:
        gravar_atomico(caminho, dados)
    except OSError as err:
        log(f"nao consegui gravar {caminho}: {err}")
        return 1

    salvar_backup(caminho)
    if not args.quiet:
        log(f"token renovado -- valido por mais {int(novo.get('expires_in', 3600)) // 60} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
