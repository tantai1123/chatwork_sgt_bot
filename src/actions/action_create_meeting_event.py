import json
import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from src.actions.action_decorator import Action, ActionRegistry
from src.config import Config
from src.utils.logger import logger
from src.utils.web_utils import WebHelper

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

HANGOUT_LINKS_FILE = 'hangout_links.json'

@ActionRegistry.register("create_meeting_event", "Create an event in google calendar.")
class CreateMeetingEventAction(Action):
    def execute(self, room_id: str, account_id: str, message: str, web_helper: WebHelper) -> str:
        try:
            event_data = self._get_data_from_message(message, web_helper)
            return self._create_calendar_event(event_data)
        except Exception as e:
            error_message = f"An error occurred while trying to create event: {str(e)}"
            logger.error(error_message, exc_info=True)
            return "Cannot create google calendar event."

    def _get_data_from_message(self, message, web_helper):
        current_time = datetime.now(ZoneInfo("Asia/Bangkok"))

        prompt = f"""
        Please extract the following event information from the user input message. Use the current date and time: {current_time.isoformat()} (GMT+7, Asia/Ho_Chi_Minh timezone) as the reference point.'

        Event Summary: The title or brief description of the meeting, e.g., 'Team Meeting,' 'Project Discussion,' etc. Use 'Meeting' if no specific summary is mentioned.
        Event Description: Additional details about the meeting if specified, or leave empty if not provided.
        Start DateTime: The start date and time of the meeting, in ISO format (YYYY-MM-DDTHH:MM:SS). Interpret any relative time references (e.g., 'next 30 min,' 'tomorrow at 10:00 AM') accurately based on the current time provided.
        End DateTime: Set the end time as 1 hour after the start time unless the user provides a specific end time.
        Conference: Conference data, if user request to create a conference(e.g., 'google meet', 'video call', 'Google MTG', etc.) set 1(type int), or set 0(type int) if user not request.

        Return the information in the following JSON structure, using the timezone 'Asia/Ho_Chi_Minh':

        {{
          "summary": "<summary>",
          "description": "<description>",
          "start": {{
            "dateTime": "<start_date_time>",
            "timeZone": "Asia/Ho_Chi_Minh"
          }},
          "end": {{
            "dateTime": "<end_date_time>",
            "timeZone": "Asia/Ho_Chi_Minh"
          }},
          "isHasConference": <is_has_conference>
        }}

        User input: {message}
        """

        system_message = (
            "You are a helpful assistant that extracts Google Calendar event information from text. "
            "Provide only the requested JSON output without any additional explanation."
        )

        event_data = web_helper.query_ai(
            prompt=prompt,
            system_message=system_message,
            max_tokens=500,
        )
        return json.loads(event_data)

    def get_path(self, file_name):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, file_name)

    def load_links(self):
        file_path = self.get_path(HANGOUT_LINKS_FILE)
        with open(file_path, 'r') as file:
            return json.load(file)

    def save_links(self, hangout_links):
        file_path = self.get_path(HANGOUT_LINKS_FILE)
        with open(file_path, 'w') as file:
            json.dump(hangout_links, file)

    def _create_calendar_event(self, event_data):
        service = self._get_calendar_service()
        event_result = service.events().insert(calendarId=self.get_config_value("MEETING_CALENDAR_ID"), body=event_data).execute()

        if event_data.get("isHasConference") == 1:
            event_ids = []
            hangout_links = self.load_links()

            current_time = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat()
            event_list = service.events().list(calendarId=self.get_config_value("MEETING_CALENDAR_ID"), timeMin=current_time, orderBy='startTime', singleEvents=True).execute()

            events = event_list.get('items', [])

            for event in events:
                event_id = event.get('id')
                if event_id:
                    event_ids.append(event_id)

            available_links = [link for link in hangout_links if link["eventId"] not in event_ids]

            if available_links:
                googleMeetUrl = random.choice(available_links)

                for link in hangout_links:
                    if link["url"] == googleMeetUrl["url"]:
                        link["eventId"] = event_result.get('id')
                        break

                googleMeetUrl = f'''
                - Google Meet joining info:
                Google meet video conferencing: {googleMeetUrl["url"]}
                '''
                self.save_links(hangout_links)
            else:
                googleMeetUrl = 'There are no more conferences, please create one manually.'
        else:
            googleMeetUrl = ''

        # Parse the start and end times
        start_datetime = datetime.fromisoformat(event_data["start"]["dateTime"])
        end_datetime = datetime.fromisoformat(event_data["end"]["dateTime"])

        # Format the date and times
        formatted_date = start_datetime.strftime("%A, %B %d")
        formatted_start_time = start_datetime.strftime("%H:%M")
        formatted_end_time = end_datetime.strftime("%H:%M")

        datetime_formatted_result = f"{formatted_date} · {formatted_start_time} – {formatted_end_time}"

        return self._format_response(event_result, datetime_formatted_result, googleMeetUrl)

    def _get_calendar_service(self):
        try:
            private_key = self.get_config_value("PRIVATE_KEY").replace('\\n', '\n')
            credentials = Credentials.from_service_account_info({
                "type": "service_account",
                "project_id": self.get_config_value("PROJECT_ID"),
                "private_key_id": self.get_config_value("PRIVATE_KEY_ID"),
                "private_key": private_key,
                "client_email": self.get_config_value("CLIENT_EMAIL"),
                "client_id": self.get_config_value("CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": self.get_config_value("CLIENT_X509_CERT_URL"),
                "universe_domain": "googleapis.com",
            }, scopes=SCOPES)
            return build('calendar', 'v3', credentials=credentials)
        except ValueError as e:
            logger.error(f"Error creating credentials: {str(e)}")
            raise

    @staticmethod
    def _format_response(event_result: Dict[str, Any], datetime_formatted: str, google_meet_url: str) -> str:
        base_message = (
            "[success]\n"
            "Meeting was created successfully.\n"
            "[info]\n"
            f"- Summary: {event_result.get('summary')}\n"
            f"- Time: {datetime_formatted}\n"
            f"- Time zone: {TIMEZONE}"
        )
        
        if google_meet_url:
            base_message += f"\n{google_meet_url}"
            
        return f"{base_message}\n[/info]"
