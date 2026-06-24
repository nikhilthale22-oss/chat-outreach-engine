"""The Pitch copy, shared by the single-send CLI and the batch runner.

Two variants we A/B (each lands inside the Brand's own chat widget):
- A: converts shoppers / CVR angle.
- B: raises average order value / AOV (upsell) angle.

Nikhil's voice + copy rules: short plain sentences, no em dashes, the free-mock risk
reversal, the $100/mo first-10-clients anchor. Keep the signature on its own lines.
"""
from __future__ import annotations

PITCH_A = (
    "Hey, saw you don't have an AI chatbot on your site. "
    "I can build one that converts your shoppers (increases your CVR). "
    "Built one recently for Tusq apparel. "
    "I'll build it for free on a mock site first so you can test it, "
    "and we only make it live once you are satisfied. Would you be interested?\n\n"
    "Nikhil Thale, Founder, Postlist\n"
    "(flat $100/month for the first 10 clients since I'm gathering feedback)"
)

PITCH_B = (
    "Hey, saw you don't have an AI chatbot on your site. "
    "I can build one that gets your shoppers to add more to their cart "
    "(raises your average order value). "
    "Built one recently for Tusq apparel. "
    "I'll build it for free on a mock site first so you can test it, "
    "and we only make it live once you are satisfied. Would you be interested?\n\n"
    "Nikhil Thale, Founder, Postlist\n"
    "(flat $100/month for the first 10 clients since I'm gathering feedback)"
)

PITCHES = {"A": PITCH_A, "B": PITCH_B}
