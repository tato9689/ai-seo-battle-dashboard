#!/usr/bin/env python3
"""Envía a Search Console el sitemap de cada agente. Operación puntual.

Por qué un script aparte y no una función del poller: el poller corre a
diario y sus credenciales se piden con `webmasters.readonly` a propósito —un
token de solo lectura no puede borrar un sitemap ni una propiedad por error.
Enviar un sitemap necesita el scope de escritura `.../auth/webmasters`, así
que se pide aquí y solo aquí, cuando lo lanza una persona.

El 2026-09-01 esto fallaba con 403 "insufficient authentication scopes" y
parecía un problema de permisos de la cuenta de servicio. No lo era: el nivel
en las 4 propiedades ya era `siteFullUser`. Era el scope. Si vuelve a salir
un 403, mira primero cuál de las dos cosas es — el mensaje no lo distingue
bien.

Uso: enviar_sitemaps.py [--listar]
"""
import json
import sys
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

BASE = Path(__file__).parent
SCOPES_ESCRITURA = ["https://www.googleapis.com/auth/webmasters"]


def servicio(cfg):
    creds = service_account.Credentials.from_service_account_file(
        cfg["google_service_account"], scopes=SCOPES_ESCRITURA
    )
    return build("searchconsole", "v1", credentials=creds)


def main():
    cfg = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
    s = servicio(cfg)
    solo_listar = "--listar" in sys.argv
    fallos = 0
    for a in cfg.get("agentes", []):
        site = a.get("gsc_site")
        if not site:
            print(f"{a['ia']:9} sin gsc_site en config.json")
            continue
        sitemap = site.rstrip("/") + "/sitemap.xml"
        if not solo_listar:
            try:
                s.sitemaps().submit(siteUrl=site, feedpath=sitemap).execute()
            except Exception as e:
                print(f"{a['ia']:9} FALLO al enviar: {str(e)[:160]}", file=sys.stderr)
                fallos += 1
                continue
        try:
            r = s.sitemaps().list(siteUrl=site).execute()
            for sm in r.get("sitemap", []):
                estado = "pendiente de procesar" if sm.get("isPending") else "procesado"
                errores = sm.get("errors", 0)
                avisos = sm.get("warnings", 0)
                urls = sum(int(c.get("submitted", 0)) for c in sm.get("contents", []))
                print(f"{a['ia']:9} {sm['path'].split('/')[-1]:14} {estado:22} "
                      f"{urls:3} urls · {errores} errores · {avisos} avisos")
            if not r.get("sitemap"):
                print(f"{a['ia']:9} sin sitemaps registrados")
        except Exception as e:
            print(f"{a['ia']:9} no se pudo listar: {str(e)[:120]}", file=sys.stderr)
            fallos += 1
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
