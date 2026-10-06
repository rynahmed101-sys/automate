"""
Command Line Interface (CLI) for Automate.
Supports both human-readable Rich console rendering and machine-readable JSON mode (--json)
for seamless integration with direct AI agents, automated verification pipelines, and CI/CD.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import click

from automate.theory.parser import parse_theory_file
from automate.core.graph import DerivationGraph
from automate.backend.dimension_backend import DimensionChecker
from automate.backend.sympy_backend import SymPyChecker
from automate.backend.lean_backend import LeanChecker
from automate.backend.numerical_backend import NumericalChecker
from automate.backend.statistical_backend import StatisticalChecker
from automate.backend.linear_algebra_backend import LinearAlgebraChecker
from automate.backend.vector_calculus_backend import VectorCalculusChecker
from automate.backend.electrostatics_backend import ElectrostaticsChecker
from automate.visualization.html_graph import generate_interactive_html
from automate.visualization.terminal import print_graph_summary, print_assumption_report, console
from automate.demo import run_harmonic_oscillator_demo
from automate.ai.schemas import AIContext
from automate.ir.tensors import TensorEquation
from automate.ai import (
    build_ai_context,
    validate_ai_proposal,
    apply_and_verify_proposal,
    get_provider,
    discover_available_providers,
    DerivationProposal
)
from automate.theory.rules import RuleRegistry
from automate.dev.inventory import summarize as capability_inventory_summary
from automate.dev.cli import capability


@click.group()
@click.version_option(version="0.2.0", prog_name="automate")
def main():
    """Automate: Local-first machine-checkable formal physics derivation engine."""
    pass


@main.command()
@click.option("--output-dir", "-o", default="output", help="Directory to save generated artifacts")
def demo(output_dir: str):
    """Run the complete canonical end-to-end harmonic oscillator demonstration."""
    run_harmonic_oscillator_demo(output_dir)


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def capabilities(as_json: bool):
    """Discover available verification backends, IR capabilities, and AI providers."""
    lean_checker = LeanChecker()
    providers = discover_available_providers()
    caps = {
        "schema_version": "0.2.0",
        "ir": True,
        "tensors": True,
        "actions": True,
        "differential_geometry": True,
        "symbolic": True,
        "dimensions": True,
        "numerical": True,
        "statistics": True,
        "linear_algebra": True,
        "vector_calculus": True,
        "lean4": lean_checker.is_available(),
        "lean4_version": lean_checker.version,
        "ai": True,
        "providers": providers,
        "rule_registry": {
            "count": len(RuleRegistry().list_rule_ids()),
            "rule_ids": RuleRegistry().list_rule_ids(),
        },
        "agent_contract": {
            "schema_version": "automate.agent.v1",
            "schema_command": "automate schema --name agent",
        },
        "development_control_plane": capability_inventory_summary(),
    }
    if as_json:
        click.echo(json.dumps(caps, indent=2))
    else:
        console.print("[bold cyan]Automate Capabilities Manifest (v0.2.0):[/bold cyan]")
        console.print(f"  * Core Typed IR & Tensors: [green]Active[/green]")
        console.print(f"  * Differential Geometry:   [green]Active[/green]")
        console.print(f"  * SymPy (Symbolic):        [green]Active[/green]")
        console.print(f"  * DimensionChecker:        [green]Active[/green]")
        console.print(f"  * Numerical (SciPy RK45):  [green]Active[/green]")
        console.print(f"  * Statistical (Inference): [green]Active[/green]")
        lean_status = "[green]Active[/green]" if caps["lean4"] else "[yellow]Inactive (Not Installed)[/yellow]"
        console.print(f"  * Lean 4 (Theorem Prover): {lean_status} ({caps['lean4_version']})")
        console.print(f"  * Universal AI Providers:  mock: [green]{providers['mock']}[/green], openai: [{ 'green' if providers['openai'] else 'dim'}]{providers['openai']}[/], local: [{ 'green' if providers['local'] else 'dim'}]{providers['local']}[/]")
        console.print(f"  * Agent Contract:           automate.agent.v1 (automate schema --name agent)")


@main.command()
@click.argument("theory_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output JSON graph path")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def parse(theory_file: str, output: str, as_json: bool):
    """Parse a declarative theory YAML/JSON file into canonical IR derivation graph."""
    graph = parse_theory_file(theory_file)
    out_path = output or f"{Path(theory_file).stem}_graph.json"
    Path(out_path).write_text(graph.to_json(), encoding="utf-8")
    if as_json:
        click.echo(json.dumps({
            "status": "PARSED",
            "file": theory_file,
            "output": out_path,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "assumptions": len(graph.assumptions)
        }, indent=2))
    else:
        console.print(f"[green][OK] Parsed '{theory_file}' into '{out_path}'[/green] ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")


@main.command()
@click.argument("theory_file", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def context(theory_file: str, as_json: bool):
    """Expose controlled mathematical context from a theory file for AI agents."""
    path = Path(theory_file)
    if path.suffix in (".yaml", ".yml"):
        graph = parse_theory_file(path)
    else:
        graph = DerivationGraph.from_json(path.read_text(encoding="utf-8"))

    ctx = build_ai_context(graph)
    ctx_dict = ctx.to_dict()
    if as_json:
        click.echo(json.dumps(ctx_dict, indent=2))
    else:
        console.print(f"[bold cyan]Mathematical Context for '{graph.name}':[/bold cyan]")
        console.print(f"  Graph Hash: [yellow]{ctx.graph_hash}[/yellow]")
        console.print(f"  Nodes: {len(ctx.nodes)} | Equations: {len(ctx.equations)} | Open Obligations: {len(ctx.open_obligations)}")
        console.print(f"  Available Transformation Rules: {len(ctx.available_rules)}")


@main.command()
@click.argument("proposal_file", type=click.Path(exists=True))
@click.option("--theory", "-t", default=None, type=click.Path(exists=True), help="Optional theory file to validate against")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def validate(proposal_file: str, theory: str, as_json: bool):
    """Validate an untrusted AI proposal against schema and graph dependencies."""
    proposal_data = json.loads(Path(proposal_file).read_text(encoding="utf-8"))
    graph = None
    if theory:
        p = Path(theory)
        graph = parse_theory_file(p) if p.suffix in (".yaml", ".yml") else DerivationGraph.from_json(p.read_text(encoding="utf-8"))

    res = validate_ai_proposal(proposal_data, graph)
    if as_json:
        click.echo(json.dumps(res.to_dict(), indent=2))
    else:
        if res.is_valid:
            console.print(f"[green][OK] Proposal '{res.proposal.proposal_id}' is structurally and semantically valid.[/green]")
        else:
            console.print(f"[bold red][FAIL] Proposal validation failed with {len(res.errors)} error(s):[/bold red]")
            for err in res.errors:
                console.print(f"  * [red]{err}[/red]")


@main.command()
@click.argument("theory_file", type=click.Path(exists=True))
@click.option("--proposal", "-p", default=None, type=click.Path(exists=True), help="Existing proposal JSON file")
@click.option("--request", "-r", default=None, help="Natural language derivation goal")
@click.option("--provider", default="mock", help="AI provider: mock, openai, local")
@click.option("--dry-run", is_flag=True, help="Test proposal without modifying canonical graph")
@click.option("--output", "-o", default=None, help="Output file for candidate/updated graph")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def propose(
    theory_file: str,
    proposal: Optional[str],
    request: Optional[str],
    provider: str,
    dry_run: bool,
    output: Optional[str],
    as_json: bool
):
    """Propose and verify the next derivation step using an AI provider or proposal file."""
    p_theory = Path(theory_file)
    graph = parse_theory_file(p_theory) if p_theory.suffix in (".yaml", ".yml") else DerivationGraph.from_json(p_theory.read_text(encoding="utf-8"))

    # Load or generate proposal
    if proposal:
        raw_prop = json.loads(Path(proposal).read_text(encoding="utf-8"))
    else:
        prov = get_provider(provider)
        if not prov.is_available():
            console.print(f"[bold red]Provider '{provider}' is not available or configured.[/bold red]")
            return
        ctx = build_ai_context(graph)
        req_text = request or "Propose the next derivation transformation step"
        raw_prop = prov.propose(ctx.to_dict(), req_text)

    prop_obj = DerivationProposal(**raw_prop)
    result = apply_and_verify_proposal(prop_obj, graph, dry_run=dry_run)

    if output and not dry_run:
        Path(output).write_text(graph.to_json(), encoding="utf-8")

    if as_json:
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        status_color = "green" if result.success else "red"
        mode_str = "[yellow](DRY RUN)[/yellow]" if dry_run else ""
        console.print(f"[{status_color}]Proposal '{result.proposal_id}' Evaluation: {result.status.value}[/{status_color}] {mode_str}")
        if result.success:
            console.print(f"  Candidate Edge: [bold]{result.edge_id}[/bold] verified via {result.report.get('checker')}")
        else:
            for err in result.errors:
                console.print(f"  [red]* Error: {err}[/red]")


@main.command()
@click.argument("theory_file", type=click.Path(exists=True))
@click.option("--max-steps", "-n", default=3, help="Maximum number of research iterations")
@click.option("--provider", default="mock", help="AI provider: mock, openai, local")
@click.option("--output-dir", "-o", default="research_output", help="Output directory for research trace")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def research(theory_file: str, max_steps: int, provider: str, output_dir: str, as_json: bool):
    """Run a bounded research loop proposing, validating, and verifying steps."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    p_theory = Path(theory_file)
    graph = parse_theory_file(p_theory) if p_theory.suffix in (".yaml", ".yml") else DerivationGraph.from_json(p_theory.read_text(encoding="utf-8"))

    prov = get_provider(provider)
    if not prov.is_available():
        console.print(f"[bold red]Provider '{provider}' is not available.[/bold red]")
        return

    step_results = []
    for step in range(1, max_steps + 1):
        ctx = build_ai_context(graph)
        raw_prop = prov.propose(ctx.to_dict(), f"Research step {step}: extend derivation with next logical step")
        prop_obj = DerivationProposal(**raw_prop)
        res = apply_and_verify_proposal(prop_obj, graph, dry_run=False)
        step_results.append({
            "step": step,
            "proposal_id": prop_obj.proposal_id,
            "rule": prop_obj.rule,
            "status": res.status.value,
            "success": res.success
        })
        if not res.success:
            break

    # Save final research graph
    graph_file = out_path / "research_graph.json"
    graph_file.write_text(graph.to_json(), encoding="utf-8")

    trace_file = out_path / "research_trace.json"
    trace_file.write_text(json.dumps(step_results, indent=2), encoding="utf-8")

    if as_json:
        click.echo(json.dumps({
            "total_steps": len(step_results),
            "trace": step_results,
            "graph_file": str(graph_file)
        }, indent=2))
    else:
        console.print(f"[green][OK] Bounded research loop completed {len(step_results)} step(s). Trace saved to '{out_path}'.[/green]")


@main.command()
@click.argument("graph_file", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def check(graph_file: str, as_json: bool):
    """Run symbolic and dimensional verification backends on a derivation graph."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)

    dim_checker = DimensionChecker()
    sympy_checker = SymPyChecker()
    linear_algebra_checker = LinearAlgebraChecker()
    vector_calculus_checker = VectorCalculusChecker()
    electrostatics_checker = ElectrostaticsChecker()
    results = {}

    if not as_json:
        console.print(f"[bold cyan]Running symbolic and dimensional verification on '{graph_file}'...[/bold cyan]")

    for eid, edge in graph.edges.items():
        dim_report = dim_checker.verify_edge(edge, graph)
        dim_str = "dim: ok" if dim_report.passed else f"dim: {dim_report.error_message}"

        if edge.checker == "sympy":
            report = sympy_checker.verify_edge(edge, graph)
            results[eid] = {"status": report.status.value, "passed": report.passed, "dim": dim_report.passed}
            if not as_json:
                status_color = "green" if report.passed else "red"
                console.print(f"  Edge '{eid}': [{status_color}]{report.status.value}[/{status_color}] ({dim_str})")
        elif edge.checker == "linear_algebra":
            report = linear_algebra_checker.verify_edge(edge, graph)
            results[eid] = {
                "status": report.status.value,
                "passed": report.passed,
                "dim": dim_report.passed,
                "independence": report.details.get("numpy_cross_check", {}).get("independence_class"),
            }
            if not as_json:
                status_color = "green" if report.passed else "red"
                console.print(f"  Edge '{eid}': [{status_color}]{report.status.value}[/{status_color}] ({dim_str})")
        elif edge.checker == "vector_calculus":
            report = vector_calculus_checker.verify_edge(edge, graph)
        elif edge.checker == "electrostatics":
            report = electrostatics_checker.verify_edge(edge, graph)
            results[eid] = {
                "status": report.status.value,
                "passed": report.passed,
                "dim": dim_report.passed,
                "independence": report.details.get("finite_difference_cross_check", {}).get("independence_class"),
            }
            if not as_json:
                status_color = "green" if report.passed else "red"
                console.print(f"  Edge '{eid}': [{status_color}]{report.status.value}[/{status_color}] ({dim_str})")
        else:
            results[eid] = {"status": "DELEGATED", "checker": edge.checker, "dim": dim_report.passed}
            if not as_json:
                console.print(f"  Edge '{eid}': [dim]Delegated to backend '{edge.checker}'[/dim] ({dim_str})")

    if as_json:
        click.echo(json.dumps(results, indent=2))
    else:
        print_graph_summary(graph)


@main.command()
@click.argument("graph_file", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def prove(graph_file: str, as_json: bool):
    """Execute Lean 4 formal interactive theorem prover on formal proof obligations."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)

    lean_checker = LeanChecker()
    if not lean_checker.is_available():
        if as_json:
            click.echo(json.dumps({"error": "Lean 4 compiler not detected in system PATH"}, indent=2))
        else:
            console.print("[bold red]Lean 4 compiler not found in toolchain paths.[/bold red]")
        return

    results = {}
    if not as_json:
        console.print(f"[bold cyan]Running Lean 4 theorem prover ({lean_checker.version}) on '{graph_file}'...[/bold cyan]")

    for eid, edge in graph.edges.items():
        if edge.checker == "lean4":
            report = lean_checker.verify_edge(edge, graph)
            results[eid] = {
                "status": report.status.value,
                "passed": report.passed,
                "theorem": report.details.get("theorem_name"),
                "runtime_ms": report.execution_time_ms
            }
            if not as_json:
                status_color = "green" if report.passed else "red"
                console.print(f"  Edge '{eid}': [{status_color}]{report.status.value}[/{status_color}]")

    if as_json:
        click.echo(json.dumps(results, indent=2))
    else:
        print_graph_summary(graph)


@main.command()
@click.argument("graph_file", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def simulate(graph_file: str, as_json: bool):
    """Execute numerical differential equation solver (SciPy RK45) on equations of motion."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)

    num_checker = NumericalChecker()
    results = {}
    if not as_json:
        console.print(f"[bold cyan]Running numerical ODE simulation on '{graph_file}'...[/bold cyan]")

    for eid, edge in graph.edges.items():
        if edge.checker == "numerical" or edge.transformation_rule == "numerical_simulation":
            report = num_checker.verify_edge(edge, graph)
            results[eid] = {
                "status": report.status.value,
                "passed": report.passed,
                "rmse": report.details.get("metrics", {}).get("rmse")
            }
            if not as_json:
                status_color = "green" if report.passed else "red"
                console.print(f"  Edge '{eid}': [{status_color}]{report.status.value}[/{status_color}] (RMSE: {results[eid]['rmse']})")

    if as_json:
        click.echo(json.dumps(results, indent=2))
    else:
        print_graph_summary(graph)


@main.command()
@click.argument("graph_file", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def stats(graph_file: str, as_json: bool):
    """Run non-linear empirical parameter estimation and chi-square residual diagnostics."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)

    stats_checker = StatisticalChecker()
    results = {}
    if not as_json:
        console.print(f"[bold cyan]Running statistical inference backend on '{graph_file}'...[/bold cyan]")

    for eid, edge in graph.edges.items():
        if edge.checker == "statistical" or edge.transformation_rule == "empirical_inference":
            report = stats_checker.verify_edge(edge, graph)
            gof = report.details.get("goodness_of_fit", {})
            results[eid] = {
                "status": report.status.value,
                "passed": report.passed,
                "reduced_chi2": gof.get("reduced_chi2"),
                "r_squared": gof.get("r_squared")
            }
            if not as_json:
                status_color = "green" if report.passed else "red"
                console.print(f"  Edge '{eid}': [{status_color}]{report.status.value}[/{status_color}] (Red. Chi2: {results[eid]['reduced_chi2']:.3f}, R2: {results[eid]['r_squared']:.4f})")

    if as_json:
        click.echo(json.dumps(results, indent=2))
    else:
        print_graph_summary(graph)


@main.command("query-assumptions")
@click.argument("graph_file", type=click.Path(exists=True))
@click.option("--drop", default=None, help="Assumption ID to simulate removing")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def query_assumptions(graph_file: str, drop: str, as_json: bool):
    """Inspect assumption dependencies and simulate the removal of specific assumptions."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)

    if drop:
        impact = graph.simulate_assumption_removal(drop)
        if as_json:
            click.echo(json.dumps(impact, indent=2))
        else:
            print_assumption_report(impact)
    else:
        data = {
            aid: {
                "description": asm.description,
                "predicate": asm.formal_predicate,
                "dependents": graph.query_nodes_dependent_on(aid)
            }
            for aid, asm in graph.assumptions.items()
        }
        if as_json:
            click.echo(json.dumps(data, indent=2))
        else:
            console.print(f"[bold cyan]Declared Assumptions in '{graph_file}':[/bold cyan]")
            for aid, d in data.items():
                console.print(f"  * [bold yellow]{aid}[/bold yellow]: {d['description']}")
                console.print(f"    Predicate: [cyan]{d['predicate']}[/cyan] | Dependent Nodes: {len(d['dependents'])}")


@main.command()
@click.argument("graph_file", type=click.Path(exists=True))
@click.option("--edge", "-e", required=True, help="Edge ID to expand")
def expand(graph_file: str, edge: str):
    """Expand a high-level macro transformation step into verifiable micro-steps."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)

    subgraph = graph.expand_edge_certificate(edge)
    if subgraph:
        console.print(f"[green][OK] Expanded '{edge}' into {len(subgraph.nodes)} sub-nodes and {len(subgraph.edges)} sub-steps:[/green]")
        for seid, se in subgraph.edges.items():
            console.print(f"  - [{seid}] {se.transformation_rule}: {se.justification}")
    else:
        console.print(f"[yellow]No expandable certificate steps found for edge '{edge}'.[/yellow]")


@main.command()
@click.argument("graph_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output HTML file path")
def visualize(graph_file: str, output: str):
    """Generate standalone interactive HTML visualization of the derivation graph."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)
    out_file = output or f"{Path(graph_file).stem}.html"
    generate_interactive_html(graph, out_file)
    console.print(f"[green][OK] Generated interactive HTML graph: '{out_file}'[/green]")


@main.command()
@click.argument("graph_file", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def report(graph_file: str, as_json: bool):
    """Display comprehensive verification report and status matrix."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)
    if as_json:
        click.echo(graph.to_json())
    else:
        print_graph_summary(graph)


@main.command("export-certificate")
@click.argument("graph_file", type=click.Path(exists=True))
@click.option("--output-dir", "-o", default="certificates", help="Directory to save certificate package")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def export_certificate(graph_file: str, output_dir: str, as_json: bool):
    """Export self-contained, machine-auditable verification certificate package."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)
    files = graph.export_certificate_package(output_dir)
    if as_json:
        click.echo(json.dumps(files, indent=2))
    else:
        console.print(f"[green][OK] Exported verification certificate package to '{output_dir}':[/green]")
        for fname, fpath in files.items():
            console.print(f"  * {fname} -> {fpath}")


@main.command()
@click.option("--name", "-n", default="ir", type=click.Choice(["ir", "tensor", "proposal", "context", "agent", "capability", "worker", "worker-result"]), help="Schema name")
def schema(name: str):
    """Print an authoritative machine-readable JSON schema for an interchange contract."""
    if name == "ir":
        schema_path = Path(__file__).parent.parent / "schemas" / "automate-ir-v0.1.json"
        if not schema_path.exists():
            raise click.ClickException("Canonical IR schema file is unavailable.")
        click.echo(schema_path.read_text(encoding="utf-8"))
        return

    if name == "agent":
        schema_path = Path(__file__).parent.parent / "schemas" / "automate-agent-v1.json"
        if not schema_path.exists():
            raise click.ClickException("Machine-agent contract file is unavailable.")
        click.echo(schema_path.read_text(encoding="utf-8"))
        return

    if name == "capability":
        schema_path = Path(__file__).parent.parent / "schemas" / "automate-capability-inventory-v1.json"
        if not schema_path.exists():
            raise click.ClickException("Capability inventory schema file is unavailable.")
        click.echo(schema_path.read_text(encoding="utf-8"))
        return

    if name == "worker":
        schema_path = Path(__file__).parent.parent / "schemas" / "automate-worker-v1.json"
        if not schema_path.exists():
            raise click.ClickException("Worker packet schema file is unavailable.")
        click.echo(schema_path.read_text(encoding="utf-8"))
        return

    if name == "worker-result":
        schema_path = Path(__file__).parent.parent / "schemas" / "automate-worker-result-v1.json"
        if not schema_path.exists():
            raise click.ClickException("Worker result schema file is unavailable.")
        click.echo(schema_path.read_text(encoding="utf-8"))
        return

    if name == "tensor":
        model = TensorEquation
    else:
        model = DerivationProposal if name == "proposal" else AIContext
    document = model.model_json_schema()
    document["$id"] = f"https://automate.physics/schemas/automate-{name}-v1.json"
    document["title"] = f"Automate {name.capitalize()} Contract (v1)"
    click.echo(json.dumps(document, indent=2))



@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable engine manifest")
def engine(as_json: bool):
    """Show the standalone three-repository engine contract and trust boundary."""
    manifest = {
        "schema_version": "automate.ecosystem.v1",
        "authority": "automate",
        "components": {
            "automate": {"role": "authority", "repository": "rynahmed101-sys/automate"},
            "worker": {"role": "execution", "repository": "rynahmed101-sys/chanfana-openapi-template"},
            "mirror": {"role": "laboratory", "repository": "rynahmed101-sys/the-mirror"},
        },
        "trust_ladder": [
            "proposal",
            "bounded_execution",
            "experimental_evidence",
            "independent_inspection",
            "focused_tests",
            "reconciliation",
            "merged_main",
            "exact_head_verified",
            "security_verified",
            "independently_cross_checked",
            "certified",
        ],
        "development_trunk": "engine",
        "release_surface": "main",
        "capability_frontier": "Stage 1B improper integrals and convergence-aware handling",
        "worker_activation": "gated",
    }
    if as_json:
        click.echo(json.dumps(manifest, indent=2))
    else:
        console.print("[bold cyan]Autonomous Scientific Engine[/bold cyan]")
        console.print("  Authority: Automate")
        console.print("  Execution: Chanfana worker")
        console.print("  Laboratory: THE MIRROR")
        console.print("  Development trunk: engine")
        console.print("  Release surface: main")
        console.print("  Worker activation: gated")
        console.print("  Capability frontier: Stage 1B")



main.add_command(capability)

if __name__ == "__main__":
    main()
