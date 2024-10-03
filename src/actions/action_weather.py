import requests
from src.actions.action_decorator import Action, ActionRegistry
from src.utils.web_utils import WebHelper
from src.utils.logger import logger

action = "weather"
description = "Forecast weather report for a given location or city or forecast weather request"


def weather_forecast(city):
    # Secret info
    api_url = "https://open-weather13.p.rapidapi.com/"
    headers = headers = {
        "x-rapidapi-host": "open-weather13.p.rapidapi.com",
        "x-rapidapi-key": "02cc6ec43bmsh87d1bf82f74b591p1b74cejsn580422db90a3"
    }
    url = api_url + "/city/" + city + "/EN"

    # Get weather forecast
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return _format_response(response.json())
    else:
        raise Exception(f"{response.status_code} {response.text}")


def _format_response(json):
    try:
        name = json["name"]
        country = json["sys"]["country"]
        description = json["weather"][0]["description"]

        t = json["main"]["temp"]
        temp = round(5 * (t - 32) / 9, 1)
        temMin = json["main"]["temp_min"]
        tempMin = round(5 * (temMin - 32) / 9, 1)
        temMax = json["main"]["temp_max"]
        tempMax = round(5 * (temMax - 32) / 9, 1)

        return (
            f"Current weather of {name} ({country}) is {description}.\n"
            f"Temperature {temp}°C ({tempMin}°C - {tempMax}°C)"
        )
    except KeyError as e:
        raise e
    except Exception as e:
        raise e


@ActionRegistry.register(action,  description)
class WeatherAction(Action):
    def execute(
        self, room_id: str, account_id: str, message: str, web_helper: WebHelper
    ) -> str:
        try:
            # Generate a summary using AI
            location = web_helper.query_ai(
                prompt=(
                    "Only return full city name in text in lower case and space in english:"
                    f"\n\n'{message}'\n\nIf not found city name return 'null'"),
                system_message=(
                    "You are a helpful assistant that return city name in text."
                    "Do not provide additional information or explanation beyond the request."
                ),
                # 'San Fernando del Valle de Catamarca' is a longest city name has 43 character
                max_tokens=43,
            )

            if location == 'null':
                location = 'ho chi minh'

            # Get message
            weather_message = weather_forecast(location)

            return weather_message
        except Exception as e:
            error_message = f"An error occurred while trying to get weather forecast: {str(e)}"
            logger.error(error_message, exc_info=True)
            return "Cannot check the weather forecast for your input."
