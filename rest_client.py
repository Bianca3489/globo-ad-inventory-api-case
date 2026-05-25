"""
rest_client.py
--------------
Cliente REST de demonstração. Executa chamadas reais contra a API
rodando localmente em http://localhost:8000.

Uso:
    # 1. Em outro terminal, suba a API:
    #    uvicorn app.main:app --reload
    #
    # 2. Rode este script:
    #    python rest_client.py
"""

import json
import sys
import httpx

BASE_URL = "http://localhost:8000"


def pretty(label: str, response: httpx.Response):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  STATUS: {response.status_code}")
    print(f"{'='*60}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    except Exception:
        print(response.text)


def main():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:

        # ── Health check ──────────────────────────────────────────────────────
        r = client.get("/health")
        pretty("GET /health", r)

        # ── Endpoint /program ─────────────────────────────────────────────────
        # Ajuste program_code e exhibition_date conforme os dados reais
        r = client.get("/program", params={
            "program_code": "HUCK",
            "exhibition_date": "2020-08-01",
        })
        pretty("GET /program  (HUCK, 2020-08-01)", r)

        # ── Endpoint /period ──────────────────────────────────────────────────
        r = client.get("/period", params={
            "start_date": "2020-07-25",
            "end_date": "2020-08-08",
        })
        pretty("GET /period  (2020-07-25 → 2020-08-08)", r)

        # ── Erros esperados ───────────────────────────────────────────────────
        r = client.get("/program", params={
            "program_code": "INEXISTENTE",
            "exhibition_date": "2020-08-01",
        })
        pretty("GET /program  (programa inexistente – espera 404)", r)

        r = client.get("/period", params={
            "start_date": "2020-08-10",
            "end_date": "2020-08-01",
        })
        pretty("GET /period  (datas invertidas – espera 422)", r)


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print(
            "\n[ERRO] Não foi possível conectar em http://localhost:8000\n"
            "Certifique-se de que a API está rodando:\n"
            "  uvicorn app.main:app --reload\n",
            file=sys.stderr,
        )
        sys.exit(1)
