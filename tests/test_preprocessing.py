"""
tests/test_preprocessing.py
----------------------------
Testes unitários para o script de pré-processamento.
"""

import pandas as pd
import pytest
from io import StringIO
from pathlib import Path

# ─── Fixtures ─────────────────────────────────────────────────────────────────

AUDIENCE_CSV = """\
signal,program_code,exhibition_date,program_start_time,average_audience
SP1,PROG_A,2020-06-01,2020-06-01T10:00:00.000Z,1000
SP1,PROG_A,2020-06-08,2020-06-08T10:00:00.000Z,2000
SP1,PROG_A,2020-06-15,2020-06-15T10:00:00.000Z,3000
SP1,PROG_A,2020-06-22,2020-06-22T10:00:00.000Z,4000
SP1,PROG_A,2020-06-29,2020-06-29T10:00:00.000Z,5000
BH,PROG_A,2020-06-01,2020-06-01T10:00:00.000Z,500
BH,PROG_A,2020-06-08,2020-06-08T10:00:00.000Z,600
"""

INVENTORY_CSV = """\
signal;program_code;date;available_time
SP1;PROG_A;01/06/2020;300
SP1;PROG_A;08/06/2020;400
BH;PROG_A;01/06/2020;200
"""


@pytest.fixture
def audience_df():
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.preprocessing import load_audience
    # monkey-patch para usar StringIO
    df = pd.read_csv(StringIO(AUDIENCE_CSV))
    df["exhibition_date"] = pd.to_datetime(df["exhibition_date"]).dt.normalize()
    df["weekday"] = df["exhibition_date"].dt.dayofweek
    return df[["signal", "program_code", "exhibition_date", "weekday", "average_audience"]]


@pytest.fixture
def inventory_df():
    df = pd.read_csv(StringIO(INVENTORY_CSV), sep=";")
    df["date"] = pd.to_datetime(df["date"], dayfirst=True)
    df["weekday"] = df["date"].dt.dayofweek
    return df[["signal", "program_code", "date", "weekday", "available_time"]]


# ─── Testes de pré-processamento ──────────────────────────────────────────────

class TestComputePredictedAudience:
    def test_uses_last_4_exhibitions(self, audience_df):
        """Deve usar apenas as 4 últimas exibições para a mediana."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.preprocessing import compute_predicted_audience

        result = compute_predicted_audience(audience_df)
        sp1_row = result[
            (result["signal"] == "SP1") & (result["program_code"] == "PROG_A")
        ]
        assert len(sp1_row) == 1
        # Últimas 4 exibições de SP1/PROG_A/Monday: 2000, 3000, 4000, 5000
        expected_median = pd.Series([2000.0, 3000.0, 4000.0, 5000.0]).median()
        assert sp1_row["predicted_audience"].values[0] == pytest.approx(expected_median)

    def test_handles_fewer_than_4_exhibitions(self, audience_df):
        """Com menos de 4 exibições, calcula a mediana do que há."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.preprocessing import compute_predicted_audience

        result = compute_predicted_audience(audience_df)
        bh_row = result[
            (result["signal"] == "BH") & (result["program_code"] == "PROG_A")
        ]
        assert len(bh_row) == 1
        expected_median = pd.Series([500.0, 600.0]).median()
        assert bh_row["predicted_audience"].values[0] == pytest.approx(expected_median)

    def test_groups_by_signal_program_weekday(self, audience_df):
        """Resultado deve ter uma linha por (signal, program_code, weekday)."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.preprocessing import compute_predicted_audience

        result = compute_predicted_audience(audience_df)
        assert list(result.columns) == ["signal", "program_code", "weekday", "predicted_audience"]
        assert result.duplicated(["signal", "program_code", "weekday"]).sum() == 0


class TestBuildMasterDataframe:
    def test_output_columns(self, tmp_path, audience_df, inventory_df):
        """O dataframe mestre deve conter as colunas esperadas."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.preprocessing import compute_predicted_audience

        predicted = compute_predicted_audience(audience_df)
        master = inventory_df.merge(
            predicted, on=["signal", "program_code", "weekday"], how="left"
        )
        expected_cols = {"signal", "program_code", "weekday", "available_time", "predicted_audience"}
        assert expected_cols.issubset(set(master.columns))

    def test_join_preserves_inventory_rows(self, audience_df, inventory_df):
        """Todos os registros de inventário devem estar no dataframe mestre."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.preprocessing import compute_predicted_audience

        predicted = compute_predicted_audience(audience_df)
        master = inventory_df.merge(
            predicted, on=["signal", "program_code", "weekday"], how="left"
        )
        assert len(master) == len(inventory_df)
