from apscheduler.schedulers.background import BackgroundScheduler
from scanner import run_scanner

scheduler = BackgroundScheduler()


def morning_scan():
    print("Running morning scan...")
    data = run_scanner()
    print(data)


scheduler.add_job(
    morning_scan,
    "cron",
    hour=9,
    minute=15
)

scheduler.start()