from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StringType, TimestampType
import time
from datetime import datetime

# ---------------------
# CONFIGURATIONS
# ---------------------
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC = "clickstream_events"
HDFS_OUTPUT_PATH = "hdfs://namenode:9000/user/hdfs/kafka-stream-output"
CHECKPOINT_LOCATION = "/tmp/spark_checkpoint/kafka_to_hdfs/"

WRITE_INTERVAL_SECS = 10  # Only write to HDFS every 10s

# ---------------------
# STATEFUL TIMER FOR WRITES
# ---------------------
# Note: Spark workers are stateless across batches.
# So this state will only work if you run in local[*] or driver-managed cluster.
last_written_timestamp = time.time()

def write_to_hdfs_conditionally(batch_df, batch_id):
    global last_written_timestamp
    current_time = time.time()
    time_diff = current_time - last_written_timestamp

    if time_diff >= WRITE_INTERVAL_SECS:
        print(f"[{datetime.now()}] Writing batch {batch_id} to HDFS...")

        batch_df.write \
            .mode("append") \
            .format("parquet") \
            .partitionBy("event_type") \
            .save(HDFS_OUTPUT_PATH)

        last_written_timestamp = current_time
    else:
        print(f"[{datetime.now()}] Skipping write for batch {batch_id}, only {time_diff:.2f}s passed")

# ---------------------
# SCHEMA FOR JSON PARSING
# ---------------------
event_schema = StructType() \
    .add("event_type", StringType()) \
    .add("user_id", StringType()) \
    .add("page_url", StringType()) \
    .add("timestamp", TimestampType())

# ---------------------
# SPARK SESSION
# ---------------------
spark = SparkSession.builder \
    .appName("KafkaToHDFSStream") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# ---------------------
# READ FROM KAFKA
# ---------------------
raw_kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "latest") \
    .load()

# ---------------------
# PARSE JSON PAYLOAD
# ---------------------
parsed_df = raw_kafka_df \
    .selectExpr("CAST(value AS STRING) as json_str") \
    .select(from_json(col("json_str"), event_schema).alias("data")) \
    .select("data.*")

# ---------------------
# FOREACHBATCH WRITING LOGIC
# ---------------------
query = parsed_df.writeStream \
    .foreachBatch(write_to_hdfs_conditionally) \
    .outputMode("append") \
    .option("checkpointLocation", CHECKPOINT_LOCATION) \
    .trigger(processingTime="1 second") \
    .start()

query.awaitTermination()
