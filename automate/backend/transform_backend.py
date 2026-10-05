"""Bounded transform backend using explicit conventions and symbolic verification."""
from __future__ import annotations
import sympy as sp
from automate.backend.base import BaseChecker, VerificationEvidence, VerificationReport
from automate.core.status import VerificationStatus

FOURIER_CONVENTION="F(w)=Integral(f(x)*exp(-I*w*x), (x,-oo,oo)); inverse=Integral(F(w)*exp(I*w*x)/(2*pi), (w,-oo,oo))"
LAPLACE_CONVENTION="F(s)=Integral(f(t)*exp(-s*t), (t,0,oo)); inverse uses the Bromwich convention"

class TransformChecker(BaseChecker):
    _RULES={"fourier_transform","inverse_fourier_transform","verify_fourier_pair",
            "laplace_transform","inverse_laplace_transform","verify_laplace_pair","convolution","verify_convolution_theorem",
            "fourier_series"}
    @property
    def name(self): return "TransformChecker"
    @property
    def version(self): return f"SymPy {sp.__version__}"

    def _report(self,edge,graph,status,passed,details,msg=None):
        ev=VerificationEvidence(backend=self.name,backend_version=self.version,
            input_node_ids=edge.input_nodes,output_node_ids=edge.output_nodes,
            assumptions_used=list(graph.compute_inherited_assumptions(edge.input_nodes[0])) if edge.input_nodes else [],
            side_conditions_checked=edge.side_conditions,generated_obligations=edge.verification_obligations,
            command_invocation=f"TransformChecker.verify_edge('{edge.id}')",passed=passed,status=status,
            execution_time_ms=0,reproducibility={"sympy":sp.__version__},metrics={"operation":details.get("operation")})
        return VerificationReport(status=status,backend=self.name,backend_version=self.version,execution_time_ms=0,
            passed=passed,details=details,error_message=msg,evidence=ev)

    @staticmethod
    def _expr(raw, varnames):
        loc={x:sp.Symbol(x, real=True) for x in varnames}
        loc.update({"pi":sp.pi,"oo":sp.oo,"I":sp.I,"exp":sp.exp,"sin":sp.sin,"cos":sp.cos,"Heaviside":sp.Heaviside})
        return sp.sympify(raw,locals=loc)

    def verify_edge(self,edge,graph):
        rule=edge.transformation_rule; d={"operation":rule}
        try:
            p=edge.parameters or {}; convention=p.get("convention")
            if rule.startswith("fourier") or rule=="verify_fourier_pair":
                if convention!="angular_2pi":
                    return self._report(edge,graph,VerificationStatus.UNKNOWN,False,d,"Explicit Fourier convention required: angular_2pi.")
            if rule=="fourier_transform":
                x=p.get("source_variable","x"); w=p.get("target_variable","w")
                f=self._expr(graph.nodes[edge.input_nodes[0]].expression.raw_str,[x])
                claimed=self._expr(graph.nodes[edge.output_nodes[0]].expression.raw_str,[w])
                expected=sp.integrate(f*sp.exp(-sp.I*w*sp.Symbol(x)),(sp.Symbol(x),-sp.oo,sp.oo))
                if expected.has(sp.Integral): return self._report(edge,graph,VerificationStatus.UNKNOWN,False,d,"Transform existence/result unresolved.")
                ok=sp.simplify(expected-claimed)==0
            elif rule=="inverse_fourier_transform":
                w=p.get("source_variable","w"); x=p.get("target_variable","x")
                F=self._expr(graph.nodes[edge.input_nodes[0]].expression.raw_str,[w])
                claimed=self._expr(graph.nodes[edge.output_nodes[0]].expression.raw_str,[x])
                W=sp.Symbol(w); X=sp.Symbol(x)
                expected=sp.integrate(F*sp.exp(sp.I*W*X)/(2*sp.pi),(W,-sp.oo,sp.oo))
                if expected.has(sp.Integral): return self._report(edge,graph,VerificationStatus.UNKNOWN,False,d,"Inverse transform unresolved.")
                ok=sp.simplify(expected-claimed)==0
            elif rule=="laplace_transform":
                t=p.get("source_variable","t"); s=p.get("target_variable","s")
                f=self._expr(graph.nodes[edge.input_nodes[0]].expression.raw_str,[t])
                claimed=self._expr(graph.nodes[edge.output_nodes[0]].expression.raw_str,[s])
                T=sp.Symbol(t); S=sp.Symbol(s)
                expected=sp.integrate(f*sp.exp(-S*T),(T,0,sp.oo))
                if expected.has(sp.Integral): return self._report(edge,graph,VerificationStatus.UNKNOWN,False,d,"Laplace transform unresolved; convergence not established.")
                ok=sp.simplify(expected-claimed)==0
            elif rule=="inverse_laplace_transform":
                s=p.get("source_variable","s"); t=p.get("target_variable","t")
                F=self._expr(graph.nodes[edge.input_nodes[0]].expression.raw_str,[s])
                claimed=self._expr(graph.nodes[edge.output_nodes[0]].expression.raw_str,[t])
                expected=sp.inverse_laplace_transform(F,sp.Symbol(s),sp.Symbol(t))
                if expected.has(sp.InverseLaplaceTransform): return self._report(edge,graph,VerificationStatus.UNKNOWN,False,d,"Inverse Laplace unresolved.")
                ok=sp.simplify(expected-claimed)==0
            elif rule=="convolution":
                t=p.get("source_variable","t"); tau=sp.Symbol(p.get("integration_variable","tau")); T=sp.Symbol(t)
                f=self._expr(graph.nodes[edge.input_nodes[0]].expression.raw_str,[t]); g=self._expr(graph.nodes[edge.input_nodes[1]].expression.raw_str,[t])
                claimed=self._expr(graph.nodes[edge.output_nodes[0]].expression.raw_str,[t])
                expected=sp.integrate(f.subs(T,tau)*g.subs(T,T-tau),(tau,-sp.oo,sp.oo))
                if expected.has(sp.Integral): return self._report(edge,graph,VerificationStatus.UNKNOWN,False,d,"Convolution unresolved.")
                ok=sp.simplify(expected-claimed)==0
            else:
                return self._report(edge,graph,VerificationStatus.UNKNOWN,False,d,"Rule requires a future structured verification path.")
            d["symbolic_equivalence"]=bool(ok)
            return self._report(edge,graph,VerificationStatus.SYMBOLIC_CHECKED if ok else VerificationStatus.FAILED,ok,d,None if ok else "Transform claim rejected.")
        except (KeyError,TypeError,ValueError,sp.SympifyError,sp.PoleError) as exc:
            return self._report(edge,graph,VerificationStatus.FAILED,False,d,f"Transform verification failed: {exc}")
