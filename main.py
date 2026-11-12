"""Command-line entry point.

    python main.py "Find an hour for Priya and Sam on Tuesday afternoon"

Uses a real model if LLM_BASE_URL and LLM_MODEL are set, otherwise a
scripted demo model.
"""

import os
import sys

from scheduler.agent import SchedulingAgent
from scheduler.demo_model import DemoModel
from scheduler.store import Store


def main() -> None:
    request = " ".join(sys.argv[1:]) or "Find an hour for Priya and Sam on Tuesday afternoon"
    store = Store.load()
    if os.environ.get("LLM_BASE_URL") and os.environ.get("LLM_MODEL"):
        from scheduler.real_model import OpenAICompatibleModel
        model = OpenAICompatibleModel()
    else:
        model = DemoModel(store.people)
    agent = SchedulingAgent(model, store)
    print(agent.run(request))


if __name__ == "__main__":
    main()
