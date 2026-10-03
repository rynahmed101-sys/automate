"""
Terminal visualizer and report renderer using Rich.
"""

from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

from automate.core.graph import DerivationGraph
from automate.core.status import VerificationStatus


console = Console()

STATUS_STYLES = {
    VerificationStatus.FORMALLY_PROVED: "bold green",
    VerificationStatus.SYMBOLIC_CHECKED: "bold blue",
    VerificationStatus.NUMERICALLY_CHECKED: "bold cyan",
    VerificationStatus.STATISTICALLY_CHECKED: "bold magenta",
    VerificationStatus.CONDITIONAL: "bold yellow",
    VerificationStatus.PARSED: "white",
    VerificationStatus.UNVERIFIED: "dim white",
    VerificationStatus.FAILED: "bold red",
}


def print_graph_summary(graph: DerivationGraph) -> None:
    console.print(Panel(
        f"[bold white]{graph.name}[/bold white]\n[dim]{graph.description or 'Formal Physics Derivation Engine'}[/dim]\n"
        f"Nodes: [cyan]{len(graph.nodes)}[/cyan] | Edges: [cyan]{len(graph.edges)}[/cyan] | Assumptions: [cyan]{len(graph.assumptions)}[/cyan]",
        title="Automate Derivation Summary",
        border_style="blue"
    ))

    # Verification table
    table = Table(title="Derivation Transformations & Verification Matrix", border_style="dim")
    table.add_column("Edge ID", style="cyan")
    table.add_column("Rule", style="bold white")
    table.add_column("Inputs -> Outputs", style="dim")
    table.add_column("Backend", style="yellow")
    table.add_column("Status", style="bold")
    table.add_column("Runtime", justify="right", style="green")

    for eid, edge in graph.edges.items():
        style = STATUS_STYLES.get(edge.status, "white")
        flow = f"{', '.join(edge.input_nodes)} -> {', '.join(edge.output_nodes)}"
        runtime = f"{edge.certificate.execution_time_ms:.1f} ms" if edge.certificate else "-"
        table.add_row(
            eid,
            edge.transformation_rule,
            flow,
            edge.checker,
            f"[{style}]{edge.status.value}[/{style}]",
            runtime
        )

    console.print(table)


def print_assumption_report(impact: Dict[str, Any]) -> None:
    dropped = impact["dropped_assumption"]
    surviving = impact["surviving_nodes"]
    invalidated = impact["invalidated_nodes"]
    ratio = impact["survival_ratio"] * 100

    table = Table(title=f"Assumption Removal Impact: '{dropped}'", border_style="yellow")
    table.add_column("Metric", style="bold white")
    table.add_column("Value", style="cyan")

    table.add_row("Dropped Assumption", dropped)
    table.add_row("Total Graph Nodes", str(impact["total_nodes"]))
    table.add_row("Surviving Nodes", f"{len(surviving)} ({ratio:.1f}%)")
    table.add_row("Invalidated / Conditional Nodes", str(len(invalidated)))
    table.add_row("Invalidated Nodes List", ", ".join(invalidated) if invalidated else "None")

    console.print(table)
