"""
Canonical End-to-End Physics Demonstration for Automate.
Executes the full pipeline:
L = 1/2*m*x_dot^2 - 1/2*k*x^2
-> Euler-Lagrange equation
-> m*x_ddot + k*x = 0
-> SymPy symbolic verification
-> Lean 4 formal proof verification
-> SciPy numerical simulation & energy conservation
-> SciPy statistical parameter inference
-> Assumption sensitivity analysis
-> Standalone interactive graph visualization.
"""

from pathlib import Path
import json
import time

from automate.theory.parser import parse_theory_file
from automate.backend.dimension_backend import DimensionChecker
from automate.backend.sympy_backend import SymPyChecker
from automate.backend.lean_backend import LeanChecker
from automate.backend.numerical_backend import NumericalChecker
from automate.backend.statistical_backend import StatisticalChecker
from automate.visualization.html_graph import generate_interactive_html
from automate.visualization.terminal import print_graph_summary, print_assumption_report, console
from automate.core.status import VerificationStatus


def run_harmonic_oscillator_demo(output_dir: str = "output") -> int:
    """
    Executes the canonical Automate demonstration.
    """
    console.print("\n[bold cyan]================================================================[/bold cyan]")
    console.print("[bold cyan]       AUTOMATE: FORMAL PHYSICS DERIVATION ENGINE DEMO          [/bold cyan]")
    console.print("[bold cyan]================================================================[/bold cyan]\n")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Parse Theory File
    theory_path = Path(__file__).parent.parent / "examples" / "harmonic_oscillator.yaml"
    console.print(f"[bold yellow][Step 1][/bold yellow] Parsing declarative physics theory from [underline]{theory_path.name}[/underline]...")
    graph = parse_theory_file(theory_path)
    console.print(f"  [green][OK][/green] Loaded graph '{graph.id}' with {len(graph.nodes)} nodes, {len(graph.edges)} edges, {len(graph.assumptions)} assumptions.")

    # 2. Validate DAG
    console.print("[bold yellow][Step 2][/bold yellow] Validating Directed Acyclic Graph (DAG) integrity...")
    is_dag = graph.validate_dag()
    if not is_dag:
        console.print("[bold red]  [FAIL] Error: Graph contains cycles![/bold red]")
        return 1
    top_order = graph.topological_sort()
    console.print(f"  [green][OK][/green] Valid DAG confirmed. Topological sort order: {top_order}")

    # 3. Instantiate Verification Backends
    dim_checker = DimensionChecker()
    sympy_checker = SymPyChecker()
    lean_checker = LeanChecker()
    num_checker = NumericalChecker()
    stats_checker = StatisticalChecker()

    console.print("\n[bold yellow][Step 3][/bold yellow] Initializing verification backends:")
    console.print(f"  * DimensionChecker:  [green]Active[/green] (SI base dimensions)")
    console.print(f"  * SymPyChecker:      [green]Active[/green] (SymPy {sympy_checker.version})")
    lean_avail = lean_checker.is_available()
    console.print(f"  * LeanChecker:       [{'green' if lean_avail else 'yellow'}]{'Active' if lean_avail else 'Inactive'}[/{'green' if lean_avail else 'yellow'}] ({lean_checker.version})")
    console.print(f"  * NumericalChecker:  [green]Active[/green] ({num_checker.version})")
    console.print(f"  * StatisticalChecker:[green]Active[/green] ({stats_checker.version})\n")

    # 4. Execute Verification Pipeline
    console.print("[bold yellow][Step 4][/bold yellow] Executing verification backends across derivation edges:")

    reports = {}

    for eid, edge in graph.edges.items():
        console.print(f"\n  [bold cyan]--> Verifying Edge: '{eid}'[/bold cyan] (Rule: [bold]{edge.transformation_rule}[/bold])")

        # Dimensional check
        dim_report = dim_checker.verify_edge(edge, graph)
        if dim_report.passed:
            console.print(f"    [dim]* [DimensionChecker] Passed: {dim_report.details.get('consistency', 'Homogeneous dimensions')}[/dim]")

        # Main assigned backend check
        checker_type = edge.checker
        if checker_type == "sympy":
            report = sympy_checker.verify_edge(edge, graph)
        elif checker_type == "lean4":
            report = lean_checker.verify_edge(edge, graph)
        elif checker_type == "numerical":
            report = num_checker.verify_edge(edge, graph)
        elif checker_type == "statistical":
            report = stats_checker.verify_edge(edge, graph)
        else:
            report = sympy_checker.verify_edge(edge, graph)

        reports[eid] = report.to_dict()

        status_color = "green" if report.passed else "red"
        console.print(f"    * [{status_color}]Status: {report.status.value}[/{status_color}] via {report.backend} in {report.execution_time_ms:.1f}ms")

        # Update output node status
        for out_nid in edge.output_nodes:
            out_node = graph.get_node(out_nid)
            if out_node:
                out_node.status = report.status

    # 5. Assumption Sensitivity Analysis
    console.print("\n[bold yellow][Step 5][/bold yellow] Performing First-Class Assumption Sensitivity Query:")
    asm_to_drop = "asm_pos_mass"
    console.print(f"  Query: 'What survives if assumption [{asm_to_drop}] is dropped?'")
    impact = graph.simulate_assumption_removal(asm_to_drop)
    print_assumption_report(impact)

    # 6. High-level Transformation Macro Expansion
    console.print("\n[bold yellow][Step 6][/bold yellow] Demonstrating Lossless Certificate Expansion (Compiler Analogy):")
    el_edge_id = "edge_euler_lagrange"
    subgraph = graph.expand_edge_certificate(el_edge_id)
    if subgraph:
        console.print(f"  [green][OK][/green] High-level rule '{el_edge_id}' expanded into {len(subgraph.nodes)} micro-nodes and {len(subgraph.edges)} micro-steps:")
        for se_id, se in subgraph.edges.items():
            console.print(f"    - Sub-step {se_id}: {se.transformation_rule} -> {se.justification}")
    else:
        console.print("  [dim]* No micro-steps certificate found to expand.[/dim]")

    # 7. Generate Visualizations and Reports
    console.print("\n[bold yellow][Step 7][/bold yellow] Generating Derivation Artifacts:")
    html_file = out_path / "harmonic_oscillator.html"
    generate_interactive_html(graph, html_file)
    console.print(f"  [green][OK][/green] Interactive HTML Graph: [green]{html_file.resolve()}[/green]")

    json_file = out_path / "derivation_graph.json"
    json_file.write_text(graph.to_json(), encoding="utf-8")
    console.print(f"  [green][OK][/green] Machine-Readable IR Graph: [green]{json_file.resolve()}[/green]")

    report_file = out_path / "verification_report.json"
    report_file.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    console.print(f"  [green][OK][/green] Verification Audit Report: [green]{report_file.resolve()}[/green]\n")

    # 8. Terminal Summary Table
    print_graph_summary(graph)

    console.print("\n[bold green][SUCCESS] Automate formal physics derivation demonstration completed successfully![/bold green]\n")
    return 0


if __name__ == "__main__":
    run_harmonic_oscillator_demo()
