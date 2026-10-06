# Free / Local Reasoning Stack

Automate's learning model adapter intentionally uses a small OpenAI-compatible
HTTP surface rather than a vendor-specific SDK.

This permits several deployment modes without changing the learning contracts:

## Local desktop

Use an OpenAI-compatible local server such as llama.cpp's `llama-server`.
The server can run GGUF models locally, including models obtained from
Hugging Face. The learning adapter only needs the server URL.

Reference: https://github.com/ggml-org/llama.cpp
Reference: https://huggingface.co/

## Local / GPU server

Use vLLM when a higher-throughput open-source serving layer is useful.
The learning adapter remains unchanged because the transport contract is
OpenAI-compatible.

Reference: https://docs.vllm.ai/

## Role separation

The model is never an authority source.

It can:

- cluster repeated experiences;
- suggest candidate lessons;
- suggest candidate system-evolution proposals;
- propose hypotheses or experiment designs.

Automate still validates the artifact, records provenance, requires independent
verification for adoption, and routes source changes through the normal PR/CI/
reconciliation lifecycle.

This makes the system model-swappable. Better or cheaper models can be tested
against the same learning corpus without rewriting the scientific governance
layer.

## Planned model ensemble

The mature system should not depend on one model either. A future ensemble can
use separate local workers for:

- mathematical pattern extraction;
- code-oriented implementation planning;
- adversarial critique;
- scientific hypothesis generation;
- experiment design;
- result summarization.

Agreement between models is evidence to investigate, not automatic verification.
