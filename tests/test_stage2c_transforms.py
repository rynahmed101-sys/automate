"""Stage 2C transform acceptance tests."""
from automate.backend.transform_backend import TransformChecker
from automate.core.edge import DerivationEdge
from automate.core.graph import DerivationGraph
from automate.core.node import DerivationNode
from automate.ir.ast import MathematicalExpression

def _check(rule,ins,out,p):
    g=DerivationGraph(id="s2c"); ids=[]
    for i,x in enumerate(ins):
        k=f"i{i}"; ids.append(k); g.add_node(DerivationNode(id=k,expression=MathematicalExpression(raw_str=x)))
    o="o"; g.add_node(DerivationNode(id=o,expression=MathematicalExpression(raw_str=out)))
    e=DerivationEdge(id="e",input_nodes=ids,output_nodes=[o],transformation_rule=rule,
        justification="Stage 2C acceptance",checker="transform",parameters=p)
    return TransformChecker().verify_edge(e,g)

def test_fourier_gaussian_pair():
    r=_check("fourier_transform",["exp(-x**2)"],["sqrt(pi)*exp(-w**2/4)"],
             {"source_variable":"x","target_variable":"w","convention":"angular_2pi"})
    assert r.passed

def test_inverse_fourier_pair():
    r=_check("inverse_fourier_transform",["sqrt(pi)*exp(-w**2/4)"],["exp(-x**2)"],
             {"source_variable":"w","target_variable":"x","convention":"angular_2pi"})
    assert r.passed

def test_laplace_pair_both_directions():
    p={"source_variable":"t","target_variable":"s","convention":"explicit"}
    assert _check("laplace_transform",["exp(-2*t)"],["1/(s+2)"],p).passed
    assert _check("inverse_laplace_transform",["1/(s+2)"],["exp(-2*t)"],
                  {"source_variable":"s","target_variable":"t","convention":"explicit"}).passed

def test_convolution():
    r=_check("convolution",["exp(-t)","exp(-t)"],["exp(-t)*t/1"],
             {"source_variable":"t","integration_variable":"tau"})
    assert r.passed

def test_fourier_requires_explicit_convention():
    assert not _check("fourier_transform",["exp(-x**2)"],["sqrt(pi)*exp(-w**2/4)"],
                       {"source_variable":"x","target_variable":"w"}).passed

def test_wrong_transform_rejected():
    assert not _check("laplace_transform",["exp(-2*t)"],["1/(s+3)"],
                       {"source_variable":"t","target_variable":"s","convention":"explicit"}).passed

def test_unsupported_inverse_case_is_not_certified():
    r=_check("inverse_laplace_transform",["log(s)"],["-1/t"],
             {"source_variable":"s","target_variable":"t","convention":"explicit"})
    assert not r.passed
