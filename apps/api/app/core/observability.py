"""Allowlisted operational logs. Never pass user text, headers or exception strings."""

import structlog

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()]
)
log = structlog.get_logger("workquest")
