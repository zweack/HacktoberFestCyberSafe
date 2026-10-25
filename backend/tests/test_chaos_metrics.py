from app import metrics
from app.chaos import get_chaos, set_chaos
from app.schemas import ChaosSettings


def test_chaos_roundtrip():
    assert get_chaos().llm_down is False
    set_chaos(ChaosSettings(llm_down=True, telegram_failure_rate=0.5))
    assert get_chaos().llm_down is True and get_chaos().telegram_failure_rate == 0.5


def test_metrics_render():
    metrics.inc("cybersafe_test_total", verdict="scam")
    assert 'cybersafe_test_total{verdict="scam"} 1.0' in metrics.render()
