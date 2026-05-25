"""
main.py
-------
REST API para o algoritmo de otimização de agenda de anúncios da TV Globo.

Endpoints
---------
GET /program   ?program_code=&exhibition_date=YYYY-MM-DD
GET /period    ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
GET /health
"""

from datetime import date
from typing import List

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from app.preprocessing import get_master_df
from app.schemas import PeriodResponse, ProgramEntry, ProgramResponse

app = FastAPI(
    title="TV Aberta – Ad Inventory & Audience API",
    description=(
        "Fornece a quantidade de segundos disponíveis para anúncios e a "
        "audiência prevista por programa / período para o algoritmo de "
        "otimização da grade de anúncios da TV Globo."
    ),
    version="1.0.0",
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame) -> List[ProgramEntry]:
    """Converte linhas do DataFrame em uma lista de ProgramEntry."""
    records = []
    for row in df.itertuples(index=False):
        records.append(
            ProgramEntry(
                signal=row.signal,
                program_code=row.program_code,
                weekday=int(row.weekday),
                exhibition_date=row.date.date() if hasattr(row.date, "date") else row.date,
                available_time=int(row.available_time),
                predicted_audience=(
                    None if pd.isna(row.predicted_audience) else float(row.predicted_audience)
                ),
            )
        )
    return records


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Infra"])
def health_check():
    """Verifica se a API está no ar e os dados foram carregados."""
    df = get_master_df()
    return {"status": "ok", "total_records": len(df)}


@app.get(
    "/program",
    response_model=ProgramResponse,
    tags=["Consultas"],
    summary="Retorna dados de um programa em uma data específica",
)
def get_by_program(
    program_code: str = Query(..., description="Código do programa (ex: HUCK)"),
    exhibition_date: date = Query(..., description="Data de exibição no formato YYYY-MM-DD"),
):
    """
    Retorna a quantidade de segundos disponíveis para anúncios e a
    audiência prevista para **todas as praças (sinais)** de um programa
    em uma data específica.
    """
    df = get_master_df()

    filtered = df[
        (df["program_code"] == program_code.upper())
        & (df["date"].dt.date == exhibition_date)
    ]

    if filtered.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum registro encontrado para programa='{program_code}' na data={exhibition_date}.",
        )

    return ProgramResponse(
        program_code=program_code.upper(),
        exhibition_date=exhibition_date,
        records=_df_to_records(filtered),
    )


@app.get(
    "/period",
    response_model=PeriodResponse,
    tags=["Consultas"],
    summary="Retorna dados de todos os programas em um período",
)
def get_by_period(
    start_date: date = Query(..., description="Data de início do período (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Data de fim do período (YYYY-MM-DD)"),
):
    """
    Retorna a quantidade de segundos disponíveis para anúncios e a
    audiência prevista para todos os programas exibidos no período
    informado.
    """
    if end_date < start_date:
        raise HTTPException(
            status_code=422,
            detail="end_date não pode ser anterior a start_date.",
        )

    df = get_master_df()

    filtered = df[
        (df["date"].dt.date >= start_date)
        & (df["date"].dt.date <= end_date)
    ]

    if filtered.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum registro encontrado entre {start_date} e {end_date}.",
        )

    return PeriodResponse(
        start_date=start_date,
        end_date=end_date,
        records=_df_to_records(filtered),
    )


# ── Entry point para rodar com `python -m app.main` ───────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
