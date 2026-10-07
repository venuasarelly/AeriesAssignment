import os


MAX_CONCURRENCY = int(
    os.getenv("MAX_CONCURRENCY", "3")
)

SCHEDULER_INTERVAL = float(
    os.getenv("SCHEDULER_INTERVAL", "0.5")
)