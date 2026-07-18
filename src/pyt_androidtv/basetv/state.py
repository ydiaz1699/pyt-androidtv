"""State detection engine for determining device state from properties."""

from __future__ import annotations

import logging
from typing import Any

from ..exceptions import InvalidStateDetectionRuleError
from ..models import State

_LOGGER = logging.getLogger(__name__)

# Valid states for detection rules
_VALID_STATES: frozenset[str] = frozenset(s.value for s in State if s not in (State.UNAVAILABLE,))

# Valid properties that can be used in rules
_VALID_STATE_PROPERTIES: tuple[str, ...] = ("audio_state", "media_session_state")
_VALID_PROPERTIES: tuple[str, ...] = ("audio_state", "media_session_state", "wake_lock_size")
_VALID_PROPERTY_TYPES: dict[str, type] = {
    "audio_state": str,
    "media_session_state": int,
    "wake_lock_size": int,
}

# Media session state to State mapping
_MEDIA_SESSION_STATE_MAP: dict[int, State] = {
    2: State.PAUSED,
    3: State.PLAYING,
}


class StateDetectionEngine:
    """Engine for determining device state using configurable rules.

    The rules parameter is a dictionary mapping app IDs to lists of rules.
    Each rule can be:
        - A fixed state string (e.g., "idle", "playing")
        - A property name ("media_session_state" or "audio_state")
        - A conditional dict: {"state": {"property": value, ...}}

    Parameters
    ----------
    rules : dict or None
        A dictionary mapping app IDs to rule lists.

    """

    def __init__(self, rules: dict[str, list[Any]] | None = None) -> None:
        self._rules: dict[str, list[Any]] = {}
        if rules:
            self.validate_rules(rules)
            self._rules = dict(rules)

    @property
    def rules(self) -> dict[str, list[Any]]:
        """Return a copy of the current rules."""
        return dict(self._rules)

    def detect_state(
        self,
        *,
        current_app: str | None,
        media_session_state: int | None = None,
        wake_lock_size: int | None = None,
        audio_state: str | None = None,
    ) -> State | None:
        """Determine the device state using the configured rules.

        Parameters
        ----------
        current_app : str or None
            The currently running application.
        media_session_state : int or None
            The media session playback state.
        wake_lock_size : int or None
            The current wake lock size.
        audio_state : str or None
            The audio state string ("idle", "paused", "playing").

        Returns
        -------
        State or None
            The detected state, or None if no rule matched.

        """
        if not self._rules or current_app is None or current_app not in self._rules:
            return None

        rules = self._rules[current_app]

        for rule in rules:
            # Fixed state rule: always return this state for the app
            if isinstance(rule, str) and rule in _VALID_STATES:
                return State(rule)

            # Property-based rule: use a device property to determine state
            if rule == "media_session_state":
                if media_session_state in _MEDIA_SESSION_STATE_MAP:
                    return _MEDIA_SESSION_STATE_MAP[media_session_state]
                if media_session_state is not None:
                    return State.IDLE

            if rule == "audio_state":
                if audio_state and audio_state in _VALID_STATES:
                    return State(audio_state)

            # Conditional rule: check conditions and return corresponding state
            if isinstance(rule, dict):
                for state_str, conditions in rule.items():
                    if state_str in _VALID_STATES and self._conditions_match(
                        conditions,
                        media_session_state=media_session_state,
                        wake_lock_size=wake_lock_size,
                        audio_state=audio_state,
                    ):
                        return State(state_str)

        return None

    @staticmethod
    def _conditions_match(
        conditions: dict[str, Any],
        *,
        media_session_state: int | None = None,
        wake_lock_size: int | None = None,
        audio_state: str | None = None,
    ) -> bool:
        """Check whether all conditions in the dict are satisfied.

        Parameters
        ----------
        conditions : dict
            A mapping of property names to expected values.
        media_session_state : int or None
            The media session playback state.
        wake_lock_size : int or None
            The current wake lock size.
        audio_state : str or None
            The audio state string.

        Returns
        -------
        bool
            True if all conditions are met.

        """
        for key, val in conditions.items():
            if key == "media_session_state":
                if media_session_state is None or media_session_state != val:
                    return False
            elif key == "wake_lock_size":
                if wake_lock_size is None or wake_lock_size != val:
                    return False
            elif key == "audio_state":
                if audio_state is None or audio_state != val:
                    return False
            else:
                return False
        return True

    @classmethod
    def validate_rules(cls, rules: dict[str, list[Any]]) -> None:
        """Validate the state detection rules.

        Parameters
        ----------
        rules : dict
            The rules to validate.

        Raises
        ------
        InvalidStateDetectionRuleError
            If any rule is invalid.

        """
        for app_id, app_rules in rules.items():
            if not isinstance(app_id, str):
                raise InvalidStateDetectionRuleError(app_id, "App ID must be a string")
            if not isinstance(app_rules, list):
                raise InvalidStateDetectionRuleError(app_rules, f"Rules for '{app_id}' must be a list")

            for rule in app_rules:
                cls._validate_single_rule(rule)

    @classmethod
    def _validate_single_rule(cls, rule: Any) -> None:
        """Validate a single rule entry.

        Parameters
        ----------
        rule : Any
            The rule to validate.

        Raises
        ------
        InvalidStateDetectionRuleError
            If the rule is invalid.

        """
        if isinstance(rule, str):
            if rule not in _VALID_STATES and rule not in _VALID_STATE_PROPERTIES:
                raise InvalidStateDetectionRuleError(
                    rule,
                    f"String rule must be a valid state {_VALID_STATES} or property {_VALID_STATE_PROPERTIES}",
                )
        elif isinstance(rule, dict):
            for state_str, conditions in rule.items():
                if state_str not in _VALID_STATES:
                    raise InvalidStateDetectionRuleError(
                        rule,
                        f"'{state_str}' is not a valid state",
                    )
                if not isinstance(conditions, dict):
                    raise InvalidStateDetectionRuleError(
                        rule,
                        f"Conditions for state '{state_str}' must be a dict",
                    )
                for prop, value in conditions.items():
                    if prop not in _VALID_PROPERTIES:
                        raise InvalidStateDetectionRuleError(
                            rule,
                            f"Invalid property '{prop}', must be one of {_VALID_PROPERTIES}",
                        )
                    expected_type = _VALID_PROPERTY_TYPES[prop]
                    if not isinstance(value, expected_type):
                        raise InvalidStateDetectionRuleError(
                            rule,
                            f"Value for '{prop}' must be {expected_type.__name__}, got {type(value).__name__}",
                        )
        else:
            raise InvalidStateDetectionRuleError(rule, "Rule must be a string or dict")

    def update_rules(self, rules: dict[str, list[Any]]) -> None:
        """Update the rules (merge with existing).

        Parameters
        ----------
        rules : dict
            New rules to merge into the existing rules.

        """
        self.validate_rules(rules)
        self._rules.update(rules)

    def set_app_rules(self, app_id: str, rules: list[Any]) -> None:
        """Set the rules for a specific app.

        Parameters
        ----------
        app_id : str
            The application identifier.
        rules : list
            The rules for the application.

        """
        self.validate_rules({app_id: rules})
        self._rules[app_id] = rules

    def remove_app_rules(self, app_id: str) -> None:
        """Remove the rules for a specific app.

        Parameters
        ----------
        app_id : str
            The application identifier to remove.

        """
        self._rules.pop(app_id, None)
