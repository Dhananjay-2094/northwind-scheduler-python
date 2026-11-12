# Project Notes

## Problems found and changes made

- **Unknown attendees could appear free.** Calendar lookup treated a missing person as an empty calendar. `find_free_slots` now checks every attendee ID against the directory and the agent returns a clear message for unknown IDs.
- **The default CLI repeated a hard-coded answer.** `main.py` used a scripted demo response regardless of the request. The local demo now recognizes common attendee, date, duration, and daypart phrases and summarizes the slots returned by the scheduling tool.
- **Model/tool failures could crash or loop.** The agent assumed valid JSON and tool arguments and had no turn limit. It now validates responses, gives the model a correction opportunity, returns a safe failure when recovery fails, and stops after five model turns. FakeModel tests cover malformed JSON, missing fields, unknown tools, invalid arguments, recovery, and repeated tool calls.
- **Morning and evening requests were mishandled.** A CLI reproduction for Tuesday morning returned afternoon slots because only “afternoon” was interpreted. Morning now means 09:00–12:00, afternoon means 12:00–17:00, and evening gets an explanation that it is outside work hours.
- **The final fitting slot was omitted.** Reviewing the search boundary showed that a window ending exactly at the limit, such as 16:30–17:00, was excluded. The slot search now includes that boundary. The existing afternoon test was updated because this newly found slot is valid.
- **Private directory fields were exposed to the model.** The system prompt and `list_people` included phone numbers and home cities. Both now expose only IDs, names, and work emails. Requests for phone, address, or home-location details receive a fixed refusal before reaching the model; a `get_email` tool provides work email lookup.

## Part B addition

- Built privacy-aware contact lookup: employees can ask for a colleague’s work email, while phone numbers and home locations are withheld. This helps employees find approved contact information without exposing personal details.
- Chose this over multi-day lookup because the sample calendar only covers 2–4 November 2026, and missing dates are currently treated as free. Trustworthy multi-day search would require changing calendar coverage and missing-data semantics. A better response summary was another option, but contact lookup adds a distinct user capability and a clear privacy rule.
- Morning/afternoon bounds and evening handling were bug fixes to existing scheduling behavior, separate from the contact lookup feature.

## AI tools

- I used Codex to inspect the repository, explain its data flow, implement the changes, and write/run tests. I delegated no work to other agents.
- I did not pursue the AI-suggested multi-day search. After inspecting the calendar data, it was clear that absent dates look free, so a multi-day feature would need broader changes to calendar coverage and missing-data handling. I chose the smaller, safer email lookup instead.

## What I would do next

- Make meeting duration explicit or apply a documented rounding rule. The demo defaults an omitted duration to 30 minutes, and `duration_minutes // 30` currently rounds a 45-minute request down to one slot.
- Round arbitrary `earliest` bounds up and `latest` bounds down to slot boundaries; current daypart bounds are aligned, but arbitrary times can still be rounded down by `time_to_slot`.
- Add calendar coverage/status so missing dates are not assumed free, then implement multi-day search.
- Add a network timeout to the live model adapter. The agent turn cap bounds the number of calls, but cannot stop an individual HTTP call that hangs.
