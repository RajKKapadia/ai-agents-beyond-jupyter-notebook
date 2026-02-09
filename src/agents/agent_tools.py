from typing_extensions import TypedDict
from typing import Literal

from agents import function_tool
import httpx

from src.config import OPENWEATHERMAP_API_KEY


class Location(TypedDict):
    location: str
    unit: Literal["metric", "imperial", "standard"]


@function_tool(
    needs_approval=True
)
async def fetch_weather(location: Location) -> str:
    """Fetch the weather for a given location using OpenWeatherMap API.

    Args:
        location: Dictionary containing:
            - location: City name (e.g., "London", "New York", "Tokyo")
            - unit: Temperature unit - "metric" (Celsius), "imperial" (Fahrenheit), or "standard" (Kelvin)

    Returns:
        A formatted string with weather information including temperature,
        conditions, humidity, and wind speed.
    """
    city = location.get("location", "")
    unit = location.get("unit", "metric")

    if not city:
        return "Error: No location provided"

    # OpenWeatherMap API endpoint
    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {"q": city, "appid": OPENWEATHERMAP_API_KEY, "units": unit}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        # Extract weather information
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        description = data["weather"][0]["description"]
        wind_speed = data["wind"]["speed"]
        city_name = data["name"]
        country = data["sys"]["country"]

        # Determine temperature unit symbol
        temp_unit = {"metric": "°C", "imperial": "°F", "standard": "K"}.get(unit, "°C")

        # Determine wind speed unit
        wind_unit = (
            "m/s" if unit == "metric" else "mph" if unit == "imperial" else "m/s"
        )

        # Format the response
        weather_info = f"""Weather in {city_name}, {country}:
🌡️ Temperature: {temp}{temp_unit} (feels like {feels_like}{temp_unit})
☁️ Conditions: {description.capitalize()}
💧 Humidity: {humidity}%
💨 Wind Speed: {wind_speed} {wind_unit}"""

        return weather_info

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: City '{city}' not found. Please check the spelling or try a different city."
        elif e.response.status_code == 401:
            return "Error: Invalid API key. Please check your OpenWeatherMap API key."
        else:
            return (
                f"Error: Failed to fetch weather data (Status {e.response.status_code})"
            )
    except httpx.TimeoutException:
        return "Error: Request timed out. Please try again."
    except httpx.RequestError as e:
        return f"Error: Network error occurred - {str(e)}"
    except KeyError as e:
        return (
            f"Error: Unexpected response format from weather API - missing key {str(e)}"
        )
    except Exception as e:
        return f"Error: An unexpected error occurred - {str(e)}"
