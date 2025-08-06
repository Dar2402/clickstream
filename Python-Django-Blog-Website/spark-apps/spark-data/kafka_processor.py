import os
import logging
import traceback
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

# ------------------------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------------------------

LOG_FILE = "snowplow_kafka_processor.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE)
    ]
)

logger = logging.getLogger("SnowplowKafkaProcessor")


# ------------------------------------------------------------------------------
# Spark Session Creation
# ------------------------------------------------------------------------------

def create_spark_session() -> SparkSession:
    """
    Create and configure a SparkSession for Kafka streaming.

    Returns:
        SparkSession: Configured Spark session.
    """
    try:
        spark = SparkSession.builder \
            .appName("SnowplowKafkaProcessor") \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
            .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
            .getOrCreate()

        logger.info("✅ SparkSession created successfully.")
        return spark

    except Exception as e:
        logger.error(f"❌ Failed to create SparkSession: {e}")
        logger.debug(traceback.format_exc())
        raise


# ------------------------------------------------------------------------------
# Snowplow Event Processing
# ------------------------------------------------------------------------------

def process_snowplow_events(spark: SparkSession):
    """
    Reads and processes Snowplow structured events from a Kafka topic.

    Args:
        spark (SparkSession): Spark session object.

    Returns:
        DataFrame: Parsed and enriched Snowplow structured event stream.
    """
    try:
        # Define schema for Snowplow structured events
        snowplow_schema = StructType([
            StructField("e", StringType(), True),
            StructField("se_ca", StringType(), True),
            StructField("se_ac", StringType(), True),
            StructField("se_la", StringType(), True),
            StructField("se_pr", StringType(), True),
            StructField("eid", StringType(), True),
            StructField("dtm", StringType(), True),
            StructField("url", StringType(), True),
            StructField("duid", StringType(), True),
            StructField("sid", StringType(), True),
        ])

        # Kafka read stream
        kafka_df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")) \
            .option("subscribe", os.getenv("KAFKA_TOPIC", "enriched")) \
            .option("startingOffsets", "latest") \
            .load()

        logger.info("📥 Kafka stream initialized from topic: enriched")

        # JSON parsing
        parsed_df = kafka_df.select(
            col("timestamp").alias("kafka_timestamp"),
            from_json(col("value").cast("string"), snowplow_schema).alias("data")
        ).select(
            col("kafka_timestamp"),
            col("data.*")
        ).withColumn("processed_at", current_timestamp()) \
            .withColumn("hour", hour(col("processed_at"))) \
            .withColumn("date", to_date(col("processed_at"))) \
            .filter(col("e") == "se")  # Filter structured events only

        logger.info("✅ Kafka stream parsed and filtered for structured events.")

        return parsed_df

    except Exception as e:
        logger.error(f"❌ Failed to process Snowplow events: {e}")
        logger.debug(traceback.format_exc())
        raise


# ------------------------------------------------------------------------------
# Console Writer
# ------------------------------------------------------------------------------

def write_to_console(df):
    """
    Writes processed DataFrame to the console for monitoring.

    Args:
        df (DataFrame): Processed DataFrame stream.

    Returns:
        StreamingQuery: Active Spark streaming query.
    """
    try:
        query = df.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .trigger(processingTime="30 seconds") \
            .start()

        logger.info("🖥️ Console writer started.")
        return query

    except Exception as e:
        logger.error(f"❌ Failed to start console writer: {e}")
        logger.debug(traceback.format_exc())
        raise


# ------------------------------------------------------------------------------
# Aggregated Metrics Writer
# ------------------------------------------------------------------------------

def write_aggregated_metrics(df):
    """
    Computes and writes event metrics (e.g., count, unique users/sessions) to console.

    Args:
        df (DataFrame): Processed Snowplow DataFrame stream.

    Returns:
        StreamingQuery: Active Spark streaming query.
    """
    try:
        aggregated = df.groupBy("se_ca", "se_ac", "hour", "date").agg(
            count("*").alias("event_count"),
            countDistinct("duid").alias("unique_users"),
            countDistinct("sid").alias("unique_sessions")
        )

        query = aggregated.writeStream \
            .outputMode("update") \
            .format("console") \
            .option("truncate", False) \
            .trigger(processingTime="60 seconds") \
            .start()

        logger.info("📊 Aggregated metrics writer started.")
        return query

    except Exception as e:
        logger.error(f"❌ Failed to start metrics writer: {e}")
        logger.debug(traceback.format_exc())
        raise


# ------------------------------------------------------------------------------
# Main Entrypoint
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("🚀 Starting Snowplow Kafka Processor...")

    try:
        spark = create_spark_session()
        spark.sparkContext.setLogLevel("WARN")

        processed_events = process_snowplow_events(spark)

        console_query = write_to_console(processed_events)
        metrics_query = write_aggregated_metrics(processed_events)

        logger.info("✅ Streaming jobs started. Check Spark UI at http://localhost:18081")

        console_query.awaitTermination()

    except Exception as e:
        logger.critical(f"❌ Fatal error occurred: {e}")
        logger.debug(traceback.format_exc())
    finally:
        logger.info("🛑 Shutting down Spark session...")
        spark.stop()
