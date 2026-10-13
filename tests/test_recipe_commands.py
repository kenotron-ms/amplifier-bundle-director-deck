"""Regression coverage for deterministic Python commands embedded in recipes."""

import ast
import re
import subprocess
from pathlib import Path

import yaml


RECIPE_FILES = (
    Path("recipes/director-deck.yaml"),
    Path("recipes/director-deck-continue.yaml"),
)
SAFE_CONTEXT = {
    "prompt": "safe presentation prompt",
    "pptx_input": "fixtures/input.pptx",
    "html_input": "fixtures/input.html",
    "run_slug": "safe-run",
    "run_dir": "runs/safe-run",
    "_approval_message": "approved",
}
_CONTEXT_VARIABLE = re.compile(r"{{\s*([a-zA-Z_]\w*)\s*}}")
_PYTHON_HEREDOC = re.compile(
    r"(?ms)^[ \t]*python[ \t]+-[ \t]+<<'(?P<delimiter>[A-Z0-9_]+)'[^\n]*\n"
    r"(?P<payload>.*?)(?=^[ \t]*(?P=delimiter)[ \t]*$)"
)


def _load_bash_commands(recipe_path: Path) -> list[str]:
    recipe = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    return [
        step["command"]
        for stage in recipe["stages"]
        for step in stage["steps"]
        if step.get("type") == "bash"
    ]


def _substitute_safe_context(command: str) -> str:
    return _CONTEXT_VARIABLE.sub(
        lambda match: SAFE_CONTEXT.get(match.group(1), "safe-value"),
        command,
    )


def test_bash_commands_are_shell_syntax_valid_after_context_substitution():
    for recipe_path in RECIPE_FILES:
        for command in _load_bash_commands(recipe_path):
            rendered = _substitute_safe_context(command)
            result = subprocess.run(
                ["bash", "-n"],
                input=rendered,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, (
                f"{recipe_path} has invalid bash syntax:\n{result.stderr}"
            )


def test_all_deterministic_python_commands_use_parseable_quoted_heredocs():
    commands = [
        command
        for recipe_path in RECIPE_FILES
        for command in _load_bash_commands(recipe_path)
        if "python" in command
    ]
    payloads = [
        (recipe_path, match.group("payload"))
        for recipe_path in RECIPE_FILES
        for command in _load_bash_commands(recipe_path)
        for match in _PYTHON_HEREDOC.finditer(command)
    ]

    assert len(commands) == 9
    assert len(payloads) == 9
    assert all("python -c" not in command for command in commands)
    for recipe_path, payload in payloads:
        tree = ast.parse(payload, filename=str(recipe_path), feature_version=(3, 11))
        compile(tree, str(recipe_path), "exec")


def test_html_capture_has_no_direct_vlm_refinement_client():
    main_recipe = yaml.safe_load(RECIPE_FILES[0].read_text(encoding="utf-8"))

    assert "vlm_refine" not in main_recipe["context"]
    commands = "\n".join(_load_bash_commands(RECIPE_FILES[0]))
    assert "import openai" not in commands
    assert "chat.completions" not in commands