"""
Tests for per-skill terminal backend routing.

When a skill's SKILL.md frontmatter declares ``backend: <name>``, viewing
the skill records a per-task env override that flips subsequent terminal
and execute_code calls in that session to a Docker image configured under
``terminal.backends`` in ``~/.hermes/config.yaml``. These tests cover the
``register_task_skill_backend`` helper itself plus the override path
through ``_get_env_config``.
"""

from unittest.mock import patch

import pytest

from tools import terminal_tool


@pytest.fixture(autouse=True)
def _clean_overrides():
    """Snapshot/restore module-level state so tests don't leak."""
    before = dict(terminal_tool._task_env_overrides)
    terminal_tool._task_env_overrides.clear()
    yield
    terminal_tool._task_env_overrides.clear()
    terminal_tool._task_env_overrides.update(before)


def _stub_config(backends):
    """Patch hermes_cli.config.load_config to return the given backends map."""
    return patch(
        "hermes_cli.config.load_config",
        return_value={"terminal": {"backends": backends}},
    )


def _no_op_cleanup():
    """Stub cleanup_vm so tests don't try to tear down real containers."""
    return patch.object(terminal_tool, "cleanup_vm", autospec=True)


class TestRegisterTaskSkillBackend:
    def test_records_override_for_known_backend(self):
        with _stub_config({"office-worker": {"image": "test-image:latest"}}), _no_op_cleanup():
            ok = terminal_tool.register_task_skill_backend(
                "task-1", "office-worker", source="pptx/SKILL.md"
            )
        assert ok is True
        override = terminal_tool._task_env_overrides["task-1"]
        assert override["env_type"] == "docker"
        assert override["docker_image"] == "test-image:latest"
        assert override["skill_backend"] == "office-worker"

    def test_optional_fields_threaded_through(self):
        backends = {
            "office-worker": {
                "image": "img:1",
                "volumes": ["/host:/cont:ro"],
                "forward_env": ["FOO"],
                "env": {"BAR": "baz"},
                "cwd": "/work",
                "network": False,
            }
        }
        with _stub_config(backends), _no_op_cleanup():
            terminal_tool.register_task_skill_backend("t", "office-worker")
        ov = terminal_tool._task_env_overrides["t"]
        assert ov["docker_volumes"] == ["/host:/cont:ro"]
        assert ov["docker_forward_env"] == ["FOO"]
        assert ov["docker_env"] == {"BAR": "baz"}
        assert ov["cwd"] == "/work"
        assert ov["docker_network"] is False

    def test_network_default_omitted_when_unset(self):
        with _stub_config({"office-worker": {"image": "i:1"}}), _no_op_cleanup():
            terminal_tool.register_task_skill_backend("t", "office-worker")
        # Absent from override → _get_env_config falls back to its True default
        assert "docker_network" not in terminal_tool._task_env_overrides["t"]

    def test_unknown_backend_warns_and_returns_false(self, caplog):
        with _stub_config({"office-worker": {"image": "img:1"}}), _no_op_cleanup():
            ok = terminal_tool.register_task_skill_backend("t", "ghost-worker")
        assert ok is False
        assert "t" not in terminal_tool._task_env_overrides
        assert any("ghost-worker" in r.message for r in caplog.records)

    def test_empty_backend_no_op(self):
        with _stub_config({"x": {"image": "y"}}), _no_op_cleanup():
            assert terminal_tool.register_task_skill_backend("t", "") is False
        assert not terminal_tool._task_env_overrides

    def test_none_or_empty_task_id_falls_back_to_default(self):
        # Top-level agent calls skill_view with task_id=None; the override must
        # land under "default" so subsequent terminal calls (which share the
        # "default" container key per _resolve_container_task_id) pick it up.
        with _stub_config({"office-worker": {"image": "i:1"}}), _no_op_cleanup():
            assert terminal_tool.register_task_skill_backend(None, "office-worker") is True
        assert "default" in terminal_tool._task_env_overrides
        assert terminal_tool._task_env_overrides["default"]["docker_image"] == "i:1"

    def test_idempotent_skips_cleanup(self):
        with _stub_config({"w": {"image": "i:1"}}), _no_op_cleanup() as cleanup:
            terminal_tool.register_task_skill_backend("t", "w")
            cleanup.reset_mock()
            second = terminal_tool.register_task_skill_backend("t", "w")
        assert second is False
        cleanup.assert_not_called()

    def test_switching_backend_triggers_cleanup(self):
        backends = {
            "office-worker": {"image": "office:1"},
            "stock-worker": {"image": "stock:1"},
        }
        with _stub_config(backends), _no_op_cleanup() as cleanup:
            terminal_tool.register_task_skill_backend("t", "office-worker")
            cleanup.reset_mock()
            terminal_tool.register_task_skill_backend("t", "stock-worker")
        cleanup.assert_called_once_with("t")
        assert terminal_tool._task_env_overrides["t"]["docker_image"] == "stock:1"


class TestGetEnvConfigOverrides:
    def test_no_task_id_with_no_default_override_returns_global_default(self, monkeypatch):
        monkeypatch.delenv("TERMINAL_ENV", raising=False)
        cfg = terminal_tool._get_env_config()
        assert cfg["env_type"] == "local"

    def test_task_id_without_override_returns_global_default(self, monkeypatch):
        monkeypatch.delenv("TERMINAL_ENV", raising=False)
        cfg = terminal_tool._get_env_config("unknown-task")
        assert cfg["env_type"] == "local"

    def test_none_task_id_picks_up_default_override(self, monkeypatch):
        # Top-level agent calls _get_env_config(None); registering an override
        # under "default" must apply.
        monkeypatch.delenv("TERMINAL_ENV", raising=False)
        terminal_tool.register_task_env_overrides(
            "default", {"env_type": "docker", "docker_image": "img:default"}
        )
        cfg = terminal_tool._get_env_config(None)
        assert cfg["env_type"] == "docker"
        assert cfg["docker_image"] == "img:default"

    def test_override_flips_env_type_and_image(self, monkeypatch):
        monkeypatch.delenv("TERMINAL_ENV", raising=False)
        terminal_tool.register_task_env_overrides(
            "t",
            {
                "env_type": "docker",
                "docker_image": "custom:tag",
                "skill_backend": "office-worker",
            },
        )
        cfg = terminal_tool._get_env_config("t")
        assert cfg["env_type"] == "docker"
        assert cfg["docker_image"] == "custom:tag"

    def test_override_does_not_leak_to_other_task(self, monkeypatch):
        monkeypatch.delenv("TERMINAL_ENV", raising=False)
        terminal_tool.register_task_env_overrides(
            "t1", {"env_type": "docker", "docker_image": "custom:tag"}
        )
        cfg_other = terminal_tool._get_env_config("t2")
        assert cfg_other["env_type"] == "local"
        assert cfg_other["docker_image"] != "custom:tag"

    def test_override_volumes_appended_not_replaced(self, monkeypatch):
        # TERMINAL_DOCKER_VOLUMES is only parsed under the docker backend
        # (upstream gates the Docker-only env vars so a stale value can't
        # break a local terminal), so select it before asserting the append.
        monkeypatch.setenv("TERMINAL_ENV", "docker")
        monkeypatch.setenv("TERMINAL_DOCKER_VOLUMES", '["/base:/base"]')
        terminal_tool.register_task_env_overrides(
            "t", {"docker_volumes": ["/extra:/extra"]}
        )
        cfg = terminal_tool._get_env_config("t")
        assert "/base:/base" in cfg["docker_volumes"]
        assert "/extra:/extra" in cfg["docker_volumes"]

    def test_override_network_flag(self, monkeypatch):
        monkeypatch.delenv("TERMINAL_ENV", raising=False)
        terminal_tool.register_task_env_overrides("t", {"docker_network": False})
        assert terminal_tool._get_env_config("t")["docker_network"] is False
        assert terminal_tool._get_env_config(None)["docker_network"] is True
