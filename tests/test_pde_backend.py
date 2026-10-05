"""Stage 2B PDE residual acceptance tests."""
from automate.backend.pde_backend import PDEChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.ir.ast import MathematicalExpression

def _check(rule,equation,candidate,parameters):
    g=DerivationGraph(id="pde")
    g.add_node(DerivationNode(id="eq",expression=MathematicalExpression(raw_str=equation)))
    g.add_node(DerivationNode(id="sol",expression=MathematicalExpression(raw_str=candidate)))
    e=DerivationEdge(id="e",input_nodes=["eq"],output_nodes=["sol"],transformation_rule=rule,
        justification="Stage 2B PDE acceptance",checker="pde",parameters=parameters)
    return PDEChecker().verify_edge(e,g)

def test_heat_equation():
    p={"variables":["x","t"],"parameters":["alpha"],"equation":"diff(u(x,t),t)-alpha*diff(u(x,t),x,2)"}
    assert _check("heat_equation","unused","exp(-alpha*t)*sin(x)",p).passed

def test_wave_equation():
    p={"variables":["x","t"],"parameters":["c"],"equation":"diff(u(x,t),t,2)-c**2*diff(u(x,t),x,2)"}
    assert _check("wave_equation","unused","sin(x-c*t)",p).passed

def test_laplace_and_poisson():
    assert _check("laplace_equation","unused","x**2-y**2",{"variables":["x","y"],"equation":"diff(u(x,y),x,2)+diff(u(x,y),y,2)"}).passed
    assert _check("poisson_equation","unused","x**2/2",{"variables":["x","y"],"parameters":["source"],"equation":"diff(u(x,y),x,2)+diff(u(x,y),y,2)-source"}).passed is False

def test_wrong_candidate_rejected():
    p={"variables":["x","t"],"parameters":["alpha"],"equation":"diff(u(x,t),t)-alpha*diff(u(x,t),x,2)"}
    assert not _check("heat_equation","unused","exp(-alpha*t)*cos(x)+t",p).passed

def test_malformed_variable_contract_fails_closed():
    assert not _check("heat_equation","unused","u",{"variables":[]}).passed
