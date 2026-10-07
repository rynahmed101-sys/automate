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
EVOLUTION_KINDS = {"knowledge", "strategy", "verifier", "capability", "governance"}
EVOLUTION_CLASS = {"MUTABLE", "CONSTITUTIONAL"}
EVOLUTION_TRANSITIONS = {
    "CANDIDATE": {"VERIFIED", "REJECTED", "SUPERSEDED"},
    "VERIFIED": {"ADOPTED", "REJECTED", "SUPERSEDED"},