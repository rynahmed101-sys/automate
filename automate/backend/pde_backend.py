"""Reusable bounded PDE residual verification backend.

PDEs are represented by an equation expression, explicit independent variables,
parameters and a candidate solution.  The backend constructs a symbolic
residual after substitution and never treats a named PDE as a pattern-only
success.
"""
from __future__ import annotations
import time
import sympy as sp
from automate.backend.base import BaseChecker, VerificationEvidence, VerificationReport
from automate.core.status import VerificationStatus

class PDEChecker(BaseChecker):
    _RULES={"verify_pde_solution","heat_equation","wave_equation","laplace_equation","poisson_equation"}

    @property
    def name(self): return "PDEChecker"
    @property
    def version(self): return f"SymPy {sp.__version__}"

    def _parse(self, raw, variables, parameters):
        funcs={str(v):sp.Function(str(v)) for v in variables}
        loc={"diff":sp.diff,"Derivative":sp.Derivative,"Eq":sp.Eq,"sin":sp.sin,"cos":sp.cos,
             "exp":sp.exp,"sqrt":sp.sqrt,"pi":sp.pi}
        loc.update({str(v):sp.Symbol(str(v)) for v in variables})
        loc.update({str(v):sp.Symbol(str(v)) for v in parameters})
        loc.update(funcs)
        return sp.sympify(str(raw),locals=loc)

    def _report(self, edge, graph, status, passed, details, msg=None):
        edge.status=status; edge.checker="pde"
        evidence=VerificationEvidence(backend=self.name,backend_version=self.version,
            input_node_ids=edge.input_nodes,output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,generated_obligations=edge.verification_obligations,
            command_invocation=f"PDEChecker.verify_edge('{edge.id}')",passed=passed,status=status,
            execution_time_ms=0.0,reproducibility={"sympy":sp.__version__},
            metrics={"operation":details.get("operation")})
        edge.evidence=evidence.to_dict()
        return VerificationReport(status=status,backend=self.name,backend_version=self.version,
            execution_time_ms=0.0,passed=passed,details=details,error_message=msg,evidence=evidence)

    def verify_edge(self, edge, graph):
        start=time.perf_counter(); rule=edge.transformation_rule; details={"operation":rule}
        if rule not in self._RULES: return self._report(edge,graph,VerificationStatus.NOT_APPLICABLE,False,details,"Unsupported PDE rule.")
        try:
            variables=edge.parameters.get("variables")
            if not isinstance(variables,list) or not variables or not all(isinstance(v,str) and v.isidentifier() for v in variables):
                raise ValueError("variables must be an explicit non-empty identifier list")
            params=edge.parameters.get("parameters",[])
            if not isinstance(params,list) or not all(isinstance(v,str) and v.isidentifier() for v in params):
                raise ValueError("parameters must be an identifier list")
            equation_raw=graph.nodes[edge.input_nodes[0]].expression.raw_str
            candidate_raw=graph.nodes[edge.output_nodes[0]].expression.raw_str
            if rule!="verify_pde_solution":
                equation_raw={
                    "heat_equation":edge.parameters.get("equation","diff(u(x,t),t)-alpha*diff(u(x,t),x,2)"),
                    "wave_equation":edge.parameters.get("equation","diff(u(x,t),t,2)-c**2*diff(u(x,t),x,2)"),
                    "laplace_equation":edge.parameters.get("equation","diff(u(x,y),x,2)+diff(u(x,y),y,2)"),
                    "poisson_equation":edge.parameters.get("equation","diff(u(x,y),x,2)+diff(u(x,y),y,2)-source"),
                }[rule]
            equation=self._parse(equation_raw,variables,params)
            candidate=self._parse(candidate_raw,variables,params)
            # Replace declared unknown functions by candidate expressions.
            residual=equation
            functions=sorted([f for f in residual.atoms(sp.Function) if isinstance(f,sp.Function)], key=str)
            if not functions:
                raise ValueError("PDE equation must contain an explicit dependent function")
            for fn in functions:
                replacement=candidate
                residual=residual.xreplace({fn:replacement})
            residual=sp.simplify(sp.expand(residual.doit()))
            details.update({"equation":str(equation),"candidate":str(candidate),"residual":str(residual)})
            if residual==0:
                details["symbolic_equivalence"]=True
                return self._report(edge,graph,VerificationStatus.SYMBOLIC_CHECKED,True,details)
            return self._report(edge,graph,VerificationStatus.FAILED,False,details,"Candidate does not satisfy PDE; nonzero residual.")
        except (KeyError,TypeError,ValueError,sp.SympifyError,AttributeError) as exc:
            return self._report(edge,graph,VerificationStatus.FAILED,False,details,f"PDE verification failed: {exc}")
