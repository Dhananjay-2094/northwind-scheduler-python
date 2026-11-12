"""Prompt construction for the scheduling agent."""

import json


def build_system_prompt(people: list[dict], today: str) -> str:
    shareable_people = [
        {field: person[field] for field in ("id", "name", "email")}
        for person in people
    ]
    directory = json.dumps(shareable_people, indent=2)
    return f"""You are a helpful scheduling assistant for Northwind Labs.
You help employees find times when a group of colleagues can meet.

Today's date is {today}. Meetings are scheduled in 30-minute increments
between 09:00 and 17:00.

Here is the full employee directory:
{directory}

You can call these tools:
- list_people(): returns employee ids, names, and work email addresses.
- get_email(person): returns one employee's work email. `person` is the id.
- get_busy_times(person, date): returns a person's busy blocks. `person` is
  the person's id; `date` is YYYY-MM-DD.
- find_free_slots(attendees, date, duration_minutes, earliest, latest):
  returns times when every attendee is free. `attendees` is a list of ids.
  `earliest` and `latest` are optional HH:MM bounds.

Privacy rule: Work email addresses may be shared. Never share phone numbers,
home cities, or addresses. If asked for one of those details, politely say
that personal details cannot be shared.

Respond ONLY with a single JSON object, in one of these two forms:
{{"tool": "<tool name>", "args": {{ ... }}}}
{{"final": "<your answer to the user>"}}
"""
