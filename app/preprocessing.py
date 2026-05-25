"""
preprocessing.py
----------------
Lê os dois CSVs, faz o join e calcula a audiência prevista (mediana das
últimas 4 exibições por programa + sinal + dia da semana).

Resultado: DataFrame com colunas
    signal | program_code | weekday | available_time | predicted_audience
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load_audience(path: Path = DATA_DIR / "tvaberta_program_audience.csv") -> pd.DataFrame:
    """Carrega e normaliza o arquivo de audiência histórica."""
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    # Parsear data e extrair dia da semana (0=Monday … 6=Sunday)
    df["exhibition_date"] = pd.to_datetime(df["exhibition_date"]).dt.normalize()
    df["weekday"] = df["exhibition_date"].dt.dayofweek

    return df[["signal", "program_code", "exhibition_date", "weekday", "average_audience"]]


def load_inventory(path: Path = DATA_DIR / "tvaberta_inventory_availability.csv") -> pd.DataFrame:
    """Carrega e normaliza o arquivo de disponibilidade de inventário."""
    df = pd.read_csv(path, sep=";")
    df.columns = df.columns.str.strip()

    df["date"] = pd.to_datetime(df["date"], dayfirst=True)
    df["weekday"] = df["date"].dt.dayofweek

    return df[["signal", "program_code", "date", "weekday", "available_time"]]


def compute_predicted_audience(audience_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula a mediana das últimas 4 exibições de cada
    (signal, program_code, weekday).

    Retorna DataFrame com colunas:
        signal | program_code | weekday | predicted_audience
    """
    # Ordenar por data para garantir que "últimas 4" seja correto
    df = audience_df.sort_values("exhibition_date")

    def last4_median(series: pd.Series) -> float:
        return series.iloc[-4:].median()

    predicted = (
        df.groupby(["signal", "program_code", "weekday"])["average_audience"]
        .agg(last4_median)
        .reset_index()
        .rename(columns={"average_audience": "predicted_audience"})
    )
    return predicted


def build_master_dataframe(
    audience_path: Path = DATA_DIR / "tvaberta_program_audience.csv",
    inventory_path: Path = DATA_DIR / "tvaberta_inventory_availability.csv",
) -> pd.DataFrame:
    """
    Pipeline completo de pré-processamento.

    Retorna o dataframe mestre com:
        signal | program_code | weekday | available_time | predicted_audience
    """
    audience_df = load_audience(audience_path)
    inventory_df = load_inventory(inventory_path)

    predicted_df = compute_predicted_audience(audience_df)

    # Join inventory + predicted audience via (signal, program_code, weekday)
    master = inventory_df.merge(
        predicted_df,
        on=["signal", "program_code", "weekday"],
        how="left",
    )

    return master[["signal", "program_code", "weekday", "date", "available_time", "predicted_audience"]]


# Singleton carregado na inicialização da API
_master_df: pd.DataFrame | None = None


def get_master_df() -> pd.DataFrame:
    """Retorna (e cria se necessário) o dataframe mestre em memória."""
    global _master_df
    if _master_df is None:
        _master_df = build_master_dataframe()
    return _master_df
