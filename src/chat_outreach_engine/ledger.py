"""The Ledger: a SQLite brand-state store.

Records each Brand, its current Stage, vendor, and Pitch variant, with an
append-only history of Stage changes. Enforces idempotency: a Brand past Queued
is never pitched again. Replaces the old flat pitched_brands.json.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

# Stages in order (CONTEXT.md). A Brand starts at Queued; "past Queued" = anything else.
STAGES = ("Queued", "Pitched", "Replied", "Call Booked", "Customer", "Dead")


class UnknownBrand(KeyError):
    """Raised when a Brand is referenced that the Ledger has never recorded."""


class UnknownStage(ValueError):
    """Raised when advancing to a Stage that is not in STAGES."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    def __init__(self, db_path):
        self._db = sqlite3.connect(str(db_path))
        self._db.row_factory = sqlite3.Row
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS brands (
                domain        TEXT PRIMARY KEY,
                vendor        TEXT,
                current_stage TEXT NOT NULL,
                pitch_variant TEXT,
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS stage_history (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                stage  TEXT NOT NULL,
                at     TEXT NOT NULL,
                note   TEXT
            );
            """
        )
        self._db.commit()

    # --- writes ---
    def add_brand(self, domain: str, vendor: str | None = None) -> None:
        """Record a new Brand at Queued. Idempotent: re-adding an existing Brand
        does NOT reset its Stage or history (no-op; vendor backfilled if newly known)."""
        existing = self._db.execute(
            "SELECT vendor FROM brands WHERE domain = ?", (domain,)
        ).fetchone()
        if existing is not None:
            if vendor and not existing["vendor"]:
                self._db.execute(
                    "UPDATE brands SET vendor = ?, updated_at = ? WHERE domain = ?",
                    (vendor, _now(), domain),
                )
                self._db.commit()
            return
        now = _now()
        self._db.execute(
            "INSERT INTO brands (domain, vendor, current_stage, pitch_variant, created_at, updated_at)"
            " VALUES (?, ?, 'Queued', NULL, ?, ?)",
            (domain, vendor, now, now),
        )
        self._db.execute(
            "INSERT INTO stage_history (domain, stage, at) VALUES (?, 'Queued', ?)",
            (domain, now),
        )
        self._db.commit()

    def advance(self, domain: str, to_stage: str, pitch_variant: str | None = None,
                note: str | None = None) -> None:
        """Move a Brand to a new Stage, appending to the history. An optional note
        records why (e.g. 'already has AI', 'no chat widget')."""
        if to_stage not in STAGES:
            raise UnknownStage(to_stage)
        row = self._db.execute(
            "SELECT pitch_variant FROM brands WHERE domain = ?", (domain,)
        ).fetchone()
        if row is None:
            raise UnknownBrand(domain)
        now = _now()
        variant = pitch_variant if pitch_variant is not None else row["pitch_variant"]
        self._db.execute(
            "UPDATE brands SET current_stage = ?, pitch_variant = ?, updated_at = ? WHERE domain = ?",
            (to_stage, variant, now, domain),
        )
        self._db.execute(
            "INSERT INTO stage_history (domain, stage, at, note) VALUES (?, ?, ?, ?)",
            (domain, to_stage, now, note),
        )
        self._db.commit()

    def mark_pitched(self, domain: str, pitch_variant: str) -> bool:
        """Advance a Brand to Pitched with its Pitch variant. Returns False and
        does nothing if the Brand is not Queued, so a Brand is never pitched twice."""
        if not self.can_pitch(domain):
            return False
        self.advance(domain, "Pitched", pitch_variant=pitch_variant)
        return True

    # --- reads ---
    def can_pitch(self, domain: str) -> bool:
        """A Brand may be pitched only while it is still Queued."""
        return self.get_stage(domain) == "Queued"

    def get_stage(self, domain: str) -> str:
        row = self._db.execute(
            "SELECT current_stage FROM brands WHERE domain = ?", (domain,)
        ).fetchone()
        if row is None:
            raise UnknownBrand(domain)
        return row["current_stage"]

    def get_pitch_variant(self, domain: str) -> str | None:
        row = self._db.execute(
            "SELECT pitch_variant FROM brands WHERE domain = ?", (domain,)
        ).fetchone()
        if row is None:
            raise UnknownBrand(domain)
        return row["pitch_variant"]

    def history(self, domain: str) -> list[tuple[str, str]]:
        """The append-only list of (stage, timestamp) for a Brand, in order."""
        if self._db.execute("SELECT 1 FROM brands WHERE domain = ?", (domain,)).fetchone() is None:
            raise UnknownBrand(domain)
        rows = self._db.execute(
            "SELECT stage, at FROM stage_history WHERE domain = ? ORDER BY id", (domain,)
        ).fetchall()
        return [(r["stage"], r["at"]) for r in rows]

    def list_by_stage(self, stage: str) -> list[str]:
        rows = self._db.execute(
            "SELECT domain FROM brands WHERE current_stage = ? ORDER BY domain", (stage,)
        ).fetchall()
        return [r["domain"] for r in rows]

    def list_by_vendor(self, vendor: str) -> list[str]:
        rows = self._db.execute(
            "SELECT domain FROM brands WHERE vendor = ? ORDER BY domain", (vendor,)
        ).fetchall()
        return [r["domain"] for r in rows]

    def close(self) -> None:
        self._db.close()
