import pandas as pd

from pipeline.utils import get_connection, get_logger, setup_schemas

logger = get_logger(__name__)


def _normalize(series: pd.Series) -> pd.Series:
    series = series.astype(float)
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.0, index=series.index)
    return (series - mn) / (mx - mn)


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["ticker", "date", "rsi_14", "daily_return"]].copy()
    for col, norm_col in [
        ("close", "close_norm"),
        ("volume", "volume_norm"),
        ("ma_7", "ma_7_norm"),
        ("ma_21", "ma_21_norm"),
    ]:
        out[norm_col] = df.groupby("ticker")[col].transform(_normalize)
    return out[[
        "ticker", "date", "close_norm", "volume_norm",
        "ma_7_norm", "ma_21_norm", "rsi_14", "daily_return",
    ]].dropna()


def _create_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS features.model_input (
            ticker       VARCHAR NOT NULL,
            date         DATE NOT NULL,
            close_norm   DOUBLE,
            volume_norm  DOUBLE,
            ma_7_norm    DOUBLE,
            ma_21_norm   DOUBLE,
            rsi_14       DOUBLE,
            daily_return DOUBLE,
            PRIMARY KEY (ticker, date)
        )
    """)


def ml_features(conn=None) -> None:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    setup_schemas(conn)
    _create_table(conn)
    gold = conn.execute("SELECT * FROM gold.prices ORDER BY ticker, date").df()
    if gold.empty:
        logger.warning("gold.prices is empty — nothing to compute")
        if own_conn:
            conn.close()
        return
    features_df = _build_features(gold)
    conn.execute("DELETE FROM features.model_input")
    conn.execute("""
        INSERT INTO features.model_input
        SELECT ticker, date, close_norm, volume_norm,
               ma_7_norm, ma_21_norm, rsi_14, daily_return
        FROM features_df
    """)
    logger.info("Computed %d ML feature rows into features.model_input", len(features_df))
    if own_conn:
        conn.close()


if __name__ == "__main__":
    ml_features()
