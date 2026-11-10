import json
from pathlib import Path
import subprocess
import sys

import pytest

import basepack
from basepack.project.config import describe, installation, load_machine_config, load_project_config
from basepack.project.doctor import doctor
from basepack.project.init import init_project, template


def test_two_projects_and_subdirectory_config(tmp_path, monkeypatch):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n[shared]\nstate_dir='state/basepack'\n", encoding="utf-8")
    projects = [tmp_path / "项目 A", tmp_path / "项目 B"]
    configs = [init_project(root, machine, ".basepack/config/deep/basepack.toml") for root in projects]
    monkeypatch.chdir(tmp_path.parent)
    loaded = [load_project_config(path) for path in configs]
    assert [config.root for config in loaded] == projects
    assert loaded[0].machine_config == loaded[1].machine_config
    assert loaded[0].memory_dir != loaded[1].memory_dir
    assert loaded[0].jobs_dir != loaded[1].jobs_dir
    assert loaded[0].raw["schema_version"] == 2
    assert loaded[0].raw["memory"]["project_id"] != loaded[1].raw["memory"]["project_id"]
    assert "resources" not in loaded[0].raw
    assert describe(loaded[0])["jobs_dir"] == str(projects[0] / ".basepack/jobs")
    assert loaded[0].machine.state_dir == tmp_path / "state/basepack"
    assert ".basepack/instructions.md" in (projects[0] / "AGENTS.md").read_text(encoding="utf-8")
    instructions = (projects[0] / ".basepack/instructions.md").read_text(encoding="utf-8")
    assert ".basepack/config/deep/basepack.toml" in instructions
    assert sys.executable in instructions
    assert "config ai --purpose retrieval" in instructions
    assert "config ai --tier tier2" in instructions
    assert "gpt-6" not in instructions
    assert (projects[0] / ".gitignore").read_text(encoding="utf-8") == "/.basepack/\n"
    assert not (projects[0] / ".basepack/memory").exists()
    assert not (projects[0] / ".basepack/jobs").exists()
    with pytest.raises(FileExistsError):
        init_project(projects[0], machine, ".basepack/config/deep/basepack.toml")
    with pytest.raises(FileExistsError):
        init_project(projects[0], machine, ".basepack/second.toml")


def test_init_preserves_existing_project_instructions(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    root = tmp_path / "project"
    root.mkdir()
    (root / "AGENTS.md").write_text("# Business\nKeep original instructions.\n"
                                  "<!-- basepack:start -->\nOld generated entry.\n<!-- basepack:end -->\n"
                                  "Keep following instructions.\n", encoding="utf-8")
    (root / ".gitignore").write_text("/original/\n", encoding="utf-8")
    path = init_project(root, machine)
    assert path == root / ".basepack/config.toml"
    assert load_project_config(path).root == root
    assert (root / "AGENTS.md").read_text(encoding="utf-8").startswith("# Business\nKeep original instructions.")
    assert (root / "AGENTS.md").read_text(encoding="utf-8").endswith("Keep following instructions.\n")
    assert "Old generated entry." not in (root / "AGENTS.md").read_text(encoding="utf-8")
    assert (root / ".gitignore").read_text(encoding="utf-8").startswith("/original/\n")
    assert "[embedding]" in template("machine.toml")
    assert "gpu_memory_mib" in template("machine.toml")
    assert "[budget]" not in template("machine.toml")


@pytest.mark.parametrize("markers", ["<!-- basepack:start -->", "<!-- basepack:end -->",
                                    "<!-- basepack:end -->\r\n<!-- basepack:start -->",
                                    "<!-- basepack:start -->\r\n<!-- basepack:start -->\r\n<!-- basepack:end -->",
                                    "<!-- basepack:start -->\r\n<!-- basepack:end -->\r\n<!-- basepack:end -->"])
def test_init_rejects_broken_host_entry_without_writing_files(tmp_path, markers):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    root = tmp_path / "project"
    root.mkdir()
    agents = root / "AGENTS.md"
    original = ("# Business\r\nKeep original instructions.\r\n"
                + markers + "\r\nKeep following instructions.\r\n").encode("utf-8")
    agents.write_bytes(original)
    with pytest.raises(ValueError):
        init_project(root, machine)
    assert agents.read_bytes() == original
    assert not (root / ".basepack/config.toml").exists()
    assert not (root / ".basepack/instructions.md").exists()
    assert not (root / ".gitignore").exists()
    agents.write_text("# Business\nKeep original instructions.\n", encoding="utf-8")
    assert load_project_config(init_project(root, machine)).root == root


def test_init_round_trips_nonbmp_paths(tmp_path, monkeypatch):
    machine = tmp_path / "machine-🚀.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    root = tmp_path / "project-🚀"
    python = tmp_path / "python-🚀" / "python.exe"
    monkeypatch.setattr(sys, "executable", str(python))
    path = init_project(root, machine, ".basepack/config-🚀/basepack.toml")
    config = load_project_config(path)
    assert config.python == python
    assert config.machine_config == machine
    assert config.root == root


def test_init_config_with_quote_is_a_valid_powershell_argument(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    root = tmp_path / "project"
    config_name = ".basepack/user's.toml"
    path = init_project(root, machine, config_name)
    assert load_project_config(path).root == root
    instructions = (root / ".basepack/instructions.md").read_text(encoding="utf-8")
    command = instructions.split("```powershell\n", 1)[1].split("\n```", 1)[0]
    parse = """$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseInput([Console]::In.ReadToEnd(), [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$ast.EndBlock.Statements[0].PipelineElements[0].CommandElements[4].Value
"""
    argument = subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", parse],
                                       input=command, text=True, timeout=10).strip()
    assert argument == config_name


def test_init_config_cannot_overwrite_instructions(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    root = tmp_path / "project"
    with pytest.raises(ValueError, match="instructions.md"):
        init_project(root, machine, ".basepack/instructions.md")
    assert not root.exists()


@pytest.mark.parametrize("target", ["../other", "other"])
def test_project_data_stays_in_managed_directory(tmp_path, target):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    path = init_project(tmp_path / "project", machine)
    path.write_text(path.read_text(encoding="utf-8").replace(".basepack/memory", target), encoding="utf-8")
    config = load_project_config(path)
    with pytest.raises(ValueError, match="inside"):
        config.memory_dir


@pytest.mark.parametrize("name", ["basepack.toml", "config/basepack.toml", ".basepack/../outside.toml"])
def test_init_requires_config_under_basepack(tmp_path, name):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    with pytest.raises(ValueError, match=".basepack"):
        init_project(tmp_path / "project", machine, name)


def test_embedding_only_configuration_has_no_other_facility_dependencies(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n[embedding]\nmodel_root='model'\n", encoding="utf-8")
    project = tmp_path / "project.toml"
    project.write_text("schema_version=2\n[runtime]\npython=" + json.dumps(sys.executable)
                       + "\nmachine_config=" + json.dumps(str(machine))
                       + "\n[project]\nroot='.'\n", encoding="utf-8")
    config = load_project_config(project)
    assert config.machine_config == load_machine_config(machine).path
    result = describe(config)
    assert result["machine_paths"] == {"embedding": {"model_root": str(tmp_path / "model")}}
    assert "memory_dir" not in result
    assert "jobs_dir" not in result
    assert "ai" not in result
    with pytest.raises(KeyError, match="memory"):
        config.memory_dir
    with pytest.raises(KeyError, match="jobs"):
        config.jobs_dir


def test_package_root_and_installed_template_anchor(tmp_path, monkeypatch):
    assert basepack.__version__ == installation()["version"]
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    package = Path(basepack.__file__).resolve().parent
    monkeypatch.setattr("basepack.project.doctor.subprocess.check_output", lambda *args, **kwargs: str(package / "__init__.py"))
    result = doctor(config, "core")
    assert Path(installation()["package_dir"]) == package
    assert Path(result["checks"]["package"]) == package
    assert Path(result["checks"]["templates"]) == package / "project/templates"
    for name in ("project.toml", "machine.toml", "agents-snippet.md", "instructions.md"):
        assert template(name)


def test_project_and_machine_schema_are_checked_separately(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_machine_config(machine)
    machine.write_text("schema_version=1\n", encoding="utf-8")
    path = init_project(tmp_path / "project", machine)
    assert load_project_config(path).machine.raw["schema_version"] == 1
    path.write_text(path.read_text(encoding="utf-8").replace("schema_version = 2", "schema_version = 1"), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_project_config(path)


@pytest.fixture
def ai_config(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    return load_project_config(init_project(tmp_path / "project", machine))


def _config_cli(config, *args):
    return subprocess.run([sys.executable, "-m", "basepack", "--config", str(config.path), "config", *args],
                          capture_output=True, text=True, encoding="utf-8", timeout=10)


def test_init_contains_project_ai_mapping(ai_config):
    assert ai_config.raw["ai"] == {
        "default_tier": "tier3", "retrieval_tier": "tier1", "tiers": {
            "tier1": {"model": "gpt-6-luna", "reasoning_effort": "max"},
            "tier2": {"model": "gpt-6.1-terra", "reasoning_effort": "ultra"},
            "tier3": {"model": "gpt-6.1-sol", "reasoning_effort": "ultra"},
            "tier4": {"model": "gpt-6-astra", "reasoning_effort": "ultra"},
        },
    }
    assert describe(ai_config)["ai"] == ai_config.raw["ai"]


@pytest.mark.parametrize("options, tier", [({}, "tier3"), ({"purpose": "task"}, "tier3"),
                                          ({"purpose": "retrieval"}, "tier1"), ({"tier": "tier2"}, "tier2")])
def test_ai_resolves_project_defaults_and_explicit_tier(ai_config, options, tier):
    assert ai_config.resolve_ai(**options) == {"tier": tier, **ai_config.raw["ai"]["tiers"][tier]}


def test_ai_mapping_edits_are_used_on_next_resolution(ai_config):
    text = ai_config.path.read_text(encoding="utf-8")
    text = text.replace("default_tier = 'tier3'", "default_tier = 'tier2'")
    text = text.replace("retrieval_tier = 'tier1'", "retrieval_tier = 'tier4'")
    text = text.replace("model = 'gpt-6.1-terra'\nreasoning_effort = 'ultra'",
                        "model = 'project-model'\nreasoning_effort = 'high'")
    ai_config.path.write_text(text, encoding="utf-8")
    config = load_project_config(ai_config.path)
    expected = {"tier": "tier2", "model": "project-model", "reasoning_effort": "high"}
    assert config.resolve_ai() == expected
    assert config.resolve_ai(purpose="retrieval")["tier"] == "tier4"
    result = _config_cli(config, "ai")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == expected


@pytest.mark.parametrize("path, options", [(["ai"], {}), (["ai", "default_tier"], {}),
                                         (["ai", "retrieval_tier"], {"purpose": "retrieval"}),
                                         (["ai", "tiers"], {}), (["ai", "tiers", "tier3"], {}),
                                         (["ai", "tiers", "tier3", "model"], {}),
                                         (["ai", "tiers", "tier3", "reasoning_effort"], {})])
def test_ai_missing_configuration_raises_original_key_error(ai_config, path, options):
    table = ai_config.raw
    for key in path[:-1]:
        table = table[key]
    del table[path[-1]]
    with pytest.raises(KeyError) as error:
        ai_config.resolve_ai(**options)
    assert error.value.args == (path[-1],)
    describe(ai_config)


def test_explicit_ai_tier_does_not_require_purpose_defaults(ai_config):
    del ai_config.raw["ai"]["default_tier"]
    del ai_config.raw["ai"]["retrieval_tier"]
    assert ai_config.resolve_ai(tier="tier2") == {"tier": "tier2", **ai_config.raw["ai"]["tiers"]["tier2"]}


@pytest.mark.parametrize("args, tier", [([], "tier3"), (["--purpose", "task"], "tier3"),
                                       (["--purpose", "retrieval"], "tier1"), (["--tier", "tier2"], "tier2")])
def test_config_ai_cli(ai_config, args, tier):
    result = _config_cli(ai_config, "ai", *args)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"tier": tier, **ai_config.raw["ai"]["tiers"][tier]}


def test_config_ai_cli_purpose_and_tier_are_mutually_exclusive(ai_config):
    result = _config_cli(ai_config, "ai", "--purpose", "retrieval", "--tier", "tier2")
    assert result.returncode == 2
    assert "not allowed with argument" in result.stderr


def test_config_show_cli_includes_project_ai_mapping(ai_config):
    result = _config_cli(ai_config, "show")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ai"] == ai_config.raw["ai"]


def test_legacy_project_resource_paths_do_not_require_ai(tmp_path):
    from basepack.embedding.client import EmbeddingClient
    from basepack.jobs import CondorClient

    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n[embedding]\nendpoint='http://127.0.0.1:18081/'\nmodel_root='model'\n"
                       "[htcondor]\nbin_dir='bin'\nconfig_file='native.conf'\n", encoding="utf-8")
    project = tmp_path / "project.toml"
    project.write_text("schema_version=2\n[runtime]\npython=" + json.dumps(sys.executable)
                       + "\nmachine_config=" + json.dumps(str(machine))
                       + "\n[project]\nroot='.'\n[jobs]\njobs_dir='.basepack/jobs'\n", encoding="utf-8")
    config = load_project_config(project)
    assert "ai" not in describe(config)
    assert EmbeddingClient(config.machine).endpoint == "http://127.0.0.1:18081"
    jobs = CondorClient(config)
    assert jobs.bin_dir == tmp_path / "bin"
    assert jobs.env["CONDOR_CONFIG"] == str(tmp_path / "native.conf")
    assert jobs.config.jobs_dir == tmp_path / ".basepack/jobs"
    with pytest.raises(KeyError, match="ai"):
        config.resolve_ai()
