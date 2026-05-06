from pipeline.aggregate import aggregate
from pipeline.ingest import ingest
from pipeline.ml_features import ml_features
from pipeline.transform import transform
from pipeline.utils import get_connection, get_logger

logger = get_logger(__name__)


def run() -> None:
    conn = get_connection()
    try:
        logger.info("Pipeline started")
        ingest(conn=conn)
        transform(conn=conn)
        aggregate(conn=conn)
        ml_features(conn=conn)
        logger.info("Pipeline complete")
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
