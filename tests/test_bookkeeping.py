from automate.dev.bookkeeping import BookkeepingError, build_bookkeeping_plan


def test_bookkeeping_updates_only_target_stage():
    inventory = {
        "capabilities": [
            {
                "id": "stage1b.series_expansions",
                "order": 160,
                "stage": "1B",
                "name": "Taylor, Maclaurin, and higher-order series expansions",
                "implementation_state": "planned",
                "authority": {"kind": "roadmap", "ref": "ledger"},
                "references": [{"type": "pr", "number": 1, "state": "open"}],
                "verification": {},
            },
            {
                "id": "stage1b.partial_derivatives",
                "order": 170,
                "stage": "1B",
                "name": "Partial derivatives and total differentials",
                "implementation_state": "planned",
                "authority": {"kind": "roadmap", "ref": "ledger"},
                "references": [],
                "verification": {},
            },
        ]
    }
    ledger = """# Ledger

## 1B. Calculus

- [ ] Taylor / Maclaurin series and higher-order expansions
- [ ] Partial derivatives and total differentials

**Control-plane frontier:** the next claimable capability is **Taylor / Maclaurin series and higher-order expansions**.

### Stage 1 exit condition

**Current status:** [~] Active. The next claimable capability is Taylor.

## 1C. General ODEs

- [ ] Separable first-order equations

**Current status:** [~] ODE work remains preserved.

"""
    plan = build_bookkeeping_plan(
        inventory,
        ledger,
        capability_id="stage1b.series_expansions",
        merge_sha="a" * 40,
        exact_head_ci_run=123,
        security_run=456,
    )
    out = plan["changes"][1]["content"]
    assert "- [x] Taylor / Maclaurin series and higher-order expansions" in out
    assert "- [ ] Partial derivatives and total differentials" in out
    assert "1C" in out
    assert "**Current status:** [~] ODE work remains preserved." in out


def test_bookkeeping_fails_closed_for_missing_ledger_anchor():
    inventory = {
        "capabilities": [{
            "id": "stage1b.series_expansions",
            "order": 160,
            "stage": "1B",
            "name": "Taylor, Maclaurin, and higher-order series expansions",
            "implementation_state": "planned",
            "authority": {"kind": "roadmap", "ref": "ledger"},
            "references": [],
            "verification": {},
        }]
    }
    try:
        build_bookkeeping_plan(
            inventory,
            "## 1B. Calculus\n\n- [ ] Completely unrelated capability\n",
            capability_id="stage1b.series_expansions",
            merge_sha="a" * 40,
            exact_head_ci_run=1,
            security_run=2,
        )
    except BookkeepingError as exc:
        assert "ambiguous" in str(exc)
    else:
        raise AssertionError("missing ledger anchor must block promotion")


def test_bookkeeping_does_not_promote_preserved_out_of_order_work_to_frontier():
    from automate.dev.inventory import next_action

    inventory = {
        "capabilities": [
            {
                "id": "stage1b.series_expansions",
                "order": 10,
                "stage": "1B",
                "name": "Taylor series",
                "implementation_state": "planned",
                "authority": {"kind": "roadmap", "ref": "ledger"},
                "references": [],
                "depends_on": [],
                "canonical_files": ["automate/backend/series.py"],
                "shared_integration_points": [],
                "verification": {},
            },
            {
                "id": "stage1c.ode",
                "order": 20,
                "stage": "1C",
                "name": "General ODEs",
                "implementation_state": "preserved_out_of_order",
                "authority": {"kind": "branch", "ref": "historical"},
                "references": [],
                "depends_on": [],
                "canonical_files": ["automate/backend/ode.py"],
                "shared_integration_points": [],
                "verification": {},
            },
            {
                "id": "stage1b.partial_derivatives",
                "order": 30,
                "stage": "1B",
                "name": "Partial derivatives",
                "implementation_state": "planned",
                "authority": {"kind": "roadmap", "ref": "ledger"},
                "references": [],
                "depends_on": [],
                "canonical_files": ["automate/backend/partials.py"],
                "shared_integration_points": [],
                "verification": {},
            },
        ]
    }
    assert next_action(inventory)["capability_id"] == "stage1b.series_expansions"
