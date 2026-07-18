"""Tests for the StateDetectionEngine."""

from __future__ import annotations

import pytest

from pyt_androidtv.basetv.state import StateDetectionEngine
from pyt_androidtv.exceptions import InvalidStateDetectionRuleError
from pyt_androidtv.models import State


class TestStateDetectionEngineNoRules:
    """Tests for when no rules are configured."""

    def test_no_rules_returns_none(self) -> None:
        """With no rules, detect_state should always return None."""
        engine = StateDetectionEngine()
        result = engine.detect_state(
            current_app="com.example.app",
            media_session_state=3,
            wake_lock_size=2,
            audio_state="playing",
        )
        assert result is None

    def test_none_rules_returns_none(self) -> None:
        """With None rules, detect_state should always return None."""
        engine = StateDetectionEngine(None)
        result = engine.detect_state(current_app="com.example.app")
        assert result is None

    def test_empty_rules_returns_none(self) -> None:
        """With empty rules dict, detect_state should always return None."""
        engine = StateDetectionEngine({})
        result = engine.detect_state(current_app="com.example.app")
        assert result is None

    def test_unknown_app_returns_none(self) -> None:
        """If the current app is not in the rules, return None."""
        engine = StateDetectionEngine({"com.known.app": ["idle"]})
        result = engine.detect_state(current_app="com.unknown.app")
        assert result is None

    def test_none_current_app_returns_none(self) -> None:
        """If current_app is None, return None."""
        engine = StateDetectionEngine({"com.known.app": ["idle"]})
        result = engine.detect_state(current_app=None)
        assert result is None


class TestFixedStateRules:
    """Tests for fixed state detection rules."""

    def test_idle_state(self) -> None:
        """A fixed 'idle' rule should return State.IDLE."""
        engine = StateDetectionEngine({"com.example.app": ["idle"]})
        result = engine.detect_state(current_app="com.example.app")
        assert result == State.IDLE

    def test_playing_state(self) -> None:
        """A fixed 'playing' rule should return State.PLAYING."""
        engine = StateDetectionEngine({"com.example.app": ["playing"]})
        result = engine.detect_state(current_app="com.example.app")
        assert result == State.PLAYING

    def test_paused_state(self) -> None:
        """A fixed 'paused' rule should return State.PAUSED."""
        engine = StateDetectionEngine({"com.example.app": ["paused"]})
        result = engine.detect_state(current_app="com.example.app")
        assert result == State.PAUSED

    def test_standby_state(self) -> None:
        """A fixed 'standby' rule should return State.STANDBY."""
        engine = StateDetectionEngine({"com.example.app": ["standby"]})
        result = engine.detect_state(current_app="com.example.app")
        assert result == State.STANDBY

    def test_off_state(self) -> None:
        """A fixed 'off' rule should return State.OFF."""
        engine = StateDetectionEngine({"com.example.app": ["off"]})
        result = engine.detect_state(current_app="com.example.app")
        assert result == State.OFF


class TestMediaSessionStateRules:
    """Tests for media_session_state property rules."""

    def test_media_session_state_playing(self) -> None:
        """media_session_state == 3 should return PLAYING."""
        engine = StateDetectionEngine({"com.example.app": ["media_session_state"]})
        result = engine.detect_state(
            current_app="com.example.app",
            media_session_state=3,
        )
        assert result == State.PLAYING

    def test_media_session_state_paused(self) -> None:
        """media_session_state == 2 should return PAUSED."""
        engine = StateDetectionEngine({"com.example.app": ["media_session_state"]})
        result = engine.detect_state(
            current_app="com.example.app",
            media_session_state=2,
        )
        assert result == State.PAUSED

    def test_media_session_state_idle(self) -> None:
        """media_session_state with other values should return IDLE."""
        engine = StateDetectionEngine({"com.example.app": ["media_session_state"]})
        result = engine.detect_state(
            current_app="com.example.app",
            media_session_state=1,
        )
        assert result == State.IDLE

    def test_media_session_state_none_skips(self) -> None:
        """media_session_state == None should skip to next rule."""
        engine = StateDetectionEngine({"com.example.app": ["media_session_state", "idle"]})
        result = engine.detect_state(
            current_app="com.example.app",
            media_session_state=None,
        )
        # Should skip media_session_state rule (None) and fall through to "idle"
        assert result == State.IDLE


class TestAudioStateRules:
    """Tests for audio_state property rules."""

    def test_audio_state_playing(self) -> None:
        """audio_state == 'playing' should return PLAYING."""
        engine = StateDetectionEngine({"com.example.app": ["audio_state"]})
        result = engine.detect_state(
            current_app="com.example.app",
            audio_state="playing",
        )
        assert result == State.PLAYING

    def test_audio_state_paused(self) -> None:
        """audio_state == 'paused' should return PAUSED."""
        engine = StateDetectionEngine({"com.example.app": ["audio_state"]})
        result = engine.detect_state(
            current_app="com.example.app",
            audio_state="paused",
        )
        assert result == State.PAUSED

    def test_audio_state_idle(self) -> None:
        """audio_state == 'idle' should return IDLE."""
        engine = StateDetectionEngine({"com.example.app": ["audio_state"]})
        result = engine.detect_state(
            current_app="com.example.app",
            audio_state="idle",
        )
        assert result == State.IDLE


class TestConditionalRules:
    """Tests for conditional (dict-based) state detection rules."""

    def test_plex_paused(self) -> None:
        """Plex rule: media_session_state=3, wake_lock_size=1 => PAUSED."""
        rules = {
            "com.plexapp.android": [
                {"paused": {"media_session_state": 3, "wake_lock_size": 1}},
                {"playing": {"media_session_state": 3}},
                "idle",
            ]
        }
        engine = StateDetectionEngine(rules)
        result = engine.detect_state(
            current_app="com.plexapp.android",
            media_session_state=3,
            wake_lock_size=1,
        )
        assert result == State.PAUSED

    def test_plex_playing(self) -> None:
        """Plex rule: media_session_state=3, wake_lock_size=2 => PLAYING."""
        rules = {
            "com.plexapp.android": [
                {"paused": {"media_session_state": 3, "wake_lock_size": 1}},
                {"playing": {"media_session_state": 3}},
                "idle",
            ]
        }
        engine = StateDetectionEngine(rules)
        result = engine.detect_state(
            current_app="com.plexapp.android",
            media_session_state=3,
            wake_lock_size=2,
        )
        assert result == State.PLAYING

    def test_plex_idle(self) -> None:
        """Plex rule: no matching conditions => IDLE."""
        rules = {
            "com.plexapp.android": [
                {"paused": {"media_session_state": 3, "wake_lock_size": 1}},
                {"playing": {"media_session_state": 3}},
                "idle",
            ]
        }
        engine = StateDetectionEngine(rules)
        result = engine.detect_state(
            current_app="com.plexapp.android",
            media_session_state=1,
            wake_lock_size=0,
        )
        assert result == State.IDLE

    def test_condition_with_none_values_does_not_match(self) -> None:
        """Conditions should not match if the property value is None."""
        rules = {"com.example.app": [{"playing": {"wake_lock_size": 3}}]}
        engine = StateDetectionEngine(rules)
        result = engine.detect_state(
            current_app="com.example.app",
            wake_lock_size=None,
        )
        assert result is None


class TestRuleManagement:
    """Tests for rule update, set, and remove operations."""

    def test_update_rules(self) -> None:
        """update_rules should merge new rules."""
        engine = StateDetectionEngine({"com.app1": ["idle"]})
        engine.update_rules({"com.app2": ["playing"]})

        assert engine.detect_state(current_app="com.app1") == State.IDLE
        assert engine.detect_state(current_app="com.app2") == State.PLAYING

    def test_update_rules_overwrites(self) -> None:
        """update_rules should overwrite existing app rules."""
        engine = StateDetectionEngine({"com.app1": ["idle"]})
        engine.update_rules({"com.app1": ["playing"]})

        assert engine.detect_state(current_app="com.app1") == State.PLAYING

    def test_set_app_rules(self) -> None:
        """set_app_rules should set rules for a specific app."""
        engine = StateDetectionEngine()
        engine.set_app_rules("com.app1", ["paused"])

        assert engine.detect_state(current_app="com.app1") == State.PAUSED

    def test_remove_app_rules(self) -> None:
        """remove_app_rules should remove rules for a specific app."""
        engine = StateDetectionEngine({"com.app1": ["idle"]})
        engine.remove_app_rules("com.app1")

        assert engine.detect_state(current_app="com.app1") is None

    def test_remove_nonexistent_app_does_not_raise(self) -> None:
        """remove_app_rules should not raise for non-existent apps."""
        engine = StateDetectionEngine()
        engine.remove_app_rules("com.nonexistent")  # Should not raise

    def test_rules_property_returns_copy(self) -> None:
        """The rules property should return a copy."""
        original = {"com.app1": ["idle"]}
        engine = StateDetectionEngine(original)
        rules_copy = engine.rules
        rules_copy["com.app2"] = ["playing"]

        # Original engine should not be affected
        assert "com.app2" not in engine.rules


class TestValidation:
    """Tests for rule validation."""

    def test_valid_string_rules(self) -> None:
        """Valid string rules should not raise."""
        StateDetectionEngine.validate_rules({
            "com.app": ["idle", "playing", "paused", "standby", "off", "media_session_state", "audio_state"]
        })

    def test_invalid_string_rule(self) -> None:
        """Invalid string rules should raise InvalidStateDetectionRuleError."""
        with pytest.raises(InvalidStateDetectionRuleError):
            StateDetectionEngine.validate_rules({"com.app": ["invalid_state"]})

    def test_invalid_rule_type(self) -> None:
        """Non-string, non-dict rules should raise."""
        with pytest.raises(InvalidStateDetectionRuleError):
            StateDetectionEngine.validate_rules({"com.app": [123]})  # type: ignore[list-item]

    def test_invalid_state_in_dict_rule(self) -> None:
        """Invalid state key in a dict rule should raise."""
        with pytest.raises(InvalidStateDetectionRuleError):
            StateDetectionEngine.validate_rules({"com.app": [{"invalid_state": {"wake_lock_size": 1}}]})

    def test_invalid_property_in_conditions(self) -> None:
        """Invalid property in conditions should raise."""
        with pytest.raises(InvalidStateDetectionRuleError):
            StateDetectionEngine.validate_rules({"com.app": [{"idle": {"invalid_prop": 1}}]})

    def test_invalid_value_type_in_conditions(self) -> None:
        """Wrong value type in conditions should raise."""
        with pytest.raises(InvalidStateDetectionRuleError):
            StateDetectionEngine.validate_rules({"com.app": [{"idle": {"wake_lock_size": "not_an_int"}}]})  # type: ignore[dict-item]

    def test_non_dict_conditions(self) -> None:
        """Non-dict conditions should raise."""
        with pytest.raises(InvalidStateDetectionRuleError):
            StateDetectionEngine.validate_rules({"com.app": [{"idle": "not_a_dict"}]})  # type: ignore[dict-item]

    def test_non_string_app_id(self) -> None:
        """Non-string app IDs should raise."""
        with pytest.raises(InvalidStateDetectionRuleError):
            StateDetectionEngine.validate_rules({123: ["idle"]})  # type: ignore[dict-item]

    def test_non_list_rules(self) -> None:
        """Non-list rules for an app should raise."""
        with pytest.raises(InvalidStateDetectionRuleError):
            StateDetectionEngine.validate_rules({"com.app": "idle"})  # type: ignore[dict-item]
