"""
schemas.py
----------
Modelos de request/response com Pydantic para a REST API.
"""

from __future__ import annotations
import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Response Models ────────────────────────────────────────────────────────────

class ProgramEntry(BaseModel):
    """Um único registro do dataframe mestre."""
    signal: str = Field(..., description="Sinal / localização")
    program_code: str = Field(..., description="Código do programa")
    weekday: int = Field(..., description="Dia da semana (0=Segunda … 6=Domingo)")
    exhibition_date: datetime.date = Field(..., description="Data de exibição")
    available_time: int = Field(..., description="Segundos disponíveis para anúncios")
    predicted_audience: Optional[float] = Field(
        None, description="Mediana das últimas 4 audiências (mesmo sinal/programa/weekday)"
    )


class ProgramResponse(BaseModel):
    """Resposta do endpoint /program."""
    program_code: str
    exhibition_date: datetime.date
    records: List[ProgramEntry]


class PeriodResponse(BaseModel):
    """Resposta do endpoint /period."""
    start_date: datetime.date
    end_date: datetime.date
    records: List[ProgramEntry]
