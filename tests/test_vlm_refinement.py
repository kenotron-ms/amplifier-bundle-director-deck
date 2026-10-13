"""Regression coverage for the optional VLM refinement embedded in the recipe.

These tests execute the relevant AST nodes extracted from the shipped YAML
heredoc. They intentionally use only Python fakes: no Playwright, network, or
paid OpenAI request is involved.
"""

import ast
import base64
import builtins
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


RECIPE_PATH = Path("recipes/director-deck.yaml")
_HEREDOC = re.compile(
    r"(?ms)^[ \t]*python[ \t]+-[ \t]+<<'PY_DIRECTOR_DECK_ANALYZE_HTML'[^\n]*\n"
    r"(?P<payload>.*?)(?=^[ \t]*PY_DIRECTOR_DECK_ANALYZE_HTML[ \t]*$)"
)


class FakePage:
    """Small pure-Python stand-in for the page calls used by the AST fragment."""

    def __init__(self, viewport, png_bytes=b"preview-bytes"):
        self.viewport = viewport
        self.png_bytes = png_bytes
        self.screenshot_viewports = []
        self.viewport_changes = []
        self.waits = []

    def screenshot(self):
        self.screenshot_viewports.append(self.viewport)
        return self.png_bytes

    def set_viewport_size(self, size):
        self.viewport = (size["width"], size["height"])
        self.viewport_changes.append(self.viewport)

    def wait_for_timeout(self, milliseconds):
        self.waits.append(milliseconds)


class FakeOpenAI:
    """A recording OpenAI module with configurable completion behavior."""

    def __init__(self, response=None, error=None):
        self.calls = []
        self.client_options = []
        self.response = response
        self.error = error
        self.client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=self._create),
            ),
        )

    def OpenAI(self, **kwargs):
        self.client_options.append(kwargs)
        return self.client

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.response))],
        )


def _analyze_html_payload(vlm_refine_value):
    """Load the exact analysis heredoc after safely rendering only its flag."""

    recipe = yaml.safe_load(RECIPE_PATH.read_text(encoding="utf-8"))
    command = next(
        step["command"]
        for stage in recipe["stages"]
        for step in stage["steps"]
        if step["id"] == "analyze-html-deck"
    )
    rendered = command.replace("{{vlm_refine}}", vlm_refine_value)
    match = _HEREDOC.search(rendered)
    assert match, "analyze-html-deck must retain its quoted Python heredoc"
    return ast.parse(match.group("payload"), filename=str(RECIPE_PATH), feature_version=(3, 11))


def _extract_vlm_nodes(vlm_refine_value):
    """Extract the actual flag assignment, helper, and nested refinement if."""

    tree = _analyze_html_payload(vlm_refine_value)
    assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "vlm_refine_enabled"
            for target in node.targets
        )
    ]
    helpers = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_vlm_cramped_check"
    ]
    refinement_ifs = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Name)
        and node.test.id == "vlm_refine_enabled"
    ]

    assert len(assignments) == 1
    assert len(helpers) == 1
    assert len(refinement_ifs) == 1

    parents = {
        id(child): parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    ancestor = parents[id(refinement_ifs[0])]
    while_ancestors = []
    while ancestor is not None:
        if isinstance(ancestor, ast.While):
            while_ancestors.append(ancestor)
        ancestor = parents.get(id(ancestor))
    assert any(
        isinstance(loop.test, ast.Compare)
        and isinstance(loop.test.left, ast.Name)
        and loop.test.left.id == "slide_num"
        for loop in while_ancestors
    ), "the exact VLM if must remain nested in the keyboard capture loop"

    return assignments[0], helpers[0], refinement_ifs[0]


def _compile_exec(nodes, namespace):
    """Compile only the recipe nodes under test into the supplied fake context."""

    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(RECIPE_PATH), "exec"), namespace)


def _builtins_with_openai_import_failure():
    guarded = dict(vars(builtins))
    original_import = builtins.__import__

    def guard(name, *args, **kwargs):
        if name == "openai":
            raise ModuleNotFoundError("openai deliberately unavailable in this test")
        return original_import(name, *args, **kwargs)

    guarded["__import__"] = guard
    return guarded


def _execute_refinement(
    vlm_refine_value,
    *,
    chosen_index=0,
    builtins_namespace=None,
):
    """Execute the exact extracted recipe fragment against a fake page."""

    assignment, helper, refinement_if = _extract_vlm_nodes(vlm_refine_value)
    ladder = [
        (1280, 720),
        (1408, 792),
        (1536, 864),
    ]
    chosen_w, chosen_h = ladder[chosen_index]
    page = FakePage((chosen_w, chosen_h))
    navigations = []
    namespace = {
        "__builtins__": builtins_namespace or builtins,
        "NAV_LADDER": ladder,
        "chosen_w": chosen_w,
        "chosen_h": chosen_h,
        "page": page,
        "slide_num": 1,
        "navigate_to": navigations.append,
    }

    _compile_exec([assignment, helper, refinement_if], namespace)
    return namespace, page, navigations


def test_default_flag_skips_the_actual_helper_without_openai_import_or_preview():
    namespace, page, navigations = _execute_refinement(
        "",
        builtins_namespace=_builtins_with_openai_import_failure(),
    )

    assert namespace["vlm_refine_enabled"] is False
    assert page.screenshot_viewports == []
    assert page.viewport_changes == []
    assert navigations == []


@pytest.mark.parametrize("opt_in_value", ["true", "1", "yes", "on"])
def test_flag_assignment_enables_each_documented_opt_in_form(opt_in_value):
    assignment, _, _ = _extract_vlm_nodes(opt_in_value)
    namespace = {}

    _compile_exec([assignment], namespace)

    assert namespace["vlm_refine_enabled"] is True


def test_cramped_bumps_once_and_preserves_preview_request_contract(monkeypatch):
    fake_openai = FakeOpenAI(response="cramped")
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    namespace, page, navigations = _execute_refinement(
        "true",
    )

    assert (namespace["chosen_w"], namespace["chosen_h"]) == (1408, 792)
    assert page.screenshot_viewports == [(1280, 720)]
    assert page.viewport_changes == [(1408, 792)]
    assert navigations == [1]
    assert len(fake_openai.calls) == 1
    assert fake_openai.client_options == [{"timeout": 5.0, "max_retries": 0}]

    request = fake_openai.calls[0]
    assert request["model"] == "gpt-4o-mini"
    assert request["messages"][0]["content"][1]["image_url"]["url"] == (
        "data:image/png;base64," + base64.b64encode(b"preview-bytes").decode()
    )


@pytest.mark.parametrize("verdict", ["small", "good", "unexpected", None])
def test_non_bump_verdicts_preserve_the_overflow_chosen_viewport(monkeypatch, verdict):
    fake_openai = FakeOpenAI(response=verdict)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    namespace, page, navigations = _execute_refinement(
        "true",
    )

    assert (namespace["chosen_w"], namespace["chosen_h"]) == (1280, 720)
    assert page.screenshot_viewports == [(1280, 720)]
    assert page.viewport_changes == []
    assert navigations == []
    assert len(fake_openai.calls) == 1


def test_top_of_ladder_skips_preview_and_openai_request(monkeypatch):
    fake_openai = FakeOpenAI(response="cramped")
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    namespace, page, navigations = _execute_refinement(
        "true",
        chosen_index=2,
    )

    assert (namespace["chosen_w"], namespace["chosen_h"]) == (1536, 864)
    assert page.screenshot_viewports == []
    assert page.viewport_changes == []
    assert navigations == []
    assert fake_openai.calls == []


@pytest.mark.parametrize("failure_mode", ["api", "import"])
def test_api_or_import_failure_warns_and_keeps_current_viewport(
    monkeypatch, capsys, failure_mode
):
    if failure_mode == "api":
        fake_openai = FakeOpenAI(error=RuntimeError("service unavailable"))
        monkeypatch.setitem(sys.modules, "openai", fake_openai)
        builtins_namespace = None
    else:
        monkeypatch.delitem(sys.modules, "openai", raising=False)
        fake_openai = None
        builtins_namespace = _builtins_with_openai_import_failure()

    namespace, page, navigations = _execute_refinement(
        "true",
        builtins_namespace=builtins_namespace,
    )

    assert "VLM check failed for slide 1" in capsys.readouterr().out
    assert (namespace["chosen_w"], namespace["chosen_h"]) == (1280, 720)
    assert page.screenshot_viewports == [(1280, 720)]
    assert page.viewport_changes == []
    assert navigations == []