from pipeline.utils import get_connection, get_logger, setup_schemas

logger = get_logger(__name__)


def _create_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS silver.prices (
            ticker  VARCHAR NOT NULL,
            date    DATE NOT NULL,
            open    DOUBLE,
            high    DOUBLE,
            low     DOUBLE,
            close   DOUBLE,
            volume  BIGINT,
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
    clean = bronze.dropna(subset=["close"])
    clean = (
        clean.sort_values("ingested_at")
        .drop_duplicates(subset=["ticker", "date"], keep="last")
    )
    conn.execute("DELETE FROM silver.prices")
    conn.execute("""
        INSERT INTO silver.prices
        SELECT ticker, date, open, high, low, close, volume
        FROM clean
    """)
    logger.info("Transformed %d rows into silver.prices", len(clean))
    if own_conn:
        conn.close()


if __name__ == "__main__":
    transform()
