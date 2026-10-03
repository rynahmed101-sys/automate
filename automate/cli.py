"""
Command Line Interface (CLI) for Automate.
"""

from pathlib import Path
import json
import click

from automate.theory.parser import parse_theory_file
from automate.core.graph import DerivationGraph
from automate.backend.dimension_backend import DimensionChecker
from automate.backend.sympy_backend import SymPyChecker
from automate.backend.lean_backend import LeanChecker
from automate.backend.numerical_backend import NumericalChecker
from automate.backend.statistical_backend import StatisticalChecker
from automate.visualization.html_graph import generate_interactive_html
from automate.visualization.terminal import print_graph_summary, print_assumption_report, console
from automate.demo import run_harmonic_oscillator_demo


@click.group()
@click.version_option(version="0.1.0", prog_name="automate")
def main():
    """Automate: Local-first machine-checkable formal physics derivation engine."""
    pass


@main.command()
@click.option("--output-dir", "-o", default="output", help="Directory to save generated artifacts")
def demo(output_dir: str):
    """Run the complete canonical end-to-end harmonic oscillator demonstration."""
    run_harmonic_oscillator_demo(output_dir)


@main.command()
@click.argument("theory_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output JSON graph path")
def parse(theory_file: str, output: str):
    """Parse a declarative theory YAML/JSON file into canonical IR derivation graph."""
    graph = parse_theory_file(theory_file)
    out_path = output or f"{Path(theory_file).stem}_graph.json"
    Path(out_path).write_text(graph.to_json(), encoding="utf-8")
    console.print(f"[green][OK] Parsed '{theory_file}' into '{out_path}'[/green] ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")


@main.command()
@click.argument("graph_file", type=click.Path(exists=True))
def check(graph_file: str):
    """Run symbolic and dimensional verification backends on a derivation graph."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)

    dim_checker = DimensionChecker()
    sympy_checker = SymPyChecker()

    console.print(f"[bold cyan]Running symbolic and dimensional verification on '{graph_file}'...[/bold cyan]")
    for eid, edge in graph.edges.items():
        dim_report = dim_checker.verify_edge(edge, graph)
        dim_str = "dim: ok" if dim_report.passed else f"dim: {dim_report.error_message}"

        if edge.checker == "sympy":
            report = sympy_checker.verify_edge(edge, graph)
            status_color = "green" if report.passed else "red"
            console.print(f"  Edge '{eid}': [{status_color}]{report.status.value}[/{status_color}] ({dim_str})")
        else:
            console.print(f"  Edge '{eid}': [dim]Delegated to backend '{edge.checker}'[/dim] ({dim_str})")

    print_graph_summary(graph)


@main.command()
@click.argument("graph_file", type=click.Path(exists=True))
def prove(graph_file: str):
    """Execute Lean 4 formal interactive theorem prover on formal proof obligations."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)

    lean_checker = LeanChecker()
    if not lean_checker.is_available():
        console.print("[bold red]Lean 4 compiler not found in toolchain paths.[/bold red]")
        return

    console.print(f"[bold cyan]Running Lean 4 theorem prover ({lean_checker.version}) on '{graph_file}'...[/bold cyan]")
    for eid, edge in graph.edges.items():
        if edge.checker == "lean4":
            report = lean_checker.verify_edge(edge, graph)
            status_color = "green" if report.passed else "red"
            console.print(f"  Edge '{eid}': [{status_color}]{report.status.value}[/{status_color}]")
            if report.proof_script:
                console.print(f"    Theorem: {report.details.get('theorem_name')}")

    print_graph_summary(graph)


@main.command()
@click.argument("graph_file", type=click.Path(exists=True))
def simulate(graph_file: str):
    """Execute numerical differential equation solver (SciPy RK45) on equations of motion."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)

    num_checker = NumericalChecker()
    console.print(f"[bold cyan]Running numerical ODE simulation on '{graph_file}'...[/bold cyan]")
    for eid, edge in graph.edges.items():
        if edge.checker == "numerical" or edge.transformation_rule == "numerical_simulation":
            report = num_checker.verify_edge(edge, graph)
            status_color = "green" if report.passed else "red"
            console.print(f"  Edge '{eid}': [{status_color}]{report.status.value}[/{status_color}] (RMSE: {report.details.get('metrics', {}).get('rmse', 'N/A')})")

    print_graph_summary(graph)


@main.command()
@click.argument("graph_file", type=click.Path(exists=True))
def stats(graph_file: str):
    """Run non-linear empirical parameter estimation and chi-square residual diagnostics."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)

    stats_checker = StatisticalChecker()
    console.print(f"[bold cyan]Running statistical inference backend on '{graph_file}'...[/bold cyan]")
    for eid, edge in graph.edges.items():
        if edge.checker == "statistical" or edge.transformation_rule == "empirical_inference":
            report = stats_checker.verify_edge(edge, graph)
            status_color = "green" if report.passed else "red"
            gof = report.details.get("goodness_of_fit", {})
            console.print(f"  Edge '{eid}': [{status_color}]{report.status.value}[/{status_color}] (Red. Chi2: {gof.get('reduced_chi2', 0):.3f}, R2: {gof.get('r_squared', 0):.4f})")

    print_graph_summary(graph)


@main.command("query-assumptions")
@click.argument("graph_file", type=click.Path(exists=True))
@click.option("--drop", default=None, help="Assumption ID to simulate removing")
def query_assumptions(graph_file: str, drop: str):
    """Inspect assumption dependencies and simulate the removal of specific assumptions."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)

    if drop:
        impact = graph.simulate_assumption_removal(drop)
        print_assumption_report(impact)
    else:
        console.print(f"[bold cyan]Declared Assumptions in '{graph_file}':[/bold cyan]")
        for aid, asm in graph.assumptions.items():
            dependents = graph.query_nodes_dependent_on(aid)
            console.print(f"  * [bold yellow]{aid}[/bold yellow]: {asm.description}")
            console.print(f"    Predicate: [cyan]{asm.formal_predicate}[/cyan] | Dependent Nodes: {len(dependents)}")


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
def report(graph_file: str):
    """Display comprehensive verification report and status matrix."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)
    print_graph_summary(graph)


@main.command("export-certificate")
@click.argument("graph_file", type=click.Path(exists=True))
@click.option("--output-dir", "-o", default="certificates", help="Directory to save certificate package")
def export_certificate(graph_file: str, output_dir: str):
    """Export self-contained, machine-auditable verification certificate package."""
    content = Path(graph_file).read_text(encoding="utf-8")
    graph = DerivationGraph.from_json(content)
    files = graph.export_certificate_package(output_dir)
    console.print(f"[green][OK] Exported verification certificate package to '{output_dir}':[/green]")
    for fname, fpath in files.items():
        console.print(f"  * {fname} -> {fpath}")


if __name__ == "__main__":
    main()
