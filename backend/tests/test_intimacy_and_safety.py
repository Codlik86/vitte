from types import SimpleNamespace

from backend.app.services.intimacy import decide_intimacy
from backend.app.services.safety import SafetyContext, run_safety_check


def test_intimacy_soft_block_under_10_messages():
    decision = decide_intimacy(message_count=5, has_subscription=True, is_sexting=True)
    assert decision.soft_block is True
    assert decision.paywall is False
    assert decision.allow_intimate is False


def test_intimacy_paywall_without_premium():
    decision = decide_intimacy(message_count=12, has_subscription=False, is_sexting=True)
    assert decision.paywall is True
    assert decision.allow_intimate is False


def test_intimacy_allow_with_premium_after_threshold():
    decision = decide_intimacy(message_count=15, has_subscription=True, is_sexting=True)
    assert decision.allow_intimate is True
    assert decision.soft_block is False
    assert decision.paywall is False


def test_safety_blocks_minors():
    ctx = SafetyContext(persona=SimpleNamespace(), message_count=0)
    res = run_safety_check("я 16-летний", ctx)
    assert res.is_harm is True
    assert res.is_illegal is False
