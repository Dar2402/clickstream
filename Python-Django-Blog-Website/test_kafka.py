from kafka import KafkaConsumer
import logging
from datetime import datetime

# Configuration
KAFKA_SERVER = 'localhost:9092'  # Change to 'kafka:9092' if running in Docker
TOPIC_NAME = 'good'  # Replace with your topic name
LOG_FILE = 'kafka_messages.log'  # Log file path

# Set up logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def consume_messages():
    try:
        # Create Kafka consumer
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=[KAFKA_SERVER],
            auto_offset_reset='latest',  # Start from latest messages
            group_id='kafka-logger-group',
            value_deserializer=lambda x: x.decode('utf-8')
        )

        logging.info(f"Starting Kafka consumer for topic: {TOPIC_NAME}")
        print(f"Listening to topic '{TOPIC_NAME}'. Logging to {LOG_FILE}...")

        # Continuously poll for new messages
        for message in consumer:
            log_message = f"Topic: {message.topic}, Partition: {message.partition}, " \
                          f"Offset: {message.offset}, Key: {message.key}, " \
                          f"Value: {message.value}"

            logging.info(log_message)
            print(log_message)  # Also print to console for monitoring

    except Exception as e:
        logging.error(f"Error in consumer: {str(e)}")
        print(f"Error: {str(e)}")
    finally:
        if 'consumer' in locals():
            consumer.close()
        logging.info("Consumer stopped")


if __name__ == "__main__":
    consume_messages()