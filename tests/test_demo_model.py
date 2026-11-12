from scheduler.agent import SchedulingAgent
from scheduler.demo_model import DemoModel
from scheduler.store import Store


def run_demo(request: str) -> str:
    store = Store.load()
    return SchedulingAgent(DemoModel(store.people), store).run(request)


def test_demo_model_limits_morning_results_to_before_noon():
    answer = run_demo("Find 30 minutes for Priya and Sam on Tuesday morning")

    assert answer == (
        "Priya Raman and Sam Okafor are free on Tue Nov 3 at 11:00–11:30, "
        "11:30–12:00."
    )


def test_demo_model_afternoon_includes_last_slot_ending_at_1700():
    answer = run_demo("Find 30 minutes for Priya and Sam on Tuesday afternoon")

    assert "16:30–17:00" in answer
    assert "11:00–11:30" not in answer


def test_demo_model_explains_evening_is_outside_work_hours():
    answer = run_demo("Find 30 minutes for Priya and Sam on Tuesday evening")

    assert answer == (
        "The scheduling day ends at 17:00, so evening is outside the available "
        "work hours (09:00–17:00)."
    )
