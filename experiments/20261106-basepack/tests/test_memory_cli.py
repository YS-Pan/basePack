import argparse
from hashlib import sha256
import os
import subprocess

import pytest

from basepack.memory.cli import _activate, dispatch, register_commands
from basepack.project.config import load_project_config
from basepack.project.init import init_project


def test_memory_activation_preserves_business_text_and_updates_one_local_entry(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    project = tmp_path / "中文 project"
    config = load_project_config(init_project(project, machine))
    instructions = project / ".basepack/instructions.md"
    original = instructions.read_text(encoding="utf-8")
    _activate(config)
    instructions.write_text(instructions.read_text(encoding="utf-8") + "\n业务尾注：需保留。\n", encoding="utf-8")
    _activate(config)
    updated = instructions.read_text(encoding="utf-8")
    assert updated.startswith(original.rstrip())
    assert updated.endswith("\n业务尾注：需保留。\n")
    assert updated.count("<!-- basepack-memory:start -->") == 1
    assert f"$basepackConfig = '{config.path}'" in updated
    assert "--config $basepackConfig memory brief" in updated
    assert "[记忆流程](<" in updated
    assert "memory.search_mode" in updated
    assert "`hybrid --literal`" in updated
    assert "`vector --literal` 明确拒绝" in updated
    assert "memory_dir/serve.ps1" in updated
    assert "logs/surreal.stderr.log" in updated


@pytest.mark.parametrize("markers", ["<!-- basepack-memory:start -->", "<!-- basepack-memory:end -->",
                                    "<!-- basepack-memory:end -->\n<!-- basepack-memory:start -->",
                                    "<!-- basepack-memory:start -->\n<!-- basepack-memory:start -->\n<!-- basepack-memory:end -->",
                                    "<!-- basepack-memory:start -->\n<!-- basepack-memory:end -->\n<!-- basepack-memory:end -->"])
def test_broken_generated_boundary_fails_before_overwriting_instructions(tmp_path, markers):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    project = tmp_path / "project"
    config = load_project_config(init_project(project, machine))
    instructions = project / ".basepack/instructions.md"
    text = "用户正文\n" + markers + "\n用户仍需的尾注\n"
    instructions.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        _activate(config)
    assert instructions.read_text(encoding="utf-8") == text


def _search_args(*options):
    parser = argparse.ArgumentParser()
    register_commands(parser.add_subparsers(dest="command"))
    return parser.parse_args(["memory", "search", "--text", "项目数据库", *options])


@pytest.mark.parametrize("configured, explicit, expected", [
    ("hybrid", None, "hybrid"), ("vector", None, "vector"),
    ("hybrid", "vector", "vector"), ("vector", "hybrid", "hybrid"),
    ("text", "vector", "vector"), (None, "hybrid", "hybrid"), ("typo", "hybrid", "hybrid"),
])
def test_search_uses_project_mode_and_explicit_override(tmp_path, monkeypatch, configured, explicit, expected):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    if configured is None:
        del config.raw["memory"]["search_mode"]
    else:
        config.raw["memory"]["search_mode"] = configured

    class Search:
        def __init__(self, config):
            pass

        def hybrid_search(self, *args, **kwargs):
            return "hybrid"

        def vector_search(self, *args, **kwargs):
            return "vector"

    monkeypatch.setattr("basepack.memory.store.Memory", Search)
    options = ["--mode", explicit] if explicit else []
    assert dispatch(_search_args(*options), config) == (expected, 0)


@pytest.mark.parametrize("configured, error", [(None, KeyError), ("typo", ValueError), ("text", ValueError)])
def test_default_search_requires_a_valid_explicit_project_setting(tmp_path, configured, error):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    if configured is None:
        del config.raw["memory"]["search_mode"]
    else:
        config.raw["memory"]["search_mode"] = configured
    with pytest.raises(error, match="search_mode"):
        dispatch(_search_args(), config)


def test_text_search_mode_is_not_a_cli_option():
    with pytest.raises(SystemExit) as error:
        _search_args("--mode", "text")
    assert error.value.code == 2


@pytest.mark.parametrize("explicit", [False, True])
def test_vector_search_rejects_literal_before_retrieving(tmp_path, monkeypatch, explicit):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    monkeypatch.setattr("basepack.memory.store.Memory.vector_search",
                        lambda *args, **kwargs: pytest.fail("vector search accepted --literal"))
    options = ["--mode", "vector"] if explicit else []
    with pytest.raises(ValueError, match="--literal requires --mode hybrid"):
        dispatch(_search_args("--literal", *options), config)


def test_hybrid_search_passes_literal_to_lexical_retrieval(tmp_path, monkeypatch):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    config.raw["memory"]["search_mode"] = "hybrid"
    calls = []

    def hybrid(self, text, **kwargs):
        calls.append((text, kwargs))
        return "matches"

    monkeypatch.setattr("basepack.memory.store.Memory.hybrid_search", hybrid)
    assert dispatch(_search_args("--literal"), config) == ("matches", 0)
    assert calls == [("项目数据库", {"scope": "", "limit": 12, "timeout": 600,
                                  "literal": True, "include_coverage": True})]


def _activation_bootstrap(config):
    text = (config.root / ".basepack/instructions.md").read_text(encoding="utf-8")
    section = text.split("<!-- basepack-memory:start -->", 1)[1].split("<!-- basepack-memory:end -->", 1)[0]
    command = section.split("```powershell\n", 1)[1].split("\n```", 1)[0]
    return command.split("& $basepackPython -X utf8 -m basepack --config $basepackConfig memory brief", 1)[0]


@pytest.mark.parametrize("password_file", [None, "relative", "absolute"])
def test_generated_bootstrap_reads_current_config_in_fresh_shell_from_other_cwd(tmp_path, password_file):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    project = tmp_path / "中文 user's project-🚀"
    config = load_project_config(init_project(project, machine, ".basepack/deep/config.toml"))
    _activate(config)
    bootstrap = _activation_bootstrap(config)
    secret = "  本地凭据 ' $pw 🚀  "
    config_text = config.path.read_text(encoding="utf-8").replace(".basepack/memory", ".basepack/新 memory")
    config_text = config_text.replace("password_env = 'BASEPACK_MEMORY_PASSWORD'", "password_env = 'BASEPACK_FRESH_TEST_PASSWORD'")
    expected_file = project / ".basepack/新 memory/password.txt"
    if password_file is not None:
        expected_file = (project / "secrets/密码.txt" if password_file == "relative" else tmp_path / "external 密码.txt")
        value = expected_file.relative_to(project).as_posix() if password_file == "relative" else expected_file.as_posix()
        config_text = config_text.replace("[memory]\n", f"[memory]\npassword_file = '{value}'\n")
    expected_file.parent.mkdir(parents=True, exist_ok=True)
    expected_file.write_text(secret, encoding="utf-8")
    config.path.write_text(config_text, encoding="utf-8")
    old_file = project / ".basepack/memory/password.txt"
    old_file.parent.mkdir(parents=True)
    old_file.write_text("obsolete secret", encoding="utf-8")
    check = ("& $basepackPython -X utf8 -c \"import hashlib,os,sys; "
             "assert hashlib.sha256(os.environ['BASEPACK_FRESH_TEST_PASSWORD'].encode()).hexdigest() == sys.argv[1]; "
             "print('loaded')\" '" + sha256(secret.encode()).hexdigest() + "'\n"
             "if ($LASTEXITCODE -ne 0) { throw 'Credential verification failed' }\n"
             "$basepackInfo.memory_dir\n")
    env = os.environ | {"BASEPACK_MEMORY_PASSWORD": "obsolete environment"}
    env.pop("BASEPACK_FRESH_TEST_PASSWORD", None)
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", bootstrap + check],
                            cwd=tmp_path.parent, env=env, capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["loaded", str(project / ".basepack/新 memory")]
    assert secret not in result.stdout + result.stderr


def test_generated_bootstrap_stops_before_memory_when_secret_file_is_missing(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    _activate(config)
    bootstrap = _activation_bootstrap(config)
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", bootstrap + "Write-Output 'continued'"],
                            cwd=tmp_path.parent, capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert result.returncode != 0
    assert "continued" not in result.stdout
    assert "password.txt" in result.stderr
