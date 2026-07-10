"""Unit tests for the Scout's plan parsing + falsifiability guardrail.

These cover the pure logic (extract/validate/assemble); the live web agent in
``scout()`` is exercised separately against a real repo.
"""

import pytest

from lazarus.scout import ResurrectionPlan, plan_from_text

_VALID = """\
Here is my analysis of the repo. Weights ship in the release.

```json
{
  "capability": "one DNA sequence -> per-target chromatin-mark probabilities",
  "base_image": "python:3.6",
  "needs_gpu": false,
  "test_input": "a 1000bp sequence from the repo's sample data",
  "sanity_metric": "roc_auc",
  "sanity_threshold": 0.8,
  "sanity_description": "compute ROC-AUC of predictions vs the shipped labels; expect >= 0.8",
  "goal_text": "Make the pretrained model predict on one sequence and score it.",
  "paper": "Quang & Xie 2016",
  "notes": "Theano may not build on a modern base image"
}
```
"""


def test_parses_valid_plan_and_builds_goal():
    plan = plan_from_text("https://github.com/foo/DanQ", _VALID)
    assert isinstance(plan, ResurrectionPlan)
    assert plan.needs_gpu is False
    assert plan.sanity_threshold == 0.8
    assert plan.base_image == "python:3.6"

    goal = plan.to_goal()
    # the sandbox agent is web-blocked, so the goal must clone the repo itself
    assert "git clone" in goal
    assert "https://github.com/foo/DanQ" in goal
    assert "roc_auc >= 0.8" in goal
    # the summary is human-facing and mentions the key decisions
    assert "DanQ" in plan.summary()
    assert "python:3.6" in plan.summary()


def test_extracts_bare_json_without_fence():
    text = 'ignore me {"capability":"c","base_image":"python:3.9","needs_gpu":true,' \
        '"test_input":"t","sanity_metric":"qualitative","sanity_threshold":null,' \
        '"sanity_description":"outputs at least 3 pockets on 1FKF","goal_text":"g"}'
    plan = plan_from_text("https://github.com/a/b", text)
    assert plan.needs_gpu is True
    assert plan.sanity_threshold is None  # qualitative -> allowed


def test_missing_required_field_raises():
    bad = '```json\n{"capability":"c","needs_gpu":false}\n```'
    with pytest.raises(ValueError, match="missing required field"):
        plan_from_text("u", bad)


def test_non_falsifiable_metric_rejected():
    # a numeric-style metric with no threshold and not declared qualitative
    bad = (
        '```json\n{'
        '"capability":"c","base_image":"python:3.9","needs_gpu":false,'
        '"test_input":"t","sanity_metric":"roc_auc","sanity_threshold":null,'
        '"sanity_description":"d","goal_text":"g"}\n```'
    )
    with pytest.raises(ValueError, match="not falsifiable"):
        plan_from_text("u", bad)


def test_no_json_block_raises():
    with pytest.raises(ValueError, match="no JSON plan block"):
        plan_from_text("u", "the repo looks interesting but I forgot to emit JSON")


def _plan_json(**over):
    base = {
        "capability": "c", "base_image": "python:3.9", "needs_gpu": False,
        "test_input": "t", "sanity_metric": "qualitative", "sanity_threshold": None,
        "sanity_description": "outputs 164 columns on one sequence", "goal_text": "g",
    }
    base.update(over)
    import json
    return "```json\n" + json.dumps(base) + "\n```"


def test_prose_base_image_is_reduced_to_reference():
    # the real bug: the model appended a whole sentence to the image field
    text = _plan_json(
        base_image="kaixhin/cuda-torch:latest (a prebuilt Torch7 image). If unavailable, build from scratch"
    )
    plan = plan_from_text("u", text)
    assert plan.base_image == "kaixhin/cuda-torch:latest"


def test_garbage_base_image_rejected():
    text = _plan_json(base_image="(see notes above)")
    with pytest.raises(ValueError, match="not a valid Docker reference"):
        plan_from_text("u", text)


def test_string_threshold_is_coerced():
    text = (
        '```json\n{'
        '"capability":"c","base_image":"python:3.9","needs_gpu":"false",'
        '"test_input":"t","sanity_metric":"pearson_r","sanity_threshold":"0.6",'
        '"sanity_description":"d","goal_text":"g"}\n```'
    )
    plan = plan_from_text("u", text)
    assert plan.sanity_threshold == 0.6
    assert plan.needs_gpu is True  # non-empty string is truthy -> bool True
