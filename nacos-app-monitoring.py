import os
import time
import logging
import subprocess
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = TimedRotatingFileHandler('nacos_monitor.log', when="midnight", interval=1)
handler.suffix = "%Y%m%d"
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)


logger.addHandler(handler)

log_path = 'D:\\nacos\\logs\\nacos.log'
server_path = 'D:\\nacos\\bin'

def check_logs():
    """Checks Nacos logs for specific events.

    Returns:
        list: A list of tuples containing event type and datetime.
    """
    try:
        logger.info("Checking Nacos logs...")
        with open(log_path, 'r') as file:
            lines = file.readlines()
            found_events = []
            for line in lines:
                if 'ERROR Application run failed' in line:
                    timestamp = datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S')
                    found_events.append(('ERROR Application run failed', timestamp))
                elif 'ERROR Nacos failed to start' in line:
                    timestamp = datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S')
                    found_events.append(('ERROR Nacos failed to start', timestamp))
        logger.info(f"Found events: {found_events}")
        return found_events
    except (IOError, FileNotFoundError) as e:
        logger.error(f"Failed to check logs: {e}")
        return []

def restart_server():
    """Restarts the Nacos server."""
    try:
        logger.info("Restarting Nacos server...")
        os.chdir(server_path)
        logger.info("Executing shutdown command...")
        shutdown_result = subprocess.run('cmd /c shutdown.cmd', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Shutdown command executed with output: {shutdown_result.stdout} and errors: {shutdown_result.stderr}")
        
        if shutdown_result.returncode != 0:
            logger.error("Shutdown command failed.")
            return

        logger.info("Waiting for 10 seconds before starting the server...")
        time.sleep(10)

        start_server()
    except Exception as e:
        logger.error(f"Failed to restart server: {e}")

def start_server():
    """Starts the Nacos server."""
    try:
        logger.info("Starting Nacos server...")
        os.chdir(server_path)
        logger.info("Executing startup command in a new cmd window...")
        subprocess.Popen('cmd /c "start cmd /c startup.cmd -m standalone"', shell=True)
        logger.info("Startup command executed.")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")

while True:
    events = check_logs()
    if len(events) >= 2:
        for i in range(len(events) - 1):
            event1, time1 = events[i]
            event2, time2 = events[i + 1]
            if event1 == 'Out dated connection' and event2 == 'Connection check task end':
                time_gap = time2 - time1
                logger.info(f"Time gap between events: {time_gap}")
                if time_gap <= timedelta(minutes=5):
                    logger.info("Condition met: Restarting server.")
                    restart_server()
                    break
    time.sleep(300)
