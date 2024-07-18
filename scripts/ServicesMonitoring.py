import os
import time
import logging
import subprocess
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
import socket
import json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'message': record.getMessage(),
            'name': record.name,
            'filename': record.pathname,
            'lineno': record.lineno
        }
        return json.dumps(log_record)

# Configure logger for Nacos monitoring
nacos_logger = logging.getLogger('nacos-monitor')
nacos_logger.setLevel(logging.DEBUG)
nacos_handler = TimedRotatingFileHandler('nacos-monitor.log', when='midnight', interval=1)
nacos_handler.suffix = "%Y%m%d"
nacos_handler.setLevel(logging.DEBUG)
formatter = JsonFormatter()
nacos_handler.setFormatter(formatter)
nacos_logger.addHandler(nacos_handler)

# Configure logger for Apollo monitoring
apollo_logger = logging.getLogger('apollo-monitor')
apollo_logger.setLevel(logging.DEBUG)
apollo_handler = TimedRotatingFileHandler('apollo-monitor.log', when='midnight', interval=1)
apollo_handler.suffix = "%Y%m%d"
apollo_handler.setLevel(logging.DEBUG)
apollo_handler.setFormatter(formatter)
apollo_logger.addHandler(apollo_handler)

# Nacos server paths
nacos_log_path = 'D:\\nacos\\logs\\nacos.log'
nacos_server_path = 'D:\\nacos\\bin'

# Services to monitor
services_to_monitor = [
    'wmiApSrv', 'ApolloEquipment', 'ApolloEquipment2', 'ApolloGateway',
    'ApolloGatewayHttps', 'ApolloMonitor', 'ApolloSystem', 'ApolloTcp'
]

def check_nacos_logs():
    """Checks Nacos logs for specific events within the last 60 seconds."""
    try:
        nacos_logger.info("Checking Nacos logs...")
        current_time = datetime.now()
        found_events = []

        with open(nacos_log_path, 'r') as file:
            lines = file.readlines()
            for line in lines:
                if line.strip():  # Ensure the line is not empty
                    try:
                        timestamp_str = line[:23]  # Extract the timestamp portion
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                        if current_time - timestamp <= timedelta(seconds=180):
                            if 'ERROR Startup errors' in line:
                                found_events.append(('ERROR Startup errors', timestamp))
                            elif 'ERROR Nacos failed to start' in line:
                                found_events.append(('ERROR Nacos failed to start', timestamp))
                    except ValueError:
                        continue  # Skip lines that don't start with a date-time format

        nacos_logger.info(f"Found events in Nacos logs: {found_events}")
        return found_events
    except (IOError, FileNotFoundError) as e:
        nacos_logger.error(f"Failed to check Nacos logs: {e}")
        return []

def restart_nacos_server():
    """Restarts the Nacos server."""
    try:
        nacos_logger.info("Restarting Nacos server...")
        os.chdir(nacos_server_path)
        nacos_logger.info("Executing shutdown command...")
        shutdown_result = subprocess.run('cmd /c shutdown.cmd', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        nacos_logger.info(f"Shutdown command executed with output: {shutdown_result.stdout} and errors: {shutdown_result.stderr}")
        
        if shutdown_result.returncode != 0:
            nacos_logger.error("Shutdown command failed.")
            return

        nacos_logger.info("Waiting for 10 seconds before starting the server...")
        time.sleep(10)

        start_nacos_server()
    except Exception as e:
        nacos_logger.error(f"Failed to restart Nacos server: {e}")

def start_nacos_server():
    """Starts the Nacos server."""
    try:
        nacos_logger.info("Starting Nacos server...")
        os.chdir(nacos_server_path)
        subprocess.Popen('cmd /c "start cmd /c startup.cmd -m standalone"', shell=True)
        nacos_logger.info("Startup command executed.")
    except Exception as e:
        nacos_logger.error(f"Failed to start Nacos server: {e}")

def check_port_status(host, port):
    """Checks if a service is running on the specified port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex((host, port))
            if result == 0:
                return True
            else:
                return False
    except Exception as e:
        nacos_logger.error(f"Failed to check port {port}: {e}")
        return False

def monitor_services():
    """Monitors the status of services."""
    try:
        nacos_logger.info("Monitoring services...")
        
        # Check if Nacos server is running on port 8848
        nacos_running = check_port_status('localhost', 8848)
        if nacos_running:
            nacos_logger.info("Nacos is running.")
        else:
            nacos_logger.warning("Nacos is not running. Restarting...")
            restart_nacos_server()

        # Check status of all services
        for service in services_to_monitor:
            service_status = check_service_status(service)
            if not service_status:
                nacos_logger.warning(f"{service} is not running. Starting...")
                start_service(service)

    except Exception as e:
        nacos_logger.error(f"Error monitoring services: {e}")

def check_service_status(service_name):
    """Checks the status of a Windows service using subprocess."""
    try:
        result = subprocess.run(['sc', 'query', service_name], capture_output=True, text=True)
        if "RUNNING" in result.stdout:
            return True
        else:
            return False
    except Exception as e:
        nacos_logger.error(f"Error checking status of {service_name}: {e}")
        return False

def start_service(service_name):
    """Starts a Windows service using subprocess."""
    try:
        subprocess.run(['net', 'start', service_name], check=True)
        nacos_logger.info(f"Started {service_name} successfully.")
    except subprocess.CalledProcessError as e:
        nacos_logger.error(f"Failed to start {service_name}: {e}")

if __name__ == "__main__":
    try:
        while True:
            events = check_nacos_logs()
            if len(events) >= 2:
                for i in range(len(events) - 1):
                    event1, time1 = events[i]
                    event2, time2 = events[i + 1]
                    if event1 == 'Out dated connection' and event2 == 'Connection check task end':
                        time_gap = time2 - time1
                        nacos_logger.info(f"Time gap between events: {time_gap}")
                        if time_gap <= timedelta(minutes=5):
                            nacos_logger.info("Condition met: Restarting server.")
                            restart_nacos_server()
                            break

            # Monitor services every 2 minutes
            monitor_services()
            time.sleep(120)  # 2 minutes

    except KeyboardInterrupt:
        nacos_logger.info("Monitoring stopped by user.")
    except Exception as e:
        nacos_logger.error(f"Unexpected error in monitoring: {e}")
