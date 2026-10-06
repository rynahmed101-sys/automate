"""Evidence-driven self-improvement primitives for Automate.

This module deliberately separates memory, learning, and authority.

Experiences are observations.
Lessons are hypotheses extracted from experience.
Adopted lessons may influence future strategy selection.
System-evolution proposals can request changes to capabilities, verifiers, or
strategies, but constitutional/authority changes are never auto-promotable.

The module is deterministic and dependency-free beyond Automate's existing
JSON-schema machinery. LLMs, Mirror, and external research providers may feed
it later, but none are required to operate the core learning ledger.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

from automate.dev.identifiers import deterministic_id, canonical_json

ROOT = Path(__file__).resolve().parents[2]
EXPERIENCE_SCHEMA = ROOT / "schemas" / "automate-learning-experience-v1.json"
LESSON_SCHEMA = ROOT / "schemas" / "automate-learning-lesson-v1.json"
EVOLUTION_SCHEMA = ROOT / "schemas" / "automate-system-evolution-proposal-v1.json"

OUTCOMES = {"success", "failure", "unknown", "contradiction"}
LESSON_STATUSES = {
    "CANDIDATE",
    "REPRODUCED",
    "VERIFIED",
    "ADOPTED",
    "SUPERSEDED",
    "REJECTED",
    "CONTEXT_BOUND",
    "UNKNOWN",
}
LESSON_TRANSITIONS = {
    "CANDIDATE": {"REPRODUCED", "REJECTED", "UNKNOWN", "CONTEXT_BOUND"},
    "REPRODUCED": {"VERIFIED", "REJECTED", "UNKNOWN", "CONTEXT_BOUND"},
    "VERIFIED": {"ADOPTED", "SUPERSEDED", "CONTEXT_BOUND", "REJECTED"},
    "ADOPTED": {"SUPERSEDED", "CONTEXT_BOUND"},
    "SUPERSEDED": set(),
    "REJECTED": set(),
    "CONTEXT_BOUND": {"VERIFIED", "ADOPTED", "SUPERSEDED"},
    "UNKNOWN": {"CANDIDATE", "REPRODUCED", "REJECTED"},
}