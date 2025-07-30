from workflow.mcp.mcp_server import mcp
from loguru import logger
import requests
from typing import Any, Dict, List

@mcp.tool()
def get_weather_forecast(lat: str, lon: str, date: str) -> str:
    """
    Fetches daily weather forecast for a specific date (YYYY-MM-DD) from Open-Meteo API.
    Only works for up to 16 days ahead (forecast) or historical (with premium support).
    """
    logger.info(f"Fetching weather forecast for {date} at lat={lat}, lon={lon}")
    
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
        f"&start_date={date}&end_date={date}&timezone=auto"
    )
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        daily = data.get("daily", {})
        if not daily or not daily.get("time"):
            return "No forecast available for that date."

        idx = 0  # always first element as we requested one day
        return (
            f"Forecast for {date}:\n"
            f"Max Temp: {daily['temperature_2m_max'][idx]}°C\n"
            f"Min Temp: {daily['temperature_2m_min'][idx]}°C\n"
            f"Precipitation: {daily['precipitation_sum'][idx]} mm\n"
            f"Weather Code: {daily['weathercode'][idx]}"
        )
    else:
        return f"Weather API error: {response.status_code}"
