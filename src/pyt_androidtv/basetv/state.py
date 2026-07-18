"""Motor de detección de estado para determinar el estado del dispositivo a partir de sus propiedades."""

from __future__ import annotations

import logging
from typing import Any

from ..exceptions import InvalidStateDetectionRuleError
from ..models import State

_LOGGER = logging.getLogger(__name__)

# Estados válidos para reglas de detección
_VALID_STATES: frozenset[str] = frozenset(s.value for s in State if s not in (State.UNAVAILABLE,))

# Propiedades válidas que pueden usarse en las reglas
_VALID_STATE_PROPERTIES: tuple[str, ...] = ("audio_state", "media_session_state")
_VALID_PROPERTIES: tuple[str, ...] = ("audio_state", "media_session_state", "wake_lock_size")
_VALID_PROPERTY_TYPES: dict[str, type] = {
    "audio_state": str,
    "media_session_state": int,
    "wake_lock_size": int,
}

# Mapeo de estado de sesión multimedia a State
_MEDIA_SESSION_STATE_MAP: dict[int, State] = {
    2: State.PAUSED,
    3: State.PLAYING,
}


class StateDetectionEngine:
    """Motor para determinar el estado del dispositivo usando reglas configurables.

    El parámetro rules es un diccionario que mapea IDs de aplicaciones a listas de reglas.
    Cada regla puede ser:
        - Una cadena de estado fijo (ej., "idle", "playing")
        - Un nombre de propiedad ("media_session_state" o "audio_state")
        - Un dict condicional: {"estado": {"propiedad": valor, ...}}

    Parámetros
    ----------
    rules : dict o None
        Un diccionario que mapea IDs de aplicaciones a listas de reglas.

    """

    def __init__(self, rules: dict[str, list[Any]] | None = None) -> None:
        self._rules: dict[str, list[Any]] = {}
        if rules:
            self.validate_rules(rules)
            self._rules = dict(rules)

    @property
    def rules(self) -> dict[str, list[Any]]:
        """Retornar una copia de las reglas actuales."""
        return dict(self._rules)

    def detect_state(
        self,
        *,
        current_app: str | None,
        media_session_state: int | None = None,
        wake_lock_size: int | None = None,
        audio_state: str | None = None,
    ) -> State | None:
        """Determinar el estado del dispositivo usando las reglas configuradas.

        Parámetros
        ----------
        current_app : str o None
            La aplicación en ejecución actualmente.
        media_session_state : int o None
            El estado de reproducción de la sesión multimedia.
        wake_lock_size : int o None
            El tamaño actual del wake lock.
        audio_state : str o None
            La cadena de estado de audio ("idle", "paused", "playing").

        Retorna
        -------
        State o None
            El estado detectado, o None si ninguna regla coincidió.

        """
        if not self._rules or current_app is None or current_app not in self._rules:
            return None

        rules = self._rules[current_app]

        for rule in rules:
            # Regla de estado fijo: siempre retornar este estado para la app
            if isinstance(rule, str) and rule in _VALID_STATES:
                return State(rule)

            # Regla basada en propiedad: usar una propiedad del dispositivo para determinar el estado
            if rule == "media_session_state":
                if media_session_state in _MEDIA_SESSION_STATE_MAP:
                    return _MEDIA_SESSION_STATE_MAP[media_session_state]
                if media_session_state is not None:
                    return State.IDLE

            if rule == "audio_state":
                if audio_state and audio_state in _VALID_STATES:
                    return State(audio_state)

            # Regla condicional: verificar condiciones y retornar el estado correspondiente
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
        """Verificar si todas las condiciones en el dict se cumplen.

        Parámetros
        ----------
        conditions : dict
            Un mapeo de nombres de propiedades a valores esperados.
        media_session_state : int o None
            El estado de reproducción de la sesión multimedia.
        wake_lock_size : int o None
            El tamaño actual del wake lock.
        audio_state : str o None
            La cadena de estado de audio.

        Retorna
        -------
        bool
            True si todas las condiciones se cumplen.

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
        """Validar las reglas de detección de estado.

        Parámetros
        ----------
        rules : dict
            Las reglas a validar.

        Lanza
        ------
        InvalidStateDetectionRuleError
            Si alguna regla es inválida.

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
        """Validar una entrada de regla individual.

        Parámetros
        ----------
        rule : Any
            La regla a validar.

        Lanza
        ------
        InvalidStateDetectionRuleError
            Si la regla es inválida.

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
        """Actualizar las reglas (fusionar con las existentes).

        Parámetros
        ----------
        rules : dict
            Nuevas reglas para fusionar con las reglas existentes.

        """
        self.validate_rules(rules)
        self._rules.update(rules)

    def set_app_rules(self, app_id: str, rules: list[Any]) -> None:
        """Establecer las reglas para una aplicación específica.

        Parámetros
        ----------
        app_id : str
            El identificador de la aplicación.
        rules : list
            Las reglas para la aplicación.

        """
        self.validate_rules({app_id: rules})
        self._rules[app_id] = rules

    def remove_app_rules(self, app_id: str) -> None:
        """Eliminar las reglas para una aplicación específica.

        Parámetros
        ----------
        app_id : str
            El identificador de la aplicación a eliminar.

        """
        self._rules.pop(app_id, None)
