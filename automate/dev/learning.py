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

from automate.dev.verification_engine import deterministic_id, canonical_json

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
MAX_EXPERIENCE_BYTES = 500_000
MAX_LESSON_BYTES = 200_000
MAX_EVOLUTION_BYTES = 200_000


class LearningError(ValueError):
    """Raised when a learning artifact violates the learning boundary."""


@dataclass(frozen=True)
class StrategyRecommendation:
    strategy_id: str
    attempts: int
    successes: int
    failures: int
    contradictions: int
    unknowns: int
    conservative_score: float
    confidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "attempts": self.attempts,
            "successes": self.successes,
            "failures": self.failures,
            "contradictions": self.contradictions,
            "unknowns": self.unknowns,
            "conservative_score": round(self.conservative_score, 6),
            "confidence": self.confidence,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate(value: Mapping[str, Any], schema_path: Path, *, max_bytes: int) -> list[str]:
    raw = canonical_json(value).encode("utf-8")
    if len(raw) > max_bytes:
        return [f"learning artifact exceeds {max_bytes} bytes"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return [err.message for err in Draft202012Validator(schema).iter_errors(value)]


def validate_experience(value: Mapping[str, Any]) -> list[str]:
    return _validate(value, EXPERIENCE_SCHEMA, max_bytes=MAX_EXPERIENCE_BYTES)


def validate_lesson(value: Mapping[str, Any]) -> list[str]:
    return _validate(value, LESSON_SCHEMA, max_bytes=MAX_LESSON_BYTES)


def validate_evolution_proposal(value: Mapping[str, Any]) -> list[str]:
    return _validate(value, EVOLUTION_SCHEMA, max_bytes=MAX_EVOLUTION_BYTES)


def build_experience(
    *,
    action_cycle_id: str,
    outcome: str,
    task_kind: str,
    task_target: str,
    strategy_id: str,
    strategy_name: str,
    observation: str,
    evidence_refs: Iterable[Mapping[str, Any]] = (),
    failure_class: str | None = None,
    repository: str = "rynahmed101-sys/automate",
    revision: str | None = None,
    correlation_id: str | None = None,
    reproducible: bool | None = None,
) -> dict[str, Any]:
    if outcome not in OUTCOMES:
        raise LearningError(f"unknown experience outcome: {outcome}")
    created_at = utc_now()
    payload = {
        "schema_version": "automate.learning_experience.v1",
        "action_cycle_id": action_cycle_id,
        "outcome": outcome,
        "task": {"kind": task_kind, "target": task_target},
        "strategy": {"strategy_id": strategy_id, "name": strategy_name},
        "observation": {
            "summary": observation,
            "reproducible": reproducible,
        },
        "failure_class": failure_class,
        "evidence_refs": [dict(ref) for ref in evidence_refs],
        "provenance": {
            "repository": repository,
            "revision": revision,
            "correlation_id": correlation_id,
            "created_at": created_at,
        },
    }
    experience_id = deterministic_id(
        "exp",
        action_cycle_id,
        outcome,
        task_kind,
        task_target,
        strategy_id,
        observation,
        payload["evidence_refs"],
    )
    payload["experience_id"] = experience_id
    errors = validate_experience(payload)
    if errors:
        raise LearningError("; ".join(errors))
    return payload


def build_lesson(
    *,
    lesson_type: str,
    statement: str,
    scope: Mapping[str, Any],
    supporting_experience_ids: Iterable[str],
    preconditions: Iterable[str] = (),
    expected_effect: str = "",
    verification_evidence: Iterable[Mapping[str, Any]] = (),
    status: str = "CANDIDATE",
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ids = sorted({str(x) for x in supporting_experience_ids if str(x)})
    if not ids:
        raise LearningError("a lesson needs at least one supporting experience")
    if status not in LESSON_STATUSES:
        raise LearningError(f"unknown lesson status: {status}")
    body = {
        "schema_version": "automate.learning_lesson.v1",
        "lesson_type": lesson_type,
        "statement": statement,
        "scope": dict(scope),
        "preconditions": [str(x) for x in preconditions],
        "expected_effect": expected_effect,
        "supporting_experience_ids": ids,
        "verification_evidence": [dict(x) for x in verification_evidence],
        "status": status,
        "provenance": dict(provenance or {"created_at": utc_now()}),
    }
    body["lesson_id"] = deterministic_id(
        "les",
        lesson_type,
        statement,
        body["scope"],
        ids,
    )
    errors = validate_lesson(body)
    if errors:
        raise LearningError("; ".join(errors))
    return body


def build_evolution_proposal(
    *,
    kind: str,
    subject: str,
    rationale: str,
    expected_benefit: str,
    evidence_refs: Iterable[Mapping[str, Any]],
    regression_requirements: Iterable[str],
    rollback: str,
    constitutional: bool = False,
    status: str = "CANDIDATE",
) -> dict[str, Any]:
    if kind not in EVOLUTION_KINDS:
        raise LearningError(f"unknown evolution kind: {kind}")
    classification = "CONSTITUTIONAL" if constitutional or kind == "governance" else "MUTABLE"
    body = {
        "schema_version": "automate.system_evolution_proposal.v1",
        "kind": kind,
        "classification": classification,
        "subject": subject,
        "rationale": rationale,
        "expected_benefit": expected_benefit,
        "evidence_refs": [dict(x) for x in evidence_refs],
        "regression_requirements": [str(x) for x in regression_requirements],
        "rollback": rollback,
        "status": status,
        "auto_promotable": classification == "MUTABLE",
        "provenance": {"created_at": utc_now()},
    }
    body["proposal_id"] = deterministic_id(
        "evo",
        kind,
        classification,
        subject,
        rationale,
        body["evidence_refs"],
    )
    errors = validate_evolution_proposal(body)
    if errors:
        raise LearningError("; ".join(errors))
    return body


class LearningStore:
    """Append-only experience/lesson ledger with explicit promotion events."""

    def __init__(self, path: str | Path = "data/learning.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS experiences("
            "id TEXT PRIMARY KEY, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL, "
            "created_at TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS lessons("
            "id TEXT PRIMARY KEY, status TEXT NOT NULL, payload_json TEXT NOT NULL, "
            "payload_sha256 TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS lesson_events("
            "event_id TEXT PRIMARY KEY, lesson_id TEXT NOT NULL, from_status TEXT NOT NULL, "
            "to_status TEXT NOT NULL, reason TEXT NOT NULL, evidence_json TEXT NOT NULL, "
            "created_at TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS evolution_proposals("
            "id TEXT PRIMARY KEY, status TEXT NOT NULL, payload_json TEXT NOT NULL, "
            "payload_sha256 TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def add_experience(self, experience: Mapping[str, Any]) -> str:
        errors = validate_experience(experience)
        if errors:
            raise LearningError("; ".join(errors))
        eid = str(experience["experience_id"])
        body = canonical_json(experience)
        self.db.execute(
            "INSERT OR IGNORE INTO experiences(id,payload_json,payload_sha256,created_at) VALUES(?,?,?,?)",
            (eid, body, hashlib.sha256(body.encode()).hexdigest(), experience["provenance"]["created_at"]),
        )
        self.db.commit()
        return eid

    def get_experience(self, experience_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT payload_json FROM experiences WHERE id=?", (experience_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def add_lesson(self, lesson: Mapping[str, Any]) -> str:
        errors = validate_lesson(lesson)
        if errors:
            raise LearningError("; ".join(errors))
        missing = [
            eid for eid in lesson["supporting_experience_ids"]
            if self.get_experience(eid) is None
        ]
        if missing:
            raise LearningError("lesson references unknown experiences: " + ", ".join(missing))
        lid = str(lesson["lesson_id"])
        body = canonical_json(lesson)
        self.db.execute(
            "INSERT OR IGNORE INTO lessons(id,status,payload_json,payload_sha256,created_at) VALUES(?,?,?,?,?)",
            (lid, lesson["status"], body, hashlib.sha256(body.encode()).hexdigest(), utc_now()),
        )
        self.db.commit()
        return lid

    def get_lesson(self, lesson_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT payload_json FROM lessons WHERE id=?", (lesson_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def transition_lesson(
        self,
        lesson_id: str,
        to_status: str,
        *,
        reason: str,
        evidence: Iterable[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        lesson = self.get_lesson(lesson_id)
        if lesson is None:
            raise LearningError(f"unknown lesson: {lesson_id}")
        current = lesson["status"]
        if to_status not in LESSON_STATUSES:
            raise LearningError(f"unknown lesson status: {to_status}")
        if to_status not in LESSON_TRANSITIONS[current]:
            raise LearningError(f"invalid lesson transition: {current} -> {to_status}")
        evidence_list = [dict(x) for x in evidence]
        if to_status in {"VERIFIED", "ADOPTED"} and not evidence_list:
            raise LearningError(f"{to_status} requires explicit verification evidence")
        if to_status == "ADOPTED":
            validation = _validate_adoption_evidence(evidence_list)
            if validation:
                raise LearningError(validation)

        lesson["status"] = to_status
        lesson["verification_evidence"] = [
            *lesson.get("verification_evidence", []),
            *evidence_list,
        ]
        body = canonical_json(lesson)
        self.db.execute(
            "UPDATE lessons SET status=?, payload_json=?, payload_sha256=? WHERE id=?",
            (to_status, body, hashlib.sha256(body.encode()).hexdigest(), lesson_id),
        )
        event_id = deterministic_id("lev", lesson_id, current, to_status, reason, evidence_list)
        self.db.execute(
            "INSERT OR IGNORE INTO lesson_events(event_id,lesson_id,from_status,to_status,reason,evidence_json,created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (event_id, lesson_id, current, to_status, reason, canonical_json(evidence_list), utc_now()),
        )
        self.db.commit()
        return lesson

    def list_adopted_lessons(self, *, lesson_type: str | None = None) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT payload_json FROM lessons WHERE status='ADOPTED' ORDER BY created_at, id"
        ).fetchall()
        lessons = [json.loads(row[0]) for row in rows]
        if lesson_type is not None:
            lessons = [x for x in lessons if x.get("lesson_type") == lesson_type]
        return lessons

    def strategy_recommendations(
        self,
        *,
        task_kind: str,
        task_target: str | None = None,
    ) -> list[StrategyRecommendation]:
        rows = self.db.execute("SELECT payload_json FROM experiences ORDER BY created_at, id").fetchall()
        buckets: dict[str, dict[str, int]] = {}
        for row in rows:
            exp = json.loads(row[0])
            if exp["task"]["kind"] != task_kind:
                continue
            if task_target is not None and exp["task"]["target"] != task_target:
                continue
            sid = exp["strategy"]["strategy_id"]
            bucket = buckets.setdefault(
                sid,
                {"success": 0, "failure": 0, "contradiction": 0, "unknown": 0},
            )
            bucket[exp["outcome"]] += 1

        recommendations: list[StrategyRecommendation] = []
        for sid, counts in buckets.items():
            effective = counts["success"] + counts["failure"] + counts["contradiction"]
            attempts = effective + counts["unknown"]
            if effective == 0:
                score = 0.0
            else:
                # Wilson lower bound for the success proportion. This is deliberately
                # conservative: a strategy with few successes is not rewarded merely
                # because we lack enough failures to challenge it.
                p = counts["success"] / effective
                z = 1.96
                denom = 1 + (z * z) / effective
                centre = p + (z * z) / (2 * effective)
                spread = z * math.sqrt((p * (1 - p) / effective) + (z * z / (4 * effective * effective)))
                score = max(0.0, (centre - spread) / denom)
            confidence = (
                "low" if attempts < 3 else
                "medium" if attempts < 10 else
                "high"
            )
            recommendations.append(
                StrategyRecommendation(
                    sid,
                    attempts,
                    counts["success"],
                    counts["failure"],
                    counts["contradiction"],
                    counts["unknown"],
                    score,
                    confidence,
                )
            )
        return sorted(
            recommendations,
            key=lambda x: (-x.conservative_score, -x.attempts, x.strategy_id),
        )

    def select_strategy(
        self,
        *,
        task_kind: str,
        task_target: str,
        default_strategy_id: str = "frontier-default",
        minimum_attempts: int = 3,
        minimum_conservative_score: float = 0.50,
    ) -> dict[str, Any]:
        """Select a learned strategy only when history is strong enough to displace the default.

        This is deliberately conservative. Sparse experience can inform telemetry but
        cannot silently steer autonomous execution.
        """
        recommendations = self.strategy_recommendations(
            task_kind=task_kind,
            task_target=task_target,
        )
        if not recommendations:
            return {
                "strategy_id": default_strategy_id,
                "source": "default",
                "confidence": "none",
                "reason": "no historical experience for this task",
            }
        best = recommendations[0]
        if (
            best.attempts >= minimum_attempts
            and best.conservative_score >= minimum_conservative_score
            and best.confidence in {"medium", "high"}
        ):
            return {
                "strategy_id": best.strategy_id,
                "source": "learned_experience",
                "confidence": best.confidence,
                "reason": "conservative historical evidence cleared the selection threshold",
                "evidence": best.to_dict(),
            }
        return {
            "strategy_id": default_strategy_id,
            "source": "default",
            "confidence": best.confidence,
            "reason": "historical evidence is too sparse or weak to override the default",
            "best_observed": best.to_dict(),
        }

    def failure_lesson_candidates(self, *, min_repetitions: int = 2) -> list[dict[str, Any]]:
        """Generate deterministic candidate lessons from repeated failure classes.

        This is intentionally a candidate generator, not a root-cause oracle.
        Repeated coincidence is evidence for investigation, not proof of causality.
        """
        if min_repetitions < 2:
            raise LearningError("min_repetitions must be at least 2")
        rows = self.db.execute("SELECT payload_json FROM experiences ORDER BY created_at, id").fetchall()
        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for row in rows:
            exp = json.loads(row[0])
            if exp["outcome"] != "failure" or not exp.get("failure_class"):
                continue
            key = (
                exp["task"]["kind"],
                exp["task"]["target"],
                str(exp["failure_class"]),
            )
            groups.setdefault(key, []).append(exp)

        candidates: list[dict[str, Any]] = []
        for (kind, target, failure_class), experiences in sorted(groups.items()):
            if len(experiences) < min_repetitions:
                continue
            ids = [x["experience_id"] for x in experiences]
            candidates.append(
                build_lesson(
                    lesson_type="failure",
                    statement=(
                        f"Repeated {failure_class} failures were observed for "
                        f"{kind}:{target}; investigate the shared failure mechanism "
                        "before retrying the same strategy."
                    ),
                    scope={"task_kind": kind, "task_target": target, "failure_class": failure_class},
                    supporting_experience_ids=ids,
                    expected_effect="Avoid repeating an unchallenged failure pattern.",
                )
            )
        return candidates

    def snapshot(self) -> dict[str, Any]:
        experience_count = self.db.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
        lesson_rows = self.db.execute(
            "SELECT status, COUNT(*) FROM lessons GROUP BY status"
        ).fetchall()
        evolution_rows = self.db.execute(
            "SELECT status, COUNT(*) FROM evolution_proposals GROUP BY status"
        ).fetchall()
        return {
            "schema_version": "automate.learning_snapshot.v1",
            "experience_count": experience_count,
            "lesson_counts": {status: count for status, count in lesson_rows},
            "evolution_proposal_counts": {status: count for status, count in evolution_rows},
            "adopted_strategy_lesson_count": len(self.list_adopted_lessons(lesson_type="strategy")),
            "strategy_selection_is_conservative": True,
        }


def _validate_adoption_evidence(evidence: list[Mapping[str, Any]]) -> str | None:
    if not any(
        str(item.get("independence", "")).lower() in {
            "independent", "independent_route", "cross_engine", "cross_checked"
        }
        for item in evidence
    ):
        return "adoption requires at least one explicitly independent verification evidence item"
    return None


def admission_decision(
    proposal: Mapping[str, Any],
    *,
    verified_evidence_count: int,
    regression_results: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the fail-closed admission decision for a system-evolution proposal."""
    errors = validate_evolution_proposal(proposal)
    if errors:
        return {"admit": False, "status": "INVALID", "reasons": errors}

    if proposal["status"] != "CANDIDATE":
        return {"admit": False, "status": "BLOCKED", "reasons": ["proposal is not in CANDIDATE state"]}

    if proposal["classification"] == "CONSTITUTIONAL":
        return {
            "admit": False,
            "status": "CONSTITUTIONAL_REVIEW_REQUIRED",
            "reasons": [
                "constitutional changes cannot be auto-promoted",
                "a separately governed authority review is required",
            ],
        }

    if verified_evidence_count < 1:
        return {"admit": False, "status": "INSUFFICIENT_EVIDENCE", "reasons": ["no verified evidence"]}

    regressions = list(regression_results)
    failed = [x for x in regressions if x.get("status") not in {"passed", "verified"}]
    if not regressions:
        return {"admit": False, "status": "REGRESSION_EVIDENCE_REQUIRED", "reasons": ["no regression results"]}

    if failed:
        return {
            "admit": False,
            "status": "REGRESSION_FAILED",
            "reasons": ["one or more required regression checks failed"],
            "failed_regressions": failed,
        }

    return {
        "admit": True,
        "status": "READY_FOR_VERIFICATION_ENGINE",
        "reasons": [
            "proposal is mutable",
            "verified evidence exists",
            "all supplied regression checks passed",
        ],
    }
