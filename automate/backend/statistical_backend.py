"""
StatisticalChecker: Empirical validation and statistical inference backend using SciPy.
Performs non-linear parameter estimation, uncertainty quantification, confidence intervals,
residual diagnostics, and goodness-of-fit without confusing empirical evidence with formal proof.
"""

import time
from typing import Dict, Any, List, Optional
import numpy as np
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

        passed = False
        error_msg = None
        details: Dict[str, Any] = {"rule": edge.transformation_rule}
        certificates: List[Dict[str, Any]] = []

        try:
            passed, details, certificates, error_msg = self._fit_harmonic_data(edge.parameters)
        except Exception as e:
            passed = False
            error_msg = f"Statistical estimation error: {type(e).__name__}: {str(e)}"

        elapsed = (time.perf_counter() - start_time) * 1000

        if passed:
            status = VerificationStatus.STATISTICALLY_CHECKED
            edge.status = status
            edge.checker = "statistical"
            edge.certificate = DerivationCertificate(
                rule_name=edge.transformation_rule,
                steps=certificates,
                backend_version=self.version,
                execution_time_ms=elapsed,
                metrics=details.get("goodness_of_fit", {})
            )
        else:
            status = VerificationStatus.FAILED
            edge.status = status
            edge.checker = "statistical"
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
            command_invocation=f"curve_fit(model_func, t_data, x_obs)",
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

    def _fit_harmonic_data(
        self, params: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
        """
        Fit the harmonic model to supplied observations or to a deterministic
        synthetic benchmark when no observations are supplied.
        """
        m_true = float(params.get("m", 1.0))
        k_true = float(params.get("k", 4.0))
        if m_true <= 0 or k_true <= 0:
            return False, {}, [], "Statistical benchmark requires m > 0 and k > 0."

        omega_true = np.sqrt(k_true / m_true)
        A_true = float(params.get("A", 1.0))
        phi_true = float(params.get("phi", 0.0))
        seed = int(params.get("seed", 42))
        noise_std = float(params.get("noise_std", 0.05))

        provided_t = params.get("t_data")
        provided_x = params.get("x_data")
        provided_sigma = params.get("sigma_data")

        if provided_t is not None or provided_x is not None:
            if provided_t is None or provided_x is None:
                return False, {}, [], "Both t_data and x_data must be supplied together."
            t_data = np.asarray(provided_t, dtype=float)
            x_obs = np.asarray(provided_x, dtype=float)
            data_source = "observed"
            if t_data.ndim != 1 or x_obs.ndim != 1 or len(t_data) != len(x_obs):
                return False, {}, [], "t_data and x_data must be one-dimensional arrays of equal length."
            if len(t_data) < 4:
                return False, {}, [], "At least four observations are required for three fitted parameters."
            if not (np.all(np.isfinite(t_data)) and np.all(np.isfinite(x_obs))):
                return False, {}, [], "Observed data must contain only finite values."

            if provided_sigma is None:
                if noise_std <= 0:
                    return False, {}, [], "noise_std must be positive when sigma_data is not supplied."
                sigma = np.full_like(x_obs, noise_std, dtype=float)
            else:
                sigma = np.asarray(provided_sigma, dtype=float)
                if sigma.ndim != 1 or len(sigma) != len(x_obs):
                    return False, {}, [], "sigma_data must match x_data in shape and length."
                if not np.all(np.isfinite(sigma)) or np.any(sigma <= 0):
                    return False, {}, [], "sigma_data must contain only positive finite uncertainties."
        else:
            n_points = int(params.get("n_points", 50))
            if n_points < 4:
                return False, {}, [], "n_points must be at least four."
            if noise_std <= 0:
                return False, {}, [], "noise_std must be positive."
            t_data = np.linspace(0.0, float(params.get("t_max", 10.0)), n_points)
            x_pure = A_true * np.cos(omega_true * t_data + phi_true)
            rng = np.random.default_rng(seed)
            x_obs = x_pure + rng.normal(0.0, noise_std, size=n_points)
            sigma = np.full_like(x_obs, noise_std, dtype=float)
            data_source = "synthetic"

        def model_func(t, A, omega, phi):
            return A * np.cos(omega * t + phi)

        amplitude_guess = max(float(np.max(np.abs(x_obs))), 1e-6)
        omega_guess = float(params.get("omega_initial", omega_true))
        phase_guess = float(params.get("phi_initial", 0.0))
        p0 = [amplitude_guess, omega_guess, phase_guess]

        popt, pcov = curve_fit(
            model_func,
            t_data,
            x_obs,
            p0=p0,
            sigma=sigma,
            absolute_sigma=True,
            maxfev=int(params.get("maxfev", 20000)),
        )

        A_est, omega_est, phi_est = [float(v) for v in popt]
        perr = np.sqrt(np.maximum(np.diag(pcov), 0.0))
        dof = len(x_obs) - len(popt)
        if dof <= 0:
            return False, {}, [], "Insufficient degrees of freedom for uncertainty estimation."

        t_critical = float(stats.t.ppf(0.975, dof))
        ci_95 = {
            "A": [float(A_est - t_critical * perr[0]), float(A_est + t_critical * perr[0])],
            "omega": [float(omega_est - t_critical * perr[1]), float(omega_est + t_critical * perr[1])],
            "phi": [float(phi_est - t_critical * perr[2]), float(phi_est + t_critical * perr[2])],
        }

        fitted_y = model_func(t_data, *popt)
        residuals = x_obs - fitted_y
        chi2 = float(np.sum((residuals / sigma) ** 2))
        reduced_chi2 = float(chi2 / dof)

        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((x_obs - np.mean(x_obs)) ** 2))
        if ss_tot == 0:
            return False, {}, [], "Observed data have zero variance; R-squared is undefined."
        r_squared = float(1.0 - (ss_res / ss_tot))

        pass_chi2 = 0.5 <= reduced_chi2 <= 2.0
        pass_r2 = r_squared > 0.90
        passed = pass_chi2 and pass_r2

        k_est = m_true * omega_est ** 2
        k_err = abs(2.0 * m_true * omega_est * perr[1])

        goodness_of_fit = {
            "chi2": chi2,
            "reduced_chi2": reduced_chi2,
            "degrees_of_freedom": dof,
            "r_squared": r_squared,
            "residual_mean": float(np.mean(residuals)),
            "residual_std": float(np.std(residuals, ddof=1)),
            "chi2_acceptance_range": [0.5, 2.0],
            "r_squared_threshold": 0.90,
        }

        estimates = {
            "amplitude_A": {
                "estimate": A_est,
                "std_err": float(perr[0]),
                "ci_95": ci_95["A"],
            },
            "frequency_omega": {
                "estimate": omega_est,
                "std_err": float(perr[1]),
                "ci_95": ci_95["omega"],
            },
            "phase_phi": {
                "estimate": phi_est,
                "std_err": float(perr[2]),
                "ci_95": ci_95["phi"],
            },
            "inferred_spring_constant_k": {
                "estimate": float(k_est),
                "std_err": k_err,
                "reference_k": k_true,
            },
        }

        details = {
            "parameter_estimates": estimates,
            "goodness_of_fit": goodness_of_fit,
            "sample_size": int(len(x_obs)),
            "noise_level": float(np.mean(sigma)),
            "data_source": data_source,
            "random_seed": seed if data_source == "synthetic" else None,
            "confidence_level": 0.95,
            "uncertainty_distribution": "Student-t",
        }

        certificates = [
            {
                "step": "non_linear_least_squares_fit",
                "description": (
                    f"Fit x(t) = A*cos(omega*t + phi) on {len(x_obs)} observations"
                ),
                "result": (
                    f"omega_est = {omega_est:.4f} +/- "
                    f"{t_critical * perr[1]:.4f} rad/s"
                ),
            },
            {
                "step": "residual_goodness_of_fit",
                "description": "Computed reduced chi-squared and coefficient of determination R^2",
                "result": (
                    f"Reduced Chi^2 = {reduced_chi2:.3f}, "
                    f"R^2 = {r_squared:.4f}"
                ),
            },
        ]

        error_msg = None if passed else (
            "Statistical fit criteria not satisfied: "
            f"reduced_chi2={reduced_chi2:.3f}, R2={r_squared:.4f}"
        )
        return passed, details, certificates, error_msg
