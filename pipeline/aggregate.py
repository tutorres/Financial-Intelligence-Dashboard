import pandas as pd

from pipeline.utils import get_connection, get_logger, setup_schemas

logger = get_logger(__name__)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").copy()
    close = df["close"]
    df["daily_return"] = close.pct_change()
    df["ma_7"] = close.rolling(7).mean()
    df["ma_21"] = close.rolling(21).mean()
    df["ma_50"] = close.rolling(50).mean()
    df["rsi_14"] = _rsi(close)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["volatility_21"] = df["daily_return"].rolling(21).std()
    return df[[
        "ticker", "date", "open", "high", "low", "close", "volume",
        "daily_return", "ma_7", "ma_21", "ma_50", "rsi_14",
        "macd", "macd_signal", "macd_hist", "volatility_21",
    ]]


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
        CREATE TABLE IF NOT EXISTS gold.prices (
            ticker        VARCHAR NOT NULL,
            date          DATE NOT NULL,
            open          DOUBLE,
            high          DOUBLE,
            low           DOUBLE,
            close         DOUBLE,
            volume        BIGINT,
            daily_return  DOUBLE,
            ma_7          DOUBLE,
            ma_21         DOUBLE,
            ma_50         DOUBLE,
            rsi_14        DOUBLE,
            macd          DOUBLE,
            macd_signal   DOUBLE,
            macd_hist     DOUBLE,
            volatility_21 DOUBLE,
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
    results = []
    for ticker in silver["ticker"].unique():
        results.append(_compute_indicators(silver[silver["ticker"] == ticker]))
    gold_df = pd.concat(results, ignore_index=True)
    summary_df = _build_summary(gold_df)
    conn.execute("DELETE FROM gold.prices")
    conn.execute("""
        INSERT INTO gold.prices
        SELECT ticker, date, open, high, low, close, volume,
               daily_return, ma_7, ma_21, ma_50, rsi_14,
               macd, macd_signal, macd_hist, volatility_21
        FROM gold_df
    """)
    conn.execute("DELETE FROM gold.summary")
    conn.execute("""
        INSERT INTO gold.summary
        SELECT ticker, last_updated, last_close, pct_change_1d, pct_change_7d,
               pct_change_30d, avg_volume_30d, current_rsi
        FROM summary_df
    """)
    logger.info(
        "Aggregated %d price rows and %d summary rows into gold",
        len(gold_df),
        len(summary_df),
    )
    if own_conn:
        conn.close()


if __name__ == "__main__":
    aggregate()
