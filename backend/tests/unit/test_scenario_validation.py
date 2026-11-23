from app.engine.registry import load_scenario
from app.engine.validation import validate_scenario


def test_seeded_definitions_and_bad_reference():
    for slug in ["checkout-outage", "inventory-race", "analytics-timezone"]:
        definition = load_scenario(slug).model_dump()
        assert validate_scenario(definition).passed
        definition["facts"][0]["artifact_id"] = "missing"
        assert not validate_scenario(definition).passed


def test_untrusted_cost_and_remote_markup_are_rejected():
    d = load_scenario("checkout-outage").model_dump()
    d["action_catalog"][0]["cost"] = 0
    assert not validate_scenario(d).passed
    d = load_scenario("checkout-outage").model_dump()
    d["metadata"]["briefing"] = '<img src="https://tracking.example/image">'
    assert not validate_scenario(d).passed
