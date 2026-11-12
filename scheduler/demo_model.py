"""Small request-aware model for running the CLI without an API."""

import json
import re
from datetime import date, timedelta

from .model import final, tool_call


class DemoModel:
    """Interpret common demo requests and summarize actual tool results.

    This intentionally supports a small set of plain-English patterns; use
    ``OpenAICompatibleModel`` for general language understanding.
    """

    def __init__(self, people: list[dict], today: str = "2026-11-02"):
        self.people = people
        self.today = date.fromisoformat(today)
        self.request: str | None = None
        self.request_details: dict | None = None

    def complete(self, messages: list[dict]) -> str:
        if self.request is None:
            self.request = next(m["content"] for m in messages if m["role"] == "user")
            details = self._parse_request(self.request)
            if isinstance(details, str):
                return final(details)
            self.request_details = details
            if details["intent"] == "email":
                return tool_call("get_email", person=details["attendee_ids"][0])
            return tool_call(
                "find_free_slots",
                attendees=details["attendee_ids"],
                date=details["date"],
                duration_minutes=details["duration_minutes"],
                earliest=details["earliest"],
                latest=details["latest"],
            )

        result_message = next(
            (m["content"] for m in reversed(messages) if m["role"] == "tool"),
            "[]",
        )
        slots = json.loads(result_message)
        details = self.request_details
        assert details is not None
        if details["intent"] == "email":
            return final(f"{details['attendee_names'][0]}'s work email is {slots}.")
        names = " and ".join(details["attendee_names"])
        parsed_date = date.fromisoformat(details["date"])
        meeting_date = f"{parsed_date.strftime('%a %b')} {parsed_date.day}"
        if not slots:
            return final(f"I couldn't find an available time for {names} on {meeting_date}.")

        options = ", ".join(f"{slot['start']}–{slot['end']}" for slot in slots)
        return final(f"{names} are free on {meeting_date} at {options}.")

    def _parse_request(self, request: str) -> dict | str:
        lowered = request.lower()
        if "evening" in lowered:
            return "The scheduling day ends at 17:00, so evening is outside the available work hours (09:00–17:00)."

        matched = [
            person for person in self.people
            if re.search(rf"\b{re.escape(person['id'].lower())}\b", lowered)
            or person["name"].lower() in lowered
        ]
        if not matched:
            return "Please name one or more employees from the directory so I can check their calendars."

        if "email" in lowered or "e-mail" in lowered or "contact details" in lowered or "contact info" in lowered:
            if len(matched) != 1:
                return "Please ask for one employee's work email at a time."
            return {
                "intent": "email",
                "attendee_ids": [matched[0]["id"]],
                "attendee_names": [matched[0]["name"]],
            }

        meeting_date = self.today
        iso_date = re.search(r"\b\d{4}-\d{2}-\d{2}\b", request)
        if iso_date:
            meeting_date = date.fromisoformat(iso_date.group())
        else:
            weekdays = {
                "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6,
            }
            weekday = next((day for day in weekdays if day in lowered), None)
            if weekday:
                delta = (weekdays[weekday] - self.today.weekday()) % 7
                if delta == 0 or "next " + weekday in lowered:
                    delta += 7
                meeting_date = self.today + timedelta(days=delta)
            elif "tomorrow" in lowered:
                meeting_date = self.today + timedelta(days=1)

        duration = 30
        number = re.search(r"\b(\d+)\s*(minutes?|mins?)\b", lowered)
        hours = re.search(r"\b(\d+)\s*hours?\b", lowered)
        if number:
            duration = int(number.group(1))
        elif hours:
            duration = int(hours.group(1)) * 60
        elif "half an hour" in lowered or "half-hour" in lowered:
            duration = 30
        elif "an hour" in lowered or "one hour" in lowered:
            duration = 60

        if "morning" in lowered:
            earliest, latest = "09:00", "12:00"
        elif "afternoon" in lowered:
            earliest, latest = "12:00", "17:00"
        else:
            earliest, latest = None, None
        return {
            "intent": "availability",
            "attendee_ids": [person["id"] for person in matched],
            "attendee_names": [person["name"] for person in matched],
            "date": meeting_date.isoformat(),
            "duration_minutes": duration,
            "earliest": earliest,
            "latest": latest,
        }
