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


def _create_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS silver.prices (
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


def transform(conn=None) -> None:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    setup_schemas(conn)
    _create_table(conn)
    bronze = conn.execute(
        "SELECT * FROM bronze.prices ORDER BY ticker, date"
    ).df()
    if bronze.empty:
        logger.warning("bronze.prices is empty — nothing to transform")
        if own_conn:
            conn.close()
        return
    results = []
    for ticker in bronze["ticker"].unique():
        results.append(_compute_indicators(bronze[bronze["ticker"] == ticker]))
    result = pd.concat(results, ignore_index=True)
    conn.execute("DELETE FROM silver.prices")
    conn.execute("""
        INSERT INTO silver.prices
        SELECT ticker, date, open, high, low, close, volume,
               daily_return, ma_7, ma_21, ma_50, rsi_14,
               macd, macd_signal, macd_hist, volatility_21
        FROM result
    """)
    logger.info("Transformed %d rows into silver.prices", len(result))
    if own_conn:
        conn.close()


if __name__ == "__main__":
    transform()
