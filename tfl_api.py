"""
tfl_api.py — Live data from the Transport for London Unified API.


  - rag.py answers document questions from the ./data folder (static knowledge)
  - tfl_api.py fetches real-time line status from the TFL API (live data)

The TFL API is free. 
The module works without a key too (subject to lower rate limits).
"""

import os
import requests
from dataclasses import dataclass

# Optional key 
TFL_APP_KEY = os.getenv("TFL_APP_KEY", "")

BASE_URL = "https://api.tfl.gov.uk"


@dataclass
class LineStatus:
    name: str            # e.g. "Victoria"
    status: str          # e.g. "Good Service" / "Minor Delays"
    reason: str          # description if there's a disruption, else ""


def get_tube_status():
    """
    Fetch current status for all London Underground lines.
    Returns a list of LineStatus objects, or raises on network error.
    """
    # url = f"{BASE_URL}/Line/Mode/tube/Status"
    url = f"{BASE_URL}/Line/Mode/tube,overground,dlr,elizabeth-line/Status"
    params = {}
    if TFL_APP_KEY:
        params["app_key"] = TFL_APP_KEY

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    statuses = []
    for line in data:
        name = line.get("name", "Unknown")
        # each line has a lineStatuses list; take the first status description
        line_statuses = line.get("lineStatuses", [])
        if line_statuses:
            desc = line_statuses[0].get("statusSeverityDescription", "Unknown")
            reason = line_statuses[0].get("reason", "") or ""
        else:
            desc, reason = "Unknown", ""
        statuses.append(LineStatus(name=name, status=desc, reason=reason))

    # sort so any disruptions appear first, then alphabetical
    statuses.sort(key=lambda s: (s.status == "Good Service", s.name))
    return statuses

@dataclass
class Arrival:
    line: str            # e.g. "Victoria"
    destination: str     # where the train is heading
    minutes: int         # minutes until arrival
    platform: str        # platform name if available


def get_arrivals(station_id: str, max_results: int = 8):
    """
    Fetch live arrival predictions for a station.
    Returns a list of Arrival objects, soonest first.
    """
    url = f"{BASE_URL}/StopPoint/{station_id}/Arrivals"
    params = {}
    if TFL_APP_KEY:
        params["app_key"] = TFL_APP_KEY

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    arrivals = []
    for item in data:
        line = item.get("lineName", "Unknown")
        destination = item.get("destinationName", "Unknown")
        seconds = item.get("timeToStation", 0)
        minutes = max(0, round(seconds / 60))
        platform = item.get("platformName", "")
        arrivals.append(Arrival(line=line, destination=destination,
                                minutes=minutes, platform=platform))

    # soonest first, then limit
    arrivals.sort(key=lambda a: a.minutes)
    return arrivals[:max_results]