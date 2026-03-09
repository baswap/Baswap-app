import logging
import logging.handlers
import requests
import json
import pytz
from datetime import datetime
import sys
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger_file_handler = logging.handlers.RotatingFileHandler(
    "status.log",
    maxBytes=1024 * 1024,
    backupCount=1,
    encoding="utf8",
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger_file_handler.setFormatter(formatter)
logger.addHandler(logger_file_handler)

if __name__ == "__main__":

    # approximately 150 measurements a day
    url = os.environ["THINGSPEAK_URL"] + "?results=1"

    response = requests.get(url)
    data = json.loads(response.text)

    # Timezone
    utc_tz = pytz.timezone("UTC")

    for feed in data["feeds"]:
        timestamp = feed.get("created_at", "")

        if timestamp:
            utc_time = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=utc_tz
            )

            # Current time in UTC
            current_time_utc = datetime.now(utc_tz)

            # Check if the timestamp is within the last hour
            time_difference = current_time_utc - utc_time

            if time_difference.total_seconds() >= 3600:
                logger.error(
                    "Latest data is older than 1 hour. " f"Last timestamp: {utc_time}"
                )
                sys.exit(1)

    logger.info("Check passed: latest data is within 1 hour.")
