"""The scheduling agent: a simple tool-calling loop."""

import json
import re

from .model import Model
from .prompts import build_system_prompt
from .store import Store
from .tools import TOOLS, UnknownAttendeesError


class SchedulingAgent:
    def __init__(
        self,
        model: Model,
        store: Store,
        today: str = "2026-11-02",
        max_turns: int = 5,
    ):
        self.model = model
        self.store = store
        self.today = today
        self.max_turns = max_turns

    def run(self, user_request: str) -> str:
        """Handle one user request and return the assistant's final answer."""
        if re.search(
            r"\b(phone|telephone|mobile|cell(?:phone)?|address|home\s+city|city|location)\b|\bwhere\s+(?:does|do)\s+\w+\s+live\b",
            user_request,
            re.IGNORECASE,
        ):
            return "Sorry, I can't share personal details such as phone numbers or home locations."

        messages = [
            {"role": "system", "content": build_system_prompt(self.store.people, self.today)},
            {"role": "user", "content": user_request},
        ]

        unresolved_error = False
        for _ in range(self.max_turns):
            raw = self.model.complete(messages)
            messages.append({"role": "assistant", "content": raw})

            try:
                action = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                self._ask_for_correction(messages, "Your response was not valid JSON.")
                unresolved_error = True
                continue

            error = self._validate_action(action)
            if error:
                self._ask_for_correction(messages, error)
                unresolved_error = True
                continue

            if "final" in action:
                if unresolved_error:
                    return "I couldn't safely complete that request because the model returned an invalid response. Please try again."
                return action["final"]

            tool = TOOLS.get(action["tool"])
            if tool is None:
                self._ask_for_correction(messages, f"Unknown tool: {action['tool']}.")
                unresolved_error = True
                continue

            try:
                result = tool(self.store, **action["args"])
            except UnknownAttendeesError as error:
                return str(error)
            except (TypeError, ValueError, KeyError, AttributeError) as error:
                self._ask_for_correction(messages, f"The tool arguments were invalid: {error}.")
                unresolved_error = True
                continue

            messages.append({"role": "tool", "content": json.dumps(result)})
            unresolved_error = False

        return f"I couldn't complete that request within {self.max_turns} model turns. Please try again."

    @staticmethod
    def _validate_action(action: object) -> str | None:
        if not isinstance(action, dict):
            return "Your response must be a JSON object."
        if "final" in action:
            if set(action) != {"final"} or not isinstance(action["final"], str):
                return 'A final response must have the form {"final": "..."}.'
            return None
        if set(action) != {"tool", "args"}:
            return 'A tool request must have the form {"tool": "...", "args": {...}}.'
        if not isinstance(action["tool"], str) or not isinstance(action["args"], dict):
            return "The tool name must be text and args must be an object."
        return None

    @staticmethod
    def _ask_for_correction(messages: list[dict], error: str) -> None:
        messages.append({
            "role": "user",
            "content": f"{error} Correct the response using the required JSON format. Do not claim a time is available unless a scheduling tool confirmed it.",
        })
