import json

from scheduler.agent import SchedulingAgent
from scheduler.model import FakeModel, final, tool_call
from scheduler.store import Store


def test_agent_returns_final_answer():
    model = FakeModel([final("Happy to help!")])
    agent = SchedulingAgent(model, Store.load())
    assert agent.run("hello") == "Happy to help!"


def test_agent_calls_tool_and_returns_result_to_model():
    model = FakeModel([
        tool_call("find_free_slots", attendees=["priya", "sam"],
                  date="2026-11-03", duration_minutes=60, earliest="12:00"),
        final("13:00 works for both."),
    ])
    agent = SchedulingAgent(model, Store.load())

    answer = agent.run("Find an hour for Priya and Sam on Tuesday afternoon")

    assert answer == "13:00 works for both."
    second_call = model.calls[1]
    assert second_call[-1]["role"] == "tool"
    assert {"start": "13:00", "end": "14:00"} in json.loads(second_call[-1]["content"])


def test_agent_accepts_attendees_in_directory():
    model = FakeModel([
        tool_call("find_free_slots", attendees=["priya", "sam"],
                  date="2026-11-03", duration_minutes=60),
        final("Priya and Sam are free at 13:00."),
    ])

    answer = SchedulingAgent(model, Store.load()).run("Find an hour for Priya and Sam")

    assert answer == "Priya and Sam are free at 13:00."
    assert model.calls[1][-1]["role"] == "tool"


def test_agent_tells_user_when_attendee_is_not_in_directory():
    model = FakeModel([
        tool_call("find_free_slots", attendees=["priya", "not-a-person"],
                  date="2026-11-03", duration_minutes=60),
    ])

    answer = SchedulingAgent(model, Store.load()).run("Find an hour for Priya and not-a-person")

    assert answer == (
        "I couldn't find 'not-a-person' in the employee directory. "
        "Please check the name and try again."
    )
    # The unknown attendee is rejected before the model can turn a missing
    # calendar into a claim that the person is free.
    assert len(model.calls) == 1


def test_agent_recovers_after_malformed_json():
    model = FakeModel([
        "not json",
        final("I couldn't safely complete that request."),
    ])

    answer = SchedulingAgent(model, Store.load()).run("Find a time")

    assert answer.startswith("I couldn't safely complete")
    assert "not valid JSON" in model.calls[1][-1]["content"]


def test_agent_recovers_from_missing_tool_fields():
    model = FakeModel([
        '{"tool": "find_free_slots"}',
        tool_call("find_free_slots", attendees=["priya"], date="2026-11-03",
                  duration_minutes=30),
        final("Priya has an available time."),
    ])

    answer = SchedulingAgent(model, Store.load()).run("Find 30 minutes for Priya")

    assert answer == "Priya has an available time."
    assert "must have the form" in model.calls[1][-1]["content"]
    assert model.calls[2][-1]["role"] == "tool"


def test_agent_does_not_accept_final_after_unknown_tool():
    model = FakeModel([
        tool_call("invented_tool"),
        final("A time is available at 13:00."),
    ])

    answer = SchedulingAgent(model, Store.load()).run("Find a time")

    assert answer.startswith("I couldn't safely complete")
    assert "Unknown tool" in model.calls[1][-1]["content"]


def test_agent_recovers_from_invalid_tool_arguments():
    model = FakeModel([
        tool_call("find_free_slots", attendees=["priya"], date="2026-11-03",
                  duration_minutes=30, earliest=123),  # earliest must be a clock string
        tool_call("find_free_slots", attendees=["priya"], date="2026-11-03",
                  duration_minutes=30),
        final("Priya has an available time."),
    ])

    answer = SchedulingAgent(model, Store.load()).run("Find 30 minutes for Priya")

    assert answer == "Priya has an available time."
    assert "arguments were invalid" in model.calls[1][-1]["content"]


def test_agent_stops_after_maximum_turns_of_repeated_tool_calls():
    repeated_call = tool_call("list_people")
    model = FakeModel([repeated_call], loop_last=True)

    answer = SchedulingAgent(model, Store.load(), max_turns=3).run("List people")

    assert answer == "I couldn't complete that request within 3 model turns. Please try again."
    assert len(model.calls) == 3


def test_system_prompt_includes_directory():
    model = FakeModel([final("ok")])
    SchedulingAgent(model, Store.load()).run("hi")
    system = model.calls[0][0]["content"]
    assert "Priya Raman" in system
