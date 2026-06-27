"""doodle eval — trigger-accuracy harness.

Phase 2: measures whether Claude actually invokes a skill on natural-language
prompts. Wraps Promptfoo's `skill-used` assertion (we generate the config,
shell out to ``promptfoo eval``, parse the JSON results).

``--generate`` uses the Anthropic SDK to draft starter prompts so authors
don't face a blank page.

Modules:
    schema      — EvalSuite dataclass + YAML round-trip
    promptfoo   — generate Promptfoo config + invoke subprocess + parse results
    generate    — draft eval.yaml via Anthropic SDK
    runner      — orchestration: discover, run, score, format
"""

from .schema import EvalSuite, EvalResult, PromptResult
from .runner import run_eval, generate_eval

__all__ = [
    "EvalSuite",
    "EvalResult",
    "PromptResult",
    "run_eval",
    "generate_eval",
]
