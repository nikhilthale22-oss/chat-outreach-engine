"""The Router (Phase 2): turn a Detection into a send-or-skip decision.

One rule set, every store:
  no widget       -> skip (no_widget)
  gated vendor    -> skip (gated)        # pure volume: never fight a locked door
  vendor we can reach -> send by its method (api / headed / form)
  anything else   -> skip (no_method)    # vendor we have no card for yet

The reason is machine-readable so the scale layer can log a per-store scoreboard.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import registry


@dataclass(frozen=True)
class Route:
    action: str            # "send" | "skip"
    method: str | None     # "api" | "headed" | "form" when action == "send", else None
    reason: str            # "reachable" | "no_widget" | "gated" | "no_method"


def route(detection) -> Route:
    if not detection.has_widget:
        return Route("skip", None, "no_widget")
    vendor = detection.vendor
    if vendor in registry.GATED_VENDORS:
        return Route("skip", None, "gated")
    method = registry.VENDOR_METHOD.get(vendor)
    if method is None:
        return Route("skip", None, "no_method")
    return Route("send", method, "reachable")
