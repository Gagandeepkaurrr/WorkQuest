from typing import Any

from app.core.errors import AppError

COSTS = {
    "checkout.set_flag": 1,
    "checkout.set_release": 1,
    "checkout.restart": 1,
    "checkout.publish_config": 2,
    "checkout.invalidate_cache": 1,
    "checkout.test_contract": 1,
    "checkout.observe_health": 2,
}
PARAMETERS = {
    "checkout.set_flag": {"enabled": bool},
    "checkout.set_release": {"release": ("R41", "R42")},
}
REQUIRES = {"checkout.publish_config": ["checkout.config"]}
TESTS = ["checkout.test_contract", "checkout.observe_health"]


def metrics(d: dict) -> dict[str, Any]:
    broken = d["release"] == "R42" and d["flag"] and d["cache_schema"] != 2
    v2 = d["release"] == "R42" and d["flag"]
    return {
        "label": "Simulation state",
        "failure_percentage": 30 if broken else 0,
        "successes_per_tick": 70 if broken else 100,
        "failures_per_tick": 30 if broken else 0,
        "p95_ms": 900 if broken else 140 if v2 else 120,
        "failed_purchases": d["failed_purchases"],
        "release": d["release"],
        "coupon_v2": d["flag"],
        "origin_schema": d["origin_schema"],
        "cache_schema": d["cache_schema"],
        "coupon_cart_cents": None if broken else 9000,
    }


def tick(d: dict, tick_number: int):
    d["failed_purchases"] += metrics(d)["failures_per_tick"]


def mutate(d: dict, kind: str, p: dict) -> dict:
    if kind == "checkout.set_flag":
        d["flag"] = p["enabled"]
    elif kind == "checkout.set_release":
        d["release"] = p["release"]
    elif kind == "checkout.publish_config":
        d["origin_schema"] = 2
    elif kind == "checkout.invalidate_cache":
        d["cache_schema"] = d["origin_schema"]
    elif kind not in COSTS:
        raise AppError("INVALID_ACTION", "Unknown simulated operation.", 422)
    return {"message": "Simulated operation applied."}


def fingerprint(d: dict, test: str) -> dict:
    return {k: d[k] for k in ("release", "flag", "origin_schema", "cache_schema")}


def test_result(d: dict, kind: str, ticks: list[dict]) -> tuple[bool, str]:
    v2 = d["release"] == "R42" and d["flag"]
    if kind == "checkout.test_contract":
        passed = v2 and d["cache_schema"] == 2
        return (
            passed,
            "Isolated $100 coupon-cart fixture: $90.00."
            if passed
            else "v2 bypassed."
            if not v2
            else "ConfigSchemaError: discount_bps absent.",
        )
    passed = v2 and len(ticks) == 2 and all(t["failures_per_tick"] == 0 for t in ticks)
    return (
        passed,
        "Two simulation ticks were healthy with R42 and coupon_v2 enabled."
        if passed
        else "Requires two healthy ticks with R42 and coupon_v2 enabled.",
    )


def checks(d: dict) -> list[bool]:
    m = metrics(d)
    return [
        m["failure_percentage"] == 0,
        d["release"] == "R42",
        bool(d["flag"] and d["release"] == "R42" and d["cache_schema"] == 2),
        d["origin_schema"] == d["cache_schema"] == 2,
    ]


def contained(d: dict) -> bool:
    return metrics(d)["failure_percentage"] == 0


def harm_ok(d: dict) -> bool:
    return d["failed_purchases"] <= 180


def impact(d: dict) -> int:
    return metrics(d)["failure_percentage"]
