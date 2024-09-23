import os
import requests
import time
import json
from dotenv import load_dotenv

load_dotenv()

# Environment variables for authentication
LOKI_ENDPOINT = os.getenv("GRAFANA_PUSH_URL")
LOKI_USERNAME = os.getenv("GRAFANA_USERNAME")
LOKI_PASSWORD = os.getenv("GRAFANA_PASSWORD")

if not LOKI_ENDPOINT or not LOKI_USERNAME or not LOKI_PASSWORD:
    raise ValueError(
        "LOKI_ENDPOINT, LOKI_USERNAME, or LOKI_PASSWORD are undefined! Please double check."
    )

def push_logs_to_loki(stream: dict, messages: list):
    """
    Push logs to Grafana Loki.

    Args:
        stream (dict): Labels for the log stream.
        messages (list): List of log messages to send.
    """

    # Create a list of log entries with timestamps in nanoseconds
    values = [[str(int(time.time() * 1e9)), message] for message in messages]

    # Create the log payload
    logs = {
        "streams": [
            {
                "stream": stream,
                "values": values
            }
        ]
    }

    try:
        print(f"LOG: {json.dumps(logs, indent=2)}")
        
        # Send the log data to Loki
        response = requests.post(
            LOKI_ENDPOINT,
            json=logs,
            auth=(LOKI_USERNAME, LOKI_PASSWORD),
            headers={
                "Content-Type": "application/json"
            }
        )

        # Check if the request was successful
        response.raise_for_status()
        print(f"Successfully pushed logs to Loki: {response.status_code}")
    
    except requests.exceptions.HTTPError as http_err:
        # Handle HTTP errors
        print(f"Loki responded with status code {response.status_code}")
        print("Response data:", response.json())
    except requests.exceptions.RequestException as req_err:
        # Handle any other errors
        print("Request error:", req_err)
    except Exception as err:
        # Handle any other unexpected errors
        print("An unexpected error occurred:", err)