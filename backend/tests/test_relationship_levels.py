import pytest

from backend.app.services.relationship_state import (
    RelationshipLevel,
    RelationshipState,
    derive_level_from_state,
    level_to_state,
    transition_level,
)
from backend.app.services.message_analysis import MessageAnalysis


def test_level_to_state_mapping():
    romantic = level_to_state(RelationshipLevel.ROMANTIC)
    assert romantic.trust_level >= 80
    friendly = level_to_state(RelationshipLevel.FRIENDLY)
    assert 30 <= friendly.trust_level <= 60
    init = level_to_state(RelationshipLevel.INIT)
    assert init.trust_level == 10


def test_derive_level_prefers_stored_level():
    state = RelationshipState(trust_level=10, closeness_level=5, relationship_level=RelationshipLevel.ROMANTIC)
    level = derive_level_from_state(state)
    assert level == RelationshipLevel.ROMANTIC


def test_transition_skips_rude_to_romantic():
    analysis = MessageAnalysis(is_rude=True)
    level = transition_level(RelationshipLevel.FRIENDLY, message_count=100, analysis=analysis)
    assert level == RelationshipLevel.FRIENDLY


def test_transition_promotes_flirty():
    analysis = MessageAnalysis(is_flirty=True)
    level = transition_level(RelationshipLevel.FRIENDLY, message_count=5, analysis=analysis)
    assert level == RelationshipLevel.ROMANTIC
