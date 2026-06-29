"""The Pitch copy, shared by the single-send CLI and the batch runner.

Two variants we A/B (each lands inside the Brand's own chat widget):
- A: turn more visitors into buyers (CVR angle).
- B: get shoppers to add more to their cart (AOV / upsell angle).

One-way model: we only need to DELIVER the pitch. It carries our website (mercwise.com)
and booking link (cal.com/nikhil1/30min), so an interested merchant contacts us - we do
NOT rely on capturing an inbound reply. Nikhil's voice + copy rules: short plain
sentences, no em dashes, no jargon, under 75 words, the free-mock risk reversal, then
the two links plainly. No price in the cold message (it goes on the call).
"""
from __future__ import annotations

PITCH_A = (
    "Hey, saw you don't have an AI chatbot on your site. "
    "I build ones that turn more of your visitors into buyers. "
    "Built one recently for Tusq apparel. "
    "I'll set it up free on a mock version of your store so you can test it first, "
    "and it only goes live once you're happy. "
    "Here's my website: mercwise.com and here's my calendar: https://cal.com/nikhil1/30min"
)

PITCH_B = (
    "Hey, saw you don't have an AI chatbot on your site. "
    "I build ones that get shoppers to add more to their cart. "
    "Built one recently for Tusq apparel. "
    "I'll set it up free on a mock version of your store so you can test it first, "
    "and it only goes live once you're happy. "
    "Here's my website: mercwise.com and here's my calendar: https://cal.com/nikhil1/30min"
)

PITCHES = {"A": PITCH_A, "B": PITCH_B}
