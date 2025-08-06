import requests
import json
import time
import logging
import socket
from datetime import datetime
from logging.handlers import RotatingFileHandler

LOG_FILE = "spark_cluster_monitor.log"
SPARK_MASTER_DEFAULT_PORT = 8080


def setup_logger():
    """Configure logging for both console and file output."""
    logger = logging.getLogger("SparkClusterMonitor")
    logger.setLevel(logging.DEBUG)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_format)

    # File Handler
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=3)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()


def resolve_spark_master_url():
    """
    Resolves the Spark Master URL based on the environment (Docker or local).
    Uses hostname resolution or defaults to localhost.
    """
    try:
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)

        if host_ip.startswith("127.") or "localhost" in hostname:
            return f"http://localhost:{SPARK_MASTER_DEFAULT_PORT}"
        else:
            return f"http://spark-master:{SPARK_MASTER_DEFAULT_PORT}"
    except Exception as e:
        logger.warning(f"Failed to resolve Spark master host: {e}. Falling back to localhost.")
        return f"http://localhost:{SPARK_MASTER_DEFAULT_PORT}"


def get_cluster_status(url):
    """
    Queries the Spark Master REST API and retrieves the cluster status.

    Args:
        url (str): Spark Master URL

    Returns:
        dict or None: Cluster status JSON or None if request fails
    """
    try:
        response = requests.get(f"{url}/json", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error connecting to Spark Master at {url}: {e}")
        return None


def print_cluster_info(status):
    """
    Logs the cluster information in a human-readable format.

    Args:
        status (dict): Spark cluster status JSON
    """
    if not status:
        logger.warning("❌ Unable to retrieve Spark cluster status")
        return

    logger.info(f"\n🔥 Spark Cluster Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    logger.info(f"📊 Master URL: {status.get('url', 'N/A')}")
    logger.info(f"🟢 Status: {status['status']}")
    logger.info(f"⚡ Cores: {status['cores']} total, {status['coresused']} used, {status['coresfree']} free")
    logger.info(f"💾 Memory: {status['memory']} total, {status['memoryused']} used")

    logger.info(f"\n👥 Workers ({len(status['workers'])}):")
    for i, worker in enumerate(status['workers'], 1):
        logger.info(f"  Worker {i}: {worker['host']}:{worker['port']}")
        logger.info(f"    Cores: {worker['cores']} total, {worker['coresused']} used")
        logger.info(f"    Memory: {worker['memory']} total, {worker['memoryused']} used")
        logger.info(f"    State: {worker['state']}")

    logger.info(f"\n🔄 Running Applications ({len(status['activeapps'])}):")
    if status['activeapps']:
        for app in status['activeapps']:
            logger.info(f"  📱 {app['name']} (ID: {app['id']})")
            logger.info(f"    Cores: {app['cores']}, Memory: {app['memory']}")
    else:
        logger.info("  No active applications")


def monitor_resources():
    """
    Continuously monitors Spark cluster resources and logs status every 30 seconds.
    """
    master_url = resolve_spark_master_url()
    logger.info(f"Resolved Spark Master URL: {master_url}")

    while True:
        try:
            status = get_cluster_status(master_url)
            print_cluster_info(status)
        except Exception as e:
            logger.exception(f"Unexpected error during monitoring: {e}")
        time.sleep(30)


if __name__ == "__main__":
    logger.info("🔍 Starting Spark Cluster Monitor...")
    try:
        monitor_resources()
    except KeyboardInterrupt:
        logger.info("👋 Monitoring stopped by user.")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
