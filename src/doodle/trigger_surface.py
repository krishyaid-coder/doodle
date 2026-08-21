"""Trigger-surface analysis: does a description use the words users actually type?

Motivation
----------
Claude picks a skill by matching the user's prompt against skill descriptions.
A description written in formal or abstract language ("performs static analysis
of committed changesets") shares almost no vocabulary with how people actually
ask ("check my code"), so the skill silently underfires. Static rules that only
measure length or look for the literal phrase "use when" cannot see this.

This module measures the lexical gap between a description and a set of
realistic user prompts. It is deliberately a *proxy*: real skill selection uses
embeddings, not bag-of-words overlap. Lexical coverage is a cheap, deterministic,
offline screen that correlates with the real thing — it is not the real thing.
Validating the proxy against empirical eval runs is future work (see docs).

Metrics
-------
``coverage(description, prompt)``
    Fraction of the prompt's content words that appear in the description,
    after stopword removal and light stemming. 1.0 means every meaningful word
    the user typed is present in the description.

``TriggerSurface.fire_coverage``
    Mean coverage across the ``should_fire`` prompts. Higher is better.

``TriggerSurface.nofire_coverage``
    Mean coverage across the ``should_not_fire`` prompts. Lower is better —
    high values predict over-firing on adjacent requests.

``TriggerSurface.margin``
    ``fire_coverage - nofire_coverage``. This is the discriminating signal: a
    description can score high on fire_coverage simply by being long and
    generic, but that also inflates nofire_coverage. Margin rewards
    descriptions that match their own use cases *and not* neighbouring ones.

Prompt source
-------------
Prompts come from, in order of preference:

1. An ``eval.yaml`` sitting next to the SKILL.md (the author's own test cases).
2. The best-matching built-in category template from :mod:`doodle.templates`.

If neither yields prompts the analysis is skipped rather than guessed at.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .templates import Template, list_templates


# Function words plus a few that appear in nearly every imperative request and
# therefore carry no discriminating signal ("me", "my", "this", "please").
STOPWORDS: frozenset[str] = frozenset(
    """
    a an and are as at be been being but by can could did do does doing done
    for from get give had has have having he her him his how i if in into is
    it its just like make me my need of on once only or our out over please
    should so some than that the their them then there these they this those
    through to too up us use used using want was we were what when where which
    while who why will with would you your
    """.split()
)

_WORD_RE = re.compile(r"[a-z][a-z'-]*")


def _stem(word: str) -> str:
    """Crude suffix stripping so 'reviews'/'reviewing'/'reviewed' collapse.

    Deliberately conservative: over-stemming creates false matches, which
    inflate coverage scores and make the metric look better than it is.

    The trailing-e strip at the end is what makes silent-e verbs agree:
    'stage' -> 'stag', 'staged' -> 'stag', 'staging' -> 'stag'. The output is
    not a real word, which is fine — only consistency between the description
    and the prompt matters here.
    """
    if len(word) > 5 and word.endswith("ing"):
        word = word[:-3]
    elif len(word) > 4 and word.endswith("ed"):
        word = word[:-2]
    elif len(word) > 4 and word.endswith("ies"):
        word = word[:-3] + "y"
    elif len(word) > 4 and word.endswith("es") and not word.endswith("sses"):
        word = word[:-2]
    elif len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]

    if len(word) > 3 and word.endswith("e"):
        word = word[:-1]
    return word


def tokenize(text: str) -> set[str]:
    """Lowercase, extract alphabetic words, drop stopwords, stem."""
    if not text:
        return set()
    words = _WORD_RE.findall(text.lower())
    return {
        _stem(w)
        for w in words
        if w not in STOPWORDS and len(w) > 1 and _stem(w) not in STOPWORDS
    }


def coverage(description: str, prompt: str) -> float:
    """Fraction of the prompt's content words present in the description.

    Returns 1.0 for prompts with no content words (nothing to miss).
    """
    prompt_tokens = tokenize(prompt)
    if not prompt_tokens:
        return 1.0
    desc_tokens = tokenize(description)
    return len(prompt_tokens & desc_tokens) / len(prompt_tokens)


@dataclass(frozen=True)
class PromptCoverage:
    prompt: str
    score: float
    missing: tuple[str, ...]
    expected_fire: bool


@dataclass(frozen=True)
class TriggerSurface:
    """Result of analysing one description against one prompt set."""

    fire_coverage: float
    nofire_coverage: float
    per_prompt: tuple[PromptCoverage, ...]
    source: str  # "eval.yaml" | "template:<name>"

    @property
    def margin(self) -> float:
        """How much better the description matches its own use cases than
        adjacent ones. Negative means the description is more attractive to
        requests it should ignore than to the ones it should serve."""
        return self.fire_coverage - self.nofire_coverage

    @property
    def weakest(self) -> tuple[PromptCoverage, ...]:
        """Should-fire prompts with the lowest coverage, worst first."""
        fires = [p for p in self.per_prompt if p.expected_fire]
        return tuple(sorted(fires, key=lambda p: p.score)[:5])


def analyze(
    description: str,
    should_fire: tuple[str, ...] | list[str],
    should_not_fire: tuple[str, ...] | list[str],
    source: str = "unknown",
) -> TriggerSurface:
    per_prompt: list[PromptCoverage] = []
    desc_tokens = tokenize(description)

    fire_scores: list[float] = []
    for prompt in should_fire:
        score = coverage(description, prompt)
        missing = tuple(sorted(tokenize(prompt) - desc_tokens))
        per_prompt.append(PromptCoverage(prompt, score, missing, True))
        fire_scores.append(score)

    nofire_scores: list[float] = []
    for prompt in should_not_fire:
        score = coverage(description, prompt)
        missing = tuple(sorted(tokenize(prompt) - desc_tokens))
        per_prompt.append(PromptCoverage(prompt, score, missing, False))
        nofire_scores.append(score)

    return TriggerSurface(
        fire_coverage=sum(fire_scores) / len(fire_scores) if fire_scores else 0.0,
        nofire_coverage=sum(nofire_scores) / len(nofire_scores) if nofire_scores else 0.0,
        per_prompt=tuple(per_prompt),
        source=source,
    )


# A category match must clear this absolute floor...
MIN_CATEGORY_MATCH = 0.15
# ...and beat the runner-up by this factor. Without the second test, a skill
# belonging to no built-in category still gets assigned to whichever one it
# resembles marginally most, and is then judged against irrelevant prompts.
MIN_CATEGORY_CONFIDENCE = 1.3


def best_matching_template(description: str) -> Template | None:
    """Pick the built-in category whose should_fire prompts best match.

    Used when the author has no eval.yaml. Returns None unless one category is
    both a decent match in absolute terms and clearly better than the next
    best — analysing a skill against prompts from an unrelated domain produces
    confident-looking nonsense.
    """
    scored: list[tuple[float, Template]] = []
    for tpl in list_templates():
        scores = [coverage(description, p) for p in tpl.should_fire]
        mean = sum(scores) / len(scores) if scores else 0.0
        scored.append((mean, tpl))

    if not scored:
        return None

    scored.sort(key=lambda pair: pair[0], reverse=True)
    best_score, best_tpl = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0

    if best_score < MIN_CATEGORY_MATCH:
        return None
    if runner_up > 0 and best_score < runner_up * MIN_CATEGORY_CONFIDENCE:
        return None
    return best_tpl


def load_prompts_for_skill(
    skill_path: Path, description: str
) -> tuple[tuple[str, ...], tuple[str, ...], str] | None:
    """Resolve a prompt set for this skill.

    Prefers the author's own ``eval.yaml``; falls back to the closest built-in
    category. Returns ``(should_fire, should_not_fire, source)`` or None when
    no defensible prompt set exists.
    """
    eval_path = skill_path.parent / "eval.yaml"
    if eval_path.is_file():
        try:
            from .eval.schema import EvalSuite

            suite = EvalSuite.load(eval_path)
            if suite.should_fire:
                return suite.should_fire, suite.should_not_fire, "eval.yaml"
        except Exception:
            # A malformed eval.yaml is reported by the eval tooling, not here.
            pass

    tpl = best_matching_template(description)
    if tpl is None:
        return None
    return tpl.should_fire, tpl.should_not_fire, f"template:{tpl.name}"
