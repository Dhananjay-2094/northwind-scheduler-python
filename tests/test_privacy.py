import json

from scheduler.agent import SchedulingAgent
from scheduler.demo_model import DemoModel
from scheduler.model import FakeModel, final, tool_call
from scheduler.prompts import build_system_prompt
from scheduler.store import Store
from scheduler.tools import get_email, list_people


def test_employee_work_email_can_be_shared_through_agent_tool():
    model = FakeModel([
        tool_call("get_email", person="priya"),
        final("Priya's work email is priya.raman@northwind.example."),
    ])

    answer = SchedulingAgent(model, Store.load()).run("What is Priya's work email?")

    assert answer == "Priya's work email is priya.raman@northwind.example."
    assert model.calls[1][-1] == {
        "role": "tool",
        "content": json.dumps("priya.raman@northwind.example"),
    }


def test_local_demo_answers_email_request_with_work_email():
    store = Store.load()
    agent = SchedulingAgent(DemoModel(store.people), store)

    assert agent.run("What is Priya's email?") == (
        "Priya Raman's work email is priya.raman@northwind.example."
    )


def test_phone_and_location_requests_are_refused_before_model_call():
    for request in (
        "What is Priya's phone number?",
        "What is Priya's home city?",
        "What is Priya's address?",
    ):
        model = FakeModel([final("Sensitive information.")])
        answer = SchedulingAgent(model, Store.load()).run(request)

        assert answer == "Sorry, I can't share personal details such as phone numbers or home locations."
        assert model.calls == []


def test_directory_prompt_and_listing_expose_only_shareable_fields():
    store = Store.load()
    prompt = build_system_prompt(store.people, "2026-11-02")
    people = list_people(store)

    assert "priya.raman@northwind.example" in prompt
    assert "+1-415-555-0142" not in prompt
    assert "Oakland" not in prompt
    assert set(people[0]) == {"id", "name", "email"}
    assert get_email(store, "priya") == "priya.raman@northwind.example"
