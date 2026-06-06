"""
Tests for skill_view → register_task_skill_backend wiring.

When a skill's SKILL.md declares ``backend: <name>`` and ``skill_view`` is
called with a non-empty ``task_id``, the backend should be recorded as a
per-task env override. Skills without ``backend:``, or calls without a
``task_id``, must remain no-ops.
"""

import json
from unittest.mock import patch

import pytest


def _create_skill(tmp_path, name, *, backend=None):
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm_extra = f"backend: {backend}\n" if backend else ""
    (skill_dir / "SKILL.md").write_text(
        f"---\n"
        f"name: {name}\n"
        f"description: Test skill\n"
        f"{fm_extra}"
        f"---\n\n"
        f"# {name}\n\nbody\n"
    )
    return skill_dir


class TestSkillViewBackendRouting:
    def test_backend_in_frontmatter_invokes_helper(self, tmp_path, monkeypatch):
        _create_skill(tmp_path, "pptx-test", backend="office-worker")
        monkeypatch.setattr("tools.skills_tool.SKILLS_DIR", tmp_path)

        with patch(
            "tools.terminal_tool.register_task_skill_backend"
        ) as helper, patch("tools.skills_tool._secret_capture_callback", None):
            from tools.skills_tool import skill_view

            result = json.loads(skill_view(name="pptx-test", task_id="task-1"))

        assert result["success"] is True
        helper.assert_called_once()
        args, kwargs = helper.call_args
        assert args[0] == "task-1"
        assert args[1] == "office-worker"
        assert "pptx-test" in (kwargs.get("source") or "")

    def test_no_backend_field_does_not_call_helper(self, tmp_path, monkeypatch):
        _create_skill(tmp_path, "plain-test")
        monkeypatch.setattr("tools.skills_tool.SKILLS_DIR", tmp_path)

        with patch(
            "tools.terminal_tool.register_task_skill_backend"
        ) as helper, patch("tools.skills_tool._secret_capture_callback", None):
            from tools.skills_tool import skill_view

            json.loads(skill_view(name="plain-test", task_id="task-1"))

        helper.assert_not_called()

    def test_no_task_id_still_calls_helper_with_none(self, tmp_path, monkeypatch):
        # task_id=None at top-level agent → helper still fires; the helper
        # itself maps None to "default" so the override lands on the shared
        # gateway container.
        _create_skill(tmp_path, "pptx-test", backend="office-worker")
        monkeypatch.setattr("tools.skills_tool.SKILLS_DIR", tmp_path)

        with patch(
            "tools.terminal_tool.register_task_skill_backend"
        ) as helper, patch("tools.skills_tool._secret_capture_callback", None):
            from tools.skills_tool import skill_view

            json.loads(skill_view(name="pptx-test"))

        helper.assert_called_once()
        args, _ = helper.call_args
        assert args[0] is None
        assert args[1] == "office-worker"

    def test_helper_raising_does_not_break_skill_view(self, tmp_path, monkeypatch):
        _create_skill(tmp_path, "pptx-test", backend="office-worker")
        monkeypatch.setattr("tools.skills_tool.SKILLS_DIR", tmp_path)

        with patch(
            "tools.terminal_tool.register_task_skill_backend",
            side_effect=RuntimeError("simulated failure"),
        ), patch("tools.skills_tool._secret_capture_callback", None):
            from tools.skills_tool import skill_view

            result = json.loads(skill_view(name="pptx-test", task_id="task-1"))

        # skill_view must still return a valid response, not blow up.
        assert result["success"] is True
