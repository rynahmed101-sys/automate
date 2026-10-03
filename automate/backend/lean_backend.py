"""
LeanChecker: Formal theorem proving backend using Lean 4.
Generates Lean 4 proof obligations from the IR, compiles them using the Lean 4 compiler,
captures proof status, compiler diagnostics, toolchain version, and cryptographic certificates.
Never pretends an unproved or failed claim is proved.
"""

import os
import shutil
import subprocess
import time
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from automate.backend.base import BaseChecker, VerificationReport
import sympy as sp
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.core.graph import DerivationGraph


class LeanChecker(BaseChecker):
    def __init__(self, lean_path: Optional[str] = None):
        self._lean_path = lean_path or self._discover_lean_path()
        self._version = self._detect_version()

    @property
    def name(self) -> str:
        return "LeanChecker"

    @property
    def version(self) -> str:
        return self._version

    def is_available(self) -> bool:
        return bool(self._lean_path and os.path.exists(self._lean_path))

    def _discover_lean_path(self) -> Optional[str]:
        # 1. Direct environment variable overrides
        for env_var in ("LEAN_BIN", "LEAN_PATH"):
            val = os.environ.get(env_var)
            if val and os.path.exists(val):
                return val

        # 2. ELAN_HOME environment variable
        elan_home = os.environ.get("ELAN_HOME")
        if elan_home:
            exe_name = "lean.exe" if os.name == "nt" else "lean"
            candidate = Path(elan_home) / "bin" / exe_name
            if candidate.exists():
                return str(candidate)

        # 3. System PATH lookup
        lean_in_path = shutil.which("lean.exe" if os.name == "nt" else "lean") or shutil.which("lean")
        if lean_in_path and os.path.exists(lean_in_path):
            return lean_in_path

        # 4. Standard platform user home location (~/.elan/bin)
        exe_name = "lean.exe" if os.name == "nt" else "lean"
        user_elan = Path.home() / ".elan" / "bin" / exe_name
        if user_elan.exists():
            return str(user_elan)

        # 5. Known installation prefixes (only checked if present on system)
        system_candidates = [
            Path("/usr/local/bin/lean"),
            Path("/opt/homebrew/bin/lean"),
            Path("F:/elan/bin/lean.exe"),
            Path("C:/elan/bin/lean.exe")
        ]
        for c in system_candidates:
            if c.exists():
                return str(c)

        return None

    def _get_execution_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        if self._lean_path:
            p = Path(self._lean_path)
            # Keep Elan available when the checker launches Lean from a sandbox.
            if p.parent.name.lower() == "bin" and p.parent.parent.name.lower().endswith("elan"):
                env.setdefault("ELAN_HOME", str(p.parent.parent))
                elan_bin = str(p.parent)
                path_entries = env.get("PATH", "").split(os.pathsep)
                if elan_bin not in path_entries:
                    env["PATH"] = elan_bin + os.pathsep + env.get("PATH", "")
        return env

    def _find_lean_toolchain_file(self) -> Optional[Path]:
        """Find the repository's Elan toolchain declaration from the current working tree."""
        current = Path.cwd().resolve()
        for directory in (current, *current.parents):
            candidate = directory / "lean-toolchain"
            if candidate.is_file():
                return candidate
        return None

    def _detect_version(self) -> str:
        if not self._lean_path:
            return "Not Installed"
        try:
            env = self._get_execution_env()
            res = subprocess.run(
                [self._lean_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            if res.returncode == 0:
                return res.stdout.strip()
            return "Unknown"
        except Exception:
            return "Unavailable"

    def verify_edge(self, edge: DerivationEdge, graph: DerivationGraph) -> VerificationReport:
        start_time = time.perf_counter()

        in_nodes = [graph.get_node(nid) for nid in edge.input_nodes]
        out_nodes = [graph.get_node(nid) for nid in edge.output_nodes]

        if not all(in_nodes) or not all(out_nodes):
            return VerificationReport(
                status=VerificationStatus.FAILED,
                backend=self.name,
                backend_version=self.version,
                passed=False,
                error_message="Referenced nodes missing from derivation graph."
            )

        if not self.is_available():
            # Toolchain not found
            return VerificationReport(
                status=VerificationStatus.UNVERIFIED,
                backend=self.name,
                backend_version="None",
                passed=False,
                error_message="Lean 4 compiler not detected in system. Run INSTALL.md instructions."
            )

        # Check side conditions against active assumptions
        active_asms = {aid for aid, a in graph.assumptions.items() if a.active}
        cond_status = None
        if edge.side_conditions:
            valid_conds, missing_conds = edge.validate_side_conditions(active_asms)
            if not valid_conds:
                cond_status = VerificationStatus.CONDITIONAL
                error_msg = f"Missing or inactive required side condition(s): {', '.join(missing_conds)}"

        if cond_status == VerificationStatus.CONDITIONAL:
            passed = False
            status = VerificationStatus.CONDITIONAL
            lean_code = ""
            theorem_name = "unverified"
            returncode = -1
            code_hash = ""
            stdout = ""
            stderr = error_msg or ""
        else:
            # Bind the formal proof obligation to the actual graph mathematics first.
            # Lean proves the resulting obligation independently; it must not be allowed
            # to certify a fixed theorem while ignoring a malformed graph node.
            if edge.transformation_rule in {"euler_lagrange", "conserve_energy"}:
                from automate.backend.sympy_backend import SymPyChecker

                semantic_checker = SymPyChecker()
                if edge.transformation_rule == "euler_lagrange":
                    semantic_ok, semantic_details, _, semantic_error = semantic_checker._verify_euler_lagrange(
                        in_nodes[0], out_nodes[0], edge.parameters
                    )
                else:
                    semantic_ok, semantic_details, _, semantic_error = semantic_checker._verify_energy_conservation(
                        in_nodes, out_nodes[0], edge.parameters
                    )

                # The Lean generator currently contains canonical harmonic-oscillator
                # theorems. Do not certify a different physical system merely because
                # the generic semantic preflight happened to succeed.
                local = semantic_checker._build_context(edge.parameters)
                formal_scope_supported = (
                    str(edge.parameters.get("coordinate", "x")) == "x"
                    and str(edge.parameters.get("time_variable", "t")) == "t"
                )
                if not formal_scope_supported:
                    semantic_ok = False
                    semantic_error = (
                        "Lean formal scope currently requires coordinate='x' and "
                        "time_variable='t'."
                    )
                elif edge.transformation_rule == "euler_lagrange":
                    lagr = semantic_checker._parse_expression(
                        in_nodes[0].expression.raw_str, local
                    )
                    canonical = (
                        sp.Rational(1, 2) * local["m"] * local["x_dot"]**2
                        - sp.Rational(1, 2) * local["k"] * local["x"]**2
                    )
                    if sp.simplify(lagr - canonical) != 0:
                        semantic_ok = False
                        semantic_error = (
                            "Lean formal scope is currently limited to the canonical "
                            "1D harmonic-oscillator Lagrangian."
                        )
                elif edge.transformation_rule == "conserve_energy":
                    energy_text = out_nodes[0].expression.raw_str.split("=", 1)[0].strip()
                    energy = semantic_checker._parse_expression(energy_text, local)
                    canonical_energy = (
                        sp.Rational(1, 2) * local["m"] * local["x_dot"]**2
                        + sp.Rational(1, 2) * local["k"] * local["x"]**2
                    )
                    if sp.simplify(energy - canonical_energy) != 0:
                        semantic_ok = False
                        semantic_error = (
                            "Lean formal scope is currently limited to canonical "
                            "harmonic-oscillator mechanical energy."
                        )

                if not semantic_ok:
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return VerificationReport(
                        status=VerificationStatus.FAILED,
                        backend=self.name,
                        backend_version=self.version,
                        execution_time_ms=elapsed,
                        passed=False,
                        details={"semantic_preflight": semantic_details},
                        error_message=(
                            "Formal proof rejected because graph semantic preflight failed: "
                            + (semantic_error or "unknown semantic mismatch")
                        ),
                    )

            # Generate Lean 4 proof obligation
            lean_code, theorem_name = self._generate_lean_obligation(edge, in_nodes, out_nodes)

            # Run Lean 4 compiler in sandboxed directory
            passed, stdout, stderr, returncode = self._run_lean(lean_code)
            code_hash = hashlib.sha256(lean_code.encode("utf-8")).hexdigest()

        elapsed = (time.perf_counter() - start_time) * 1000
                    return VerificationReport(
                        status=VerificationStatus.FAILED,
                        backend=self.name,
                        backend_version=self.version,
                        execution_time_ms=elapsed,
                        passed=False,
                        details={"semantic_preflight": semantic_details},
                        error_message=(
                            "Formal proof rejected because graph semantic preflight failed: "
                            + (semantic_error or "unknown semantic mismatch")
                        ),
                    )
                
            # Generate Lean 4 proof obligation
                lean_code, theorem_name = self._generate_lean_obligation(edge, in_nodes, out_nodes)
                
                # Run Lean 4 compiler in sandboxed directory
                passed, stdout, stderr, returncode = self._run_lean(lean_code)
                code_hash = hashlib.sha256(lean_code.encode("utf-8")).hexdigest()
                
        elapsed = (time.perf_counter() - start_time) * 1000
            
        details = {
            "theorem_name": theorem_name,
            "lean_version": self.version,
            "returncode": returncode,
            "code_hash_sha256": code_hash,
            "compiler_stdout": stdout,
            "compiler_stderr": stderr
        }

        if passed:
            status = VerificationStatus.FORMALLY_PROVED
            edge.status = status
            edge.checker = "lean4"
            edge.certificate = DerivationCertificate(
                rule_name=edge.transformation_rule,
                proof_code=lean_code,
                backend_version=f"Lean {self.version}",
                execution_time_ms=elapsed,
                metrics={"formal_proof_hash": code_hash},
                diagnostics=[line for line in stdout.splitlines() if line.strip()]
            )
            error_msg = None
        elif cond_status == VerificationStatus.CONDITIONAL:
            status = VerificationStatus.CONDITIONAL
            edge.status = status
            edge.failed_reason = error_msg
        else:
            status = VerificationStatus.FAILED
            edge.status = status
            edge.checker = "lean4"
            error_msg = f"Lean 4 formal verification failed with exit code {returncode}:\n{stderr}\n{stdout}"
            edge.failed_reason = error_msg

        from automate.backend.base import VerificationEvidence
        evidence = VerificationEvidence(
            backend=self.name,
            backend_version=self.version,
            graph_id=graph.id,
            edge_id=edge.id,
            input_node_ids=edge.input_nodes,
            output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,
            generated_obligations=edge.verification_obligations or [{"theorem": theorem_name, "obligation": "Lean 4 Type Checking"}],
            command_invocation=f"lean {theorem_name}.lean",
            passed=passed,
            status=status,
            execution_time_ms=elapsed,
            reproducibility={
                "compiler": "lean",
                "version": self.version,
                "source_hash": code_hash,
                "obligation_id": theorem_name,
                "generated_lean_source": lean_code
            },
            metrics={"type_checked": passed, "source_hash": code_hash}
        )
        edge.evidence = evidence.to_dict()

        return VerificationReport(
            status=status,
            backend=self.name,
            backend_version=self.version,
            execution_time_ms=elapsed,
            passed=passed,
            details=details,
            error_message=error_msg,
            proof_script=lean_code if lean_code else None,
            evidence=evidence
        )

    def _generate_lean_obligation(
        self, edge: DerivationEdge, in_nodes: List[Any], out_nodes: List[Any]
    ) -> Tuple[str, str]:
        """
        Synthesizes a formally checkable Lean 4 theorem.
        """
        rule = edge.transformation_rule

        if rule == "conserve_energy":
            theorem_name = "harmonic_oscillator_energy_derivative_vanishes"
            code = f"""-- Automate Machine-Generated Lean 4 Proof Obligation
-- Derivation Edge ID: {edge.id}
-- Rule: {rule}
-- Justification: {edge.justification}

import Init

namespace Automate.ClassicalMechanics

/--
Theorem: In a 1D harmonic oscillator with mass `m` and spring constant `k`,
along any trajectory satisfying the equation of motion `m * a + k * x = 0`,
the time derivative of the total mechanical energy `v * (m * a + k * x)` identically vanishes.
-/
theorem {theorem_name}
    (m k x v a : Int)
    (h_eom : m * a + k * x = 0) :
    v * (m * a + k * x) = 0 := by
  simpa [h_eom]

end Automate.ClassicalMechanics
"""
            return code, theorem_name

        elif rule == "euler_lagrange":
            theorem_name = "euler_lagrange_quadratic_action_identity"
            code = f"""-- Automate Machine-Generated Lean 4 Proof Obligation
-- Derivation Edge ID: {edge.id}
-- Rule: {rule}
-- Justification: {edge.justification}

import Init

namespace Automate.LagrangianMechanics

/--
Theorem: For a quadratic Lagrangian L(x, v) = (1/2)*m*v^2 - (1/2)*k*x^2,
the Euler-Lagrange subtraction term `p_dot - F` equates directly to the harmonic equation of motion `m*a - (-k*x) = m*a + k*x`.
-/
theorem {theorem_name}
    (m k x a p_dot F : Int)
    (h_momentum : p_dot = m * a)
    (h_force : F = - (k * x)) :
    p_dot - F = m * a + k * x := by
  rw [h_momentum, h_force]
  simp [Int.sub_eq_add_neg]

end Automate.LagrangianMechanics
"""
            return code, theorem_name

        else:
            raise ValueError(
                f"LeanChecker has no formal implementation for rule: {rule}"
            )

    def _run_lean(self, code: str) -> Tuple[bool, str, str, int]:
        """
        Executes lean on a temporary file.
        """
        temp_dir = tempfile.mkdtemp(prefix="automate_lean_")
        temp_file = Path(temp_dir) / "ProofObligation.lean"
        try:
            temp_file.write_text(code, encoding="utf-8")
            # Elan's lean shim selects the toolchain from lean-toolchain files
            # relative to the working directory. Copy the project's declaration
            # into the sandbox so the isolated compiler invocation resolves the
            # exact same toolchain as the calling repository.
            toolchain_file = self._find_lean_toolchain_file()
            if toolchain_file is not None:
                shutil.copy2(toolchain_file, Path(temp_dir) / "lean-toolchain")

            env = self._get_execution_env()

            proc = subprocess.run(
                [self._lean_path, str(temp_file)],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
                cwd=temp_dir
            )
            passed = (proc.returncode == 0) and ("error:" not in proc.stderr.lower())
            return passed, proc.stdout, proc.stderr, proc.returncode
        except Exception as e:
            return False, "", str(e), -1
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
