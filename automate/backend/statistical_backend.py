"""
StatisticalChecker: Empirical validation and statistical inference backend using SciPy.

Performs parametric model fitting against observed or synthetic data.
The model function is determined by the graph's node expressions and edge parameters,
NOT hardcoded to a cosine/harmonic oscillator model.

Supported model types (via edge.parameters['model']):
  - 'cosine'          : A * cos(omega * t + phi)
  - 'exponential_decay': A * exp(-lambda * t)
  - 'power_law'       : A * t^n
  - 'damped_oscillator': A * exp(-gamma * t) * cos(omega * t + phi)
  - 'linear'          : a * t + b
  - 'expression'      : arbitrary SymPy expression string (from node or params)

If no model is specified and the rule is not 'empirical_inference',
returns NOT_APPLICABLE rather than silently fitting a cosine.
"""

import hashlib
import time
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import sympy as sp
import scipy
from scipy.optimize import curve_fit
from scipy import stats

from automate.backend.base import BaseChecker, VerificationReport
from automate.core.status import VerificationStatus
from automate.core.edge import DerivationEdge, DerivationCertificate
from automate.core.graph import DerivationGraph


class StatisticalChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "StatisticalChecker"

    @property
    def version(self) -> str:
        return f"SciPy {scipy.__version__}"

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

        rule = edge.transformation_rule
        passed = False
        error_msg = None
        details: Dict[str, Any] = {"rule": rule}
        certificates: List[Dict[str, Any]] = []

        if rule != "empirical_inference":
            status = VerificationStatus.NOT_APPLICABLE
            details["reason"] = (
                f"Rule '{rule}' is not an empirical inference rule. "
                "StatisticalChecker only applies to 'empirical_inference'."
            )
            elapsed = (time.perf_counter() - start_time) * 1000
            return self._build_report(status, False, details, [], None, edge, graph, elapsed)

        try:
            passed, details, certificates, error_msg = self._fit_parametric_model(
                in_nodes[0], out_nodes[0], edge.parameters
            )
        except Exception as e:
            passed = False
            error_msg = f"Statistical estimation error: {type(e).__name__}: {str(e)}"

        elapsed = (time.perf_counter() - start_time) * 1000
        status = VerificationStatus.STATISTICALLY_CHECKED if passed else VerificationStatus.FAILED
        return self._build_report(status, passed, details, certificates, error_msg, edge, graph, elapsed)

    def _build_report(
        self, status, passed, details, certificates, error_msg, edge, graph, elapsed
    ) -> VerificationReport:
        rule = edge.transformation_rule
        if passed:
            edge.status = status
            edge.checker = "statistical"
            edge.certificate = DerivationCertificate(
                rule_name=rule,
                steps=certificates,
                backend_version=self.version,
                execution_time_ms=elapsed,
                metrics=details.get("goodness_of_fit", {})
            )
        else:
            edge.status = status
            edge.checker = "statistical"
            if error_msg:
                edge.failed_reason = error_msg

        from automate.backend.base import VerificationEvidence
        evidence = VerificationEvidence(
            backend=self.name,
            backend_version=self.version,
            input_node_ids=edge.input_nodes,
            output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,
            generated_obligations=edge.verification_obligations or [{"type": "parameter_fit", "model": "non_linear_least_squares"}],
            command_invocation="curve_fit(model_func, t_data, x_obs)",
            passed=passed,
            status=status,
            execution_time_ms=elapsed,
            reproducibility={"library": "scipy.optimize", "version": self.version},
            metrics=details.get("goodness_of_fit", {})
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
            certificates=certificates,
            evidence=evidence
        )

    # ------------------------------------------------------------------
    # Core fitting method: reads model from parameters, NOT hardcoded.
    # ------------------------------------------------------------------
    def _fit_parametric_model(
        self,
        in_node: Any,
        out_node: Any,
        params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """
        Fits a parametric model to data.

        The model is determined by params['model']:
          'cosine'            → A * cos(omega * t + phi)
          'exponential_decay' → A * exp(-lam * t)
          'power_law'         → A * t**n
          'damped_oscillator' → A * exp(-gamma * t) * cos(omega * t + phi)
          'linear'            → a * t + b
          'expression'        → arbitrary expression from params or in_node

        Data may come from:
          - params['t_data'] + params['x_obs'] (explicit arrays)
          - otherwise generates synthetic data based on model + true parameter values

        Returns goodness-of-fit metrics without fabricating verification.
        """
        model_type = params.get("model", "")
        if not model_type:
            # Try to infer from node expression
            expr_str = in_node.expression.raw_str.strip()
            if expr_str:
                model_type = "expression"
            else:
                return (
                    False, {}, [],
                    "UNSUPPORTED: edge.parameters['model'] is required for empirical_inference. "
                    "No default model is applied."
                )

        model_func, param_names, p0, true_params = self._build_model(model_type, params, in_node)
        if model_func is None:
            return False, {}, [], f"Cannot build model function for model type '{model_type}'"

        # Empirical inference must consume an explicit external data payload.
        # Synthetic data remains available to lower-level benchmark callers, but it
        # is never silently promoted to observational evidence.
        if "t_data" not in params or "x_obs" not in params:
            return (
                False,
                {},
                [],
                "UNSUPPORTED: empirical_inference requires explicit t_data and x_obs. "
                "Synthetic data generation is not observational evidence.",
            )

        data_source = params.get("data_source")
        if data_source != "observed":
            return (
                False,
                {"data_source": data_source},
                [],
                "UNSUPPORTED: empirical_inference requires data_source='observed'. "
                "Synthetic or unspecified data cannot receive STATISTICALLY_CHECKED status.",
            )

        t_data, x_obs, noise_std = self._load_data(params, model_type, model_func, true_params)
        if len(t_data) != len(x_obs) or len(t_data) < max(3, len(param_names) + 1):
            return (
                False,
                {},
                [],
                "Invalid observational data: t_data and x_obs must have equal length "
                "and contain more samples than fitted parameters.",
            )
        if not (np.all(np.isfinite(t_data)) and np.all(np.isfinite(x_obs))):
            return False, {}, [], "Invalid observational data: non-finite values found."
        if np.any(np.diff(t_data) <= 0):
            return False, {}, [], "Invalid observational data: t_data must be strictly increasing."
        if not np.isfinite(noise_std) or noise_std < 0:
            return False, {}, [], "Invalid observational data: noise_std must be finite and non-negative."

        sigma = np.full_like(x_obs, noise_std) if noise_std > 0 else None

        data_hash = hashlib.sha256(
            np.ascontiguousarray(t_data, dtype=np.float64).tobytes()
            + np.ascontiguousarray(x_obs, dtype=np.float64).tobytes()
            + str(float(noise_std)).encode("utf-8")
        ).hexdigest()

        try:
            fit_kwargs = {"p0": p0}
            if sigma is not None:
                fit_kwargs["sigma"] = sigma
                fit_kwargs["absolute_sigma"] = True

            popt, pcov = curve_fit(model_func, t_data, x_obs, **fit_kwargs)
        except Exception as e:
            return False, {}, [], f"curve_fit failed: {type(e).__name__}: {str(e)}"

        perr = np.sqrt(np.diag(pcov))

        # 95% confidence intervals use the Student-t critical value with the
        # actual residual degrees of freedom, not a fixed normal 1.96 shortcut.
        if dof > 0 and np.all(np.isfinite(perr)):
            t_critical = float(stats.t.ppf(0.975, dof))
        else:
            t_critical = float("nan")

        ci_95 = {
            name: (
                [float(popt[i] - t_critical * perr[i]), float(popt[i] + t_critical * perr[i])]
                if np.isfinite(t_critical) and np.isfinite(perr[i])
                else [float("nan"), float("nan")]
            )
            for i, name in enumerate(param_names)
        }

        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((x_obs - np.mean(x_obs)) ** 2))
        r_squared = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

        if sigma is not None and np.all(sigma > 0) and dof > 0:
            chi2 = float(np.sum((residuals / sigma) ** 2))
            reduced_chi2 = float(chi2 / dof)
            chi2_mode = "known_observation_sigma"
            passed = (0.3 <= reduced_chi2 <= 3.0) and (r_squared > 0.85)
        else:
            chi2 = None
            reduced_chi2 = None
            chi2_mode = "unavailable_without_positive_observation_sigma"
            # Without a known observation uncertainty, a reduced chi-squared
            # threshold would be numerically arbitrary and is therefore not used.
            passed = r_squared > 0.85

        residual_mean = float(np.mean(residuals))
        residual_std = float(np.std(residuals))
        centered = residuals - residual_mean
        if len(centered) > 2 and np.std(centered) > 0:
            lag1 = float(np.corrcoef(centered[:-1], centered[1:])[0, 1])
        else:
            lag1 = float("nan")

        if len(residuals) >= 8 and np.all(np.isfinite(residuals)):
            normality_p = float(stats.normaltest(residuals).pvalue)
        else:
            normality_p = None

        goodness_of_fit = {
            "chi2": chi2,
            "reduced_chi2": reduced_chi2,
            "chi2_mode": chi2_mode,
            "degrees_of_freedom": dof,
            "r_squared": r_squared,
            "sum_squared_residuals": ss_res,
            "residual_mean": residual_mean,
            "residual_std": residual_std,
            "residual_lag1_autocorrelation": lag1,
            "residual_normality_p_value": normality_p,
            "confidence_level": 0.95,
            "confidence_critical_value": t_critical,
        }

        estimates = {
            name: {
                "estimate": float(popt[i]),
                "std_err": float(perr[i]),
                "ci_95": ci_95[name],
                **({"true_value": float(true_params[i])} if i < len(true_params) else {})
            }
            for i, name in enumerate(param_names)
        }

        details = {
            "model": model_type,
            "parameter_estimates": estimates,
            "goodness_of_fit": goodness_of_fit,
            "sample_size": n_points,
            "noise_std_used": float(noise_std),
            "data_source": data_source,
            "data_provenance": {
                "source_type": "observed",
                "data_id": str(params.get("data_id", "unidentified_observed_dataset")),
                "sha256": data_hash,
                "n_points": n_points,
            },
        }

        certificates = [
            {
                "step": "non_linear_least_squares_fit",
                "description": f"Fit model '{model_type}' on {n_points} data points",
                "result": f"Parameters: {dict(zip(param_names, [f'{v:.4f}' for v in popt]))}"
            },
            {
                "step": "residual_goodness_of_fit",
                "description": "Computed reduced chi-squared and R^2",
                "result": f"Reduced Chi^2 = {reduced_chi2:.3f}, R^2 = {r_squared:.4f}"
            }
        ]

        if passed:
            error_msg = None
        elif reduced_chi2 is not None:
            error_msg = (
                "Statistical fit criteria not satisfied: "
                f"reduced_chi2={reduced_chi2:.3f} (need [0.3, 3.0]), "
                f"R2={r_squared:.4f} (need > 0.85)"
            )
        else:
            error_msg = (
                "Statistical fit criteria not satisfied: observational uncertainty "
                f"was not supplied, so only R2={r_squared:.4f} (need > 0.85) was evaluated."
            )
        return passed, details, certificates, error_msg

    def _build_model(
        self, model_type: str, params: Dict[str, Any], in_node: Any
    ):
        """Returns (model_func, param_names, p0_guesses, true_param_values)."""
        import numpy as np

        if model_type == "cosine":
            A_true = float(params.get("A", 1.0))
            omega_true = float(params.get("omega", 2.0))
            phi_true = float(params.get("phi", 0.0))

            def model_func(t, A, omega, phi):
                return A * np.cos(omega * t + phi)

            return model_func, ["A", "omega", "phi"], [1.2, 1.8, 0.1], [A_true, omega_true, phi_true]

        elif model_type == "exponential_decay":
            A_true = float(params.get("A", 1.0))
            lam_true = float(params.get("lambda", 0.5))

            def model_func(t, A, lam):
                return A * np.exp(-lam * t)

            return model_func, ["A", "lambda"], [1.2, 0.4], [A_true, lam_true]

        elif model_type == "power_law":
            A_true = float(params.get("A", 1.0))
            n_true = float(params.get("n", 2.0))

            def model_func(t, A, n):
                return A * np.abs(t) ** n

            return model_func, ["A", "n"], [0.9, 1.8], [A_true, n_true]

        elif model_type == "damped_oscillator":
            A_true = float(params.get("A", 1.0))
            gamma_true = float(params.get("gamma", 0.1))
            omega_true = float(params.get("omega", 2.0))
            phi_true = float(params.get("phi", 0.0))

            def model_func(t, A, gamma, omega, phi):
                return A * np.exp(-gamma * t) * np.cos(omega * t + phi)

            return model_func, ["A", "gamma", "omega", "phi"], [1.1, 0.05, 1.8, 0.1], \
                [A_true, gamma_true, omega_true, phi_true]

        elif model_type == "linear":
            a_true = float(params.get("a", 1.0))
            b_true = float(params.get("b", 0.0))

            def model_func(t, a, b):
                return a * t + b

            return model_func, ["a", "b"], [0.9, 0.1], [a_true, b_true]

        elif model_type == "expression":
            # Build model function from expression string
            expr_str = params.get("expression_str") or in_node.expression.raw_str
            model_params = params.get("model_parameters", [])  # list of param names to fit
            if not model_params:
                return None, [], [], []

            t_sym = sp.Symbol("t", real=True)
            fit_syms = [sp.Symbol(p, real=True) for p in model_params]
            local_syms = {"t": t_sym, **{p: s for p, s in zip(model_params, fit_syms)}}

            try:
                from automate.ir.safe_parser import SafeParser, SafeParseError
                expr = SafeParser(extra_symbols=local_syms).parse(expr_str)
                func = sp.lambdify([t_sym] + fit_syms, expr, modules="numpy")
            except Exception as e:
                return None, [], [], []

            true_vals = [float(params.get(p, 1.0)) for p in model_params]
            p0 = [v * 1.1 + 0.1 for v in true_vals]  # perturbed initial guess
            return func, model_params, p0, true_vals

        else:
            return None, [], [], []

    def _load_data(
        self, params: Dict[str, Any], model_type: str, model_func, true_params: list
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """Returns (t_data, x_obs, noise_std)."""
        if "t_data" in params and "x_obs" in params:
            t_data = np.array(params["t_data"], dtype=float)
            x_obs = np.array(params["x_obs"], dtype=float)
            noise_std = float(params.get("noise_std", 0.0))
            return t_data, x_obs, noise_std

        # Synthetic data with explicit labeling
        n_points = int(params.get("n_points", 50))
        t_max = float(params.get("t_max", 10.0))
        noise_std = float(params.get("noise_std", 0.05))
        t_data = np.linspace(0, t_max, n_points)

        np.random.seed(int(params.get("random_seed", 42)))
        x_pure = model_func(t_data, *true_params)
        x_obs = x_pure + np.random.normal(0, noise_std, size=n_points)
        return t_data, x_obs, noise_std

