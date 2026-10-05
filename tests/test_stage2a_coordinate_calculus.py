"""Stage 2A coordinate-aware vector calculus and potential reconstruction tests."""
from automate.backend.coordinate_vector_calculus_backend import CoordinateVectorCalculusChecker
from automate.backend.vector_calculus_backend import VectorCalculusChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.core.status import VerificationStatus
from automate.ir.ast import MathematicalExpression

def _check(rule, inputs, outputs, checker, parameters):
    g=DerivationGraph(id="stage2a")
    ins=[]; outs=[]
    for i,e in enumerate(inputs):
        n=f"i{i}"; ins.append(n); g.add_node(DerivationNode(id=n,expression=MathematicalExpression(raw_str=e)))
    for i,e in enumerate(outputs):
        n=f"o{i}"; outs.append(n); g.add_node(DerivationNode(id=n,expression=MathematicalExpression(raw_str=e)))
    edge=DerivationEdge(id="e",input_nodes=ins,output_nodes=outs,transformation_rule=rule,
        justification="Stage 2A coordinate test",checker=checker,parameters=parameters)
    return (CoordinateVectorCalculusChecker() if checker=="coordinate_vector_calculus" else VectorCalculusChecker()).verify_edge(edge,g)

def test_cylindrical_gradient_and_laplacian():
    p={"coordinate_system":"cylindrical","coordinates":["r","phi","z"],"domain_exclusions":["r != 0"]}
    assert _check("coordinate_gradient",["r**2*sin(phi)+z"],["Vector([2*r*sin(phi), r*cos(phi), 1])"],"coordinate_vector_calculus",p).passed
    assert _check("coordinate_laplacian",["r**2+z**2"],["4"],"coordinate_vector_calculus",p).passed

def test_spherical_gradient():
    p={"coordinate_system":"spherical","coordinates":["r","theta","phi"],"domain_exclusions":["r != 0","sin(theta) != 0"]}
    assert _check("coordinate_gradient",["r**2*cos(theta)"],["Vector([2*r*cos(theta), -sin(theta), 0])"],"coordinate_vector_calculus",p).passed

def test_coordinate_divergence_and_curl_differ_from_cartesian():
    p={"coordinate_system":"cylindrical","coordinates":["r","phi","z"],"domain_exclusions":["r != 0"]}
    assert _check("coordinate_divergence",["Vector([r**2,0,0])"],["3*r"],"coordinate_vector_calculus",p).passed
    assert _check("coordinate_curl",["Vector([0,r**2,0])"],["Vector([0,0,2*r])"],"coordinate_vector_calculus",p).passed

def test_coordinate_backend_fails_closed():
    p={"coordinate_system":"toroidal","coordinates":["u","v","w"]}
    assert not _check("coordinate_gradient",["u"],["Vector([1,0,0])"],"coordinate_vector_calculus",p).passed
    p={"coordinate_system":"cylindrical","coordinates":["r","phi","z"],"scale_factors":["1","0","1"]}
    assert not _check("coordinate_gradient",["r"],["Vector([1,0,0])"],"coordinate_vector_calculus",p).passed
    p={"coordinate_system":"cylindrical","coordinates":["r","phi"]}
    assert not _check("coordinate_gradient",["r"],["Vector([1])"],"coordinate_vector_calculus",p).passed

def test_reconstruct_and_verify_potential():
    report=_check("reconstruct_potential",["Vector([2*x*y, x**2+2*y])"],["x**2*y+y**2"],"vector_calculus",{"coordinates":["x","y"],"base_point":[0,0]})
    assert report.passed and report.status == VerificationStatus.SYMBOLIC_CHECKED

def test_reconstruction_rejects_nonconservative_field():
    report=_check("reconstruct_potential",["Vector([-y,x])"],["0"],"vector_calculus",{"coordinates":["x","y"],"base_point":[0,0]})
    assert not report.passed
