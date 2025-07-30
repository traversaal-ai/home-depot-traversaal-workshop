#!/usr/bin/env python3
"""
Simple Weather MCP Server for ADK Workshop

This MCP server provides weather information using OpenWeatherMap API.
For educational purposes, it includes a fallback mode with simulated data.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional
import httpx

# MCP server imports
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server instance
app = Server("weather-server")

# OpenWeatherMap API configuration
# For production, use environment variable: os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "demo")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

# Demo mode flag - uses simulated data if API key is not set
DEMO_MODE = OPENWEATHER_API_KEY == "demo"

# Simulated weather data for demo mode
DEMO_WEATHER_DATA = {
    "chicago": {
        "temperature": 72,  # Fahrenheit
        "conditions": "Partly Cloudy",
        "precipitation": 0.0,
        "wind_speed": 8,
        "humidity": 65
    },
    "new york": {
        "temperature": 68,
        "conditions": "Clear",
        "precipitation": 0.0,
        "wind_speed": 5,
        "humidity": 55
    },
    "seattle": {
        "temperature": 60,
        "conditions": "Light Rain",
        "precipitation": 0.25,
        "wind_speed": 12,
        "humidity": 80
    },
    "miami": {
        "temperature": 85,
        "conditions": "Thunderstorm",
        "precipitation": 1.5,
        "wind_speed": 20,
        "humidity": 90
    }
}

async def fetch_real_weather(city: str, date: Optional[str] = None) -> Dict[str, Any]:
    """Fetch real weather data from OpenWeatherMap API"""
    async with httpx.AsyncClient() as client:
        try:
            # For current weather
            url = f"{OPENWEATHER_BASE_URL}/weather"
            params = {
                "q": city,
                "appid": OPENWEATHER_API_KEY,
                "units": "imperial"  # Use Fahrenheit
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract relevant information
            return {
                "temperature": data["main"]["temp"],
                "conditions": data["weather"][0]["description"].title(),
                "precipitation": data.get("rain", {}).get("1h", 0.0),  # mm in last hour
                "wind_speed": data["wind"]["speed"],
                "humidity": data["main"]["humidity"]
            }
            
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            # Fall back to demo data
            return DEMO_WEATHER_DATA.get(city.lower(), {
                "temperature": 70,
                "conditions": "Unknown",
                "precipitation": 0.0,
                "wind_speed": 5,
                "humidity": 50
            })

def get_demo_weather(city: str, date: Optional[str] = None) -> Dict[str, Any]:
    """Get simulated weather data for demo mode"""
    # Get base weather for city
    weather = DEMO_WEATHER_DATA.get(city.lower(), {
        "temperature": 70,
        "conditions": "Clear",
        "precipitation": 0.0,
        "wind_speed": 5,
        "humidity": 50
    })
    
    # If a future date is requested, simulate some variation
    if date:
        try:
            # Simple simulation: add some variation based on day difference
            target_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            days_ahead = (target_date - datetime.now()).days
            
            if days_ahead > 0:
                # Add some variation
                weather = weather.copy()
                weather["temperature"] += (days_ahead % 10) - 5  # +/- 5 degrees
                if days_ahead % 3 == 0:
                    weather["conditions"] = "Partly Cloudy"
                    weather["precipitation"] = 0.1
        except:
            pass
    
    return weather

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available weather tools"""
    return [
        types.Tool(
            name="get_weather",
            description="Get current or forecasted weather for a city",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (e.g., 'Chicago', 'New York')"
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional: Date in ISO format (e.g., '2025-06-21'). If not provided, returns current weather."
                    }
                },
                "required": ["city"]
            }
        ),
        types.Tool(
            name="assess_weather_risk",
            description="Assess delivery risk based on weather conditions",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name for weather assessment"
                    },
                    "date": {
                        "type": "string",
                        "description": "Delivery date in ISO format"
                    }
                },
                "required": ["city", "date"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[types.TextContent]:
    """Handle tool calls"""
    
    if name == "get_weather":
        city = arguments.get("city", "")
        date = arguments.get("date")
        
        if DEMO_MODE:
            logger.info(f"Demo mode: Getting simulated weather for {city}")
            weather_data = get_demo_weather(city, date)
        else:
            logger.info(f"Fetching real weather for {city}")
            weather_data = await fetch_real_weather(city, date)
        
        response = {
            "city": city,
            "date": date or "current",
            "weather": weather_data,
            "mode": "demo" if DEMO_MODE else "live"
        }
        
        return [types.TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
    
    elif name == "assess_weather_risk":
        city = arguments.get("city", "")
        date = arguments.get("date", "")
        
        # Get weather data
        if DEMO_MODE:
            weather_data = get_demo_weather(city, date)
        else:
            weather_data = await fetch_real_weather(city, date)
        
        # Assess risk based on weather conditions
        risk_score = 1  # Base score
        risk_factors = []
        
        # Precipitation risk
        precip = weather_data.get("precipitation", 0)
        if precip > 1.0:
            risk_score = 8
            risk_factors.append(f"Heavy precipitation ({precip} inches)")
        elif precip > 0.5:
            risk_score = 5
            risk_factors.append(f"Moderate precipitation ({precip} inches)")
        elif precip > 0.1:
            risk_score = 3
            risk_factors.append(f"Light precipitation ({precip} inches)")
        
        # Wind risk
        wind = weather_data.get("wind_speed", 0)
        if wind > 25:
            risk_score = max(risk_score, 8)
            risk_factors.append(f"High winds ({wind} mph)")
        elif wind > 15:
            risk_score = max(risk_score, 5)
            risk_factors.append(f"Moderate winds ({wind} mph)")
        
        # Condition-based risk
        conditions = weather_data.get("conditions", "").lower()
        if any(severe in conditions for severe in ["thunderstorm", "tornado", "hurricane", "blizzard"]):
            risk_score = 9
            risk_factors.append(f"Severe weather: {weather_data['conditions']}")
        elif any(bad in conditions for bad in ["snow", "ice", "sleet", "hail"]):
            risk_score = max(risk_score, 7)
            risk_factors.append(f"Hazardous conditions: {weather_data['conditions']}")
        
        # Temperature extremes
        temp = weather_data.get("temperature", 70)
        if temp > 95 or temp < 20:
            risk_score = max(risk_score, 6)
            risk_factors.append(f"Extreme temperature ({temp}°F)")
        
        if not risk_factors:
            risk_factors.append("Favorable weather conditions")
            risk_score = 1
        
        response = {
            "city": city,
            "date": date,
            "weather_risk_score": risk_score,
            "weather_factors": risk_factors,
            "weather_data": weather_data,
            "risk_level": "HIGH" if risk_score >= 7 else "MEDIUM" if risk_score >= 4 else "LOW",
            "mode": "demo" if DEMO_MODE else "live"
        }
        
        return [types.TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
    
    else:
        return [types.TextContent(
            type="text",
            text=f"Error: Unknown tool '{name}'"
        )]

async def main():
    """Run the MCP server"""
    logger.info("Starting Weather MCP Server...")
    if DEMO_MODE:
        logger.info("Running in DEMO MODE (no API key set)")
        logger.info("To use real weather data, set OPENWEATHER_API_KEY environment variable")
    else:
        logger.info("Running with OpenWeatherMap API")
    
    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="weather-mcp-server",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())