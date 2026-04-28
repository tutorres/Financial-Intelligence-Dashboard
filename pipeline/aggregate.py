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


def _pct_change(group: pd.DataFrame, n: int) -> float | None:
    if len(group) <= n:
        return None
    current = group.iloc[-1]["close"]
    prev = group.iloc[-(n + 1)]["close"]
    return (current - prev) / prev * 100


def _build_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker, group in df.groupby("ticker"):
        group = group.sort_values("date").reset_index(drop=True)
        last = group.iloc[-1]
        rows.append({
            "ticker": ticker,
            "last_updated": last["date"],
            "last_close": float(last["close"]),
            "pct_change_1d": _pct_change(group, 1),
            "pct_change_7d": _pct_change(group, 7),
            "pct_change_30d": _pct_change(group, 30),
            "avg_volume_30d": float(group.tail(30)["volume"].mean()),
            "current_rsi": float(last["rsi_14"]) if pd.notna(last["rsi_14"]) else None,
        })
    return pd.DataFrame(rows)


def _create_tables(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gold.features (
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gold.summary (
            ticker          VARCHAR PRIMARY KEY,
            last_updated    DATE,
            last_close      DOUBLE,
            pct_change_1d   DOUBLE,
            pct_change_7d   DOUBLE,
            pct_change_30d  DOUBLE,
            avg_volume_30d  DOUBLE,
            current_rsi     DOUBLE
        )
    """)


def aggregate(conn=None) -> None:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    setup_schemas(conn)
    _create_tables(conn)
    silver = conn.execute("SELECT * FROM silver.prices ORDER BY ticker, date").df()
    if silver.empty:
        logger.warning("silver.prices is empty — nothing to aggregate")
        if own_conn:
            conn.close()
        return
    features_df = _build_features(silver)
    summary_df = _build_summary(silver)
    conn.execute("DELETE FROM gold.features")
    conn.execute("""
        INSERT INTO gold.features
        SELECT ticker, date, close_norm, volume_norm, ma_7_norm, ma_21_norm, rsi_14, daily_return
        FROM features_df
    """)
    conn.execute("DELETE FROM gold.summary")
    conn.execute("""
        INSERT INTO gold.summary
        SELECT ticker, last_updated, last_close, pct_change_1d, pct_change_7d,
               pct_change_30d, avg_volume_30d, current_rsi
        FROM summary_df
    """)
    logger.info(
        "Aggregated %d feature rows and %d summary rows into gold",
        len(features_df),
        len(summary_df),
    )
    if own_conn:
        conn.close()


if __name__ == "__main__":
    aggregate()
