"""Evaluate the shipped site policy with Condor itself, without a schedd."""

import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


@pytest.fixture
def policy(tmp_path):
    search_path = os.environ.get("BASEPACK_TEST_CONDOR_BIN", os.environ.get("PATH", ""))
    tools = {name: shutil.which(name, path=search_path)
             for name in ("condor_config_val", "condor_transform_ads")}
    if not all(tools.values()):
        pytest.skip("Condor tools require PATH or BASEPACK_TEST_CONDOR_BIN")
    examples = Path(__file__).resolve().parents[1] / "examples" / "condor"
    root = tmp_path / "condor.conf"
    root.write_text(
        "LOCAL_CONFIG_FILE =\nLOCAL_CONFIG_DIR =\nSTART = true\n"
        "JOB_TRANSFORM_NAMES = Existing\n"
        "JOB_TRANSFORM_Existing @=end\n SET ExistingTransform true\n@end\n"
        "JOB_TRANSFORM_Check @=end\n EVALSET Matches Requirements\n@end\n"
        "SUBMIT_REQUIREMENT_NAMES = Existing\nSUBMIT_REQUIREMENT_Existing = true\n"
        f"include : {(examples / '60_resources.conf').as_posix()}\n"
        f"include : {(examples / '70_job_transforms.conf').as_posix()}\n",
        encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("_CONDOR_")}
    env["CONDOR_CONFIG"] = str(root)

    def run(name, *args):
        result = subprocess.run([tools[name], *map(str, args)], env=env,
                                capture_output=True, text=True, timeout=20)
        assert not result.stderr, result
        return result

    def config(name):
        result = run("condor_config_val", name)
        assert result.returncode == 0, result
        return result.stdout.strip()

    version = run("condor_config_val", "-version")
    assert version.returncode == 0, version
    # This exact upstream build returns ApplyTransforms' success count from main.
    known_exit_one = re.search(r"\$CondorVersion: 25\.4\.0 .* GitSHA: 6c530282 \$", version.stdout)
    serial = itertools.count()

    def transform(ads, *, names=None, rules=None):
        prefix = tmp_path / str(next(serial))
        source, output = prefix.with_suffix(".ads"), prefix.with_suffix(".json")
        source.write_text(ads, encoding="utf-8")
        args = ["-jobtransforms", names] if names else ["-rules", rules]
        result = run("condor_transform_ads", *args, "-in:long", source,
                     "-out:json", output)
        assert result.returncode == 0 or (known_exit_one and result.returncode == 1), result
        return json.loads(output.read_text(encoding="utf-8"))

    return config, transform, tmp_path


def test_site_transform_preserves_matching_and_other_admin_rules(policy):
    config, transform, _ = policy
    assert config("JOB_TRANSFORM_NAMES").split() == ["Existing", "ReserveGPUMemory"]
    assert config("SUBMIT_REQUIREMENT_NAMES").split() == [
        "Existing", "SingleGPU", "PositiveGPUMemory", "GPUMemoryCapacity"]
    pool = int(config("MACHINE_RESOURCE_GPUMemoryMiB"))
    common = ('JobUniverse = 5\nRequestGPUs = 1\nGPUsMinMemory = 3000\n'
              'RequireGPUs = Capability >= 8\n'
              'Requirements = TARGET.Arch == "X86_64" && '
              'countMatches(MY.RequireGPUs, TARGET.AvailableGPUs) >= RequestGPUs\n')
    ads = "\n".join(common + f'TARGET = [Arch = "{arch}"; GPUMemoryMiB = {memory}; '
                    f'AvailableGPUs = {{[Capability = {capability}]}}]\n'
                    for arch, memory, capability in [
                        ("X86_64", 3000, 8), ("X86_64", 2999, 8),
                        ("OTHER", 3000, 8), ("X86_64", 3000, 7)])
    ads += ('\nJobUniverse = 5\nRequestGPUs = 1\nRequirements = true\n'
            '\nJobUniverse = 5\nRequestCpus = 1\nRequirements = true\n')
    before = transform(ads, names="Existing")
    after = transform(ads, names=config("JOB_TRANSFORM_NAMES"))
    assert all(ad["ExistingTransform"] is True for ad in after)
    assert [ad["RequestGPUMemoryMiB"] for ad in after[:5]] == [3000] * 4 + [pool]
    assert "RequestGPUMemoryMiB" not in after[5]
    assert after[5]["Requirements"] == before[5]["Requirements"]
    assert all(new["RequireGPUs"] == old["RequireGPUs"]
               for old, new in zip(before[:4], after[:4]))
    evaluated = transform(ads, names=config("JOB_TRANSFORM_NAMES") + " Check")
    assert [ad["Matches"] for ad in evaluated[:4]] == [True, False, False, False]


def test_submit_requirements_evaluate_standard_inputs_in_job_scope(policy):
    config, transform, tmp_path = policy
    names = config("SUBMIT_REQUIREMENT_NAMES").split()
    rules = tmp_path / "requirements.rules"
    rules.write_text("\n".join(
        f"EVALSET Pass{name} {config('SUBMIT_REQUIREMENT_' + name)}"
        for name in names) + "\n" + "\n".join(
        f"EVALSET Reason{name} {config('SUBMIT_REQUIREMENT_' + name + '_REASON')}"
        for name in names if name != "Existing") + "\n", encoding="utf-8")
    pool = int(config("MACHINE_RESOURCE_GPUMemoryMiB"))
    cases = [
        ("positive", "3000", 1, None), ("omitted", None, 1, None),
        ("zero", "0", 1, "PositiveGPUMemory"),
        ("negative", "-1", 1, "PositiveGPUMemory"),
        ("undefined", "undefined", 1, "PositiveGPUMemory"),
        ("unresolved", "Unknown / 2", 1, "PositiveGPUMemory"),
        ("overpool", str(pool + 1), 1, "GPUMemoryCapacity"),
        ("multigpu", "1000", 2, "SingleGPU"),
        ("cpu", "undefined", 0, None),
    ]
    ads = "\n\n".join(
        f'Case = "{case}"\nJOB = [JobUniverse = 5; RequestGPUs = {gpus}'
        + (f"; GPUsMinMemory = {memory}" if memory is not None else "") + "]"
        for case, memory, gpus, _ in cases)
    evaluated = transform(ads, rules=rules)
    assert len(evaluated) == len(cases)
    for ad, (case, _, _, rejection) in zip(evaluated, cases):
        assert ad["Case"] == case
        assert ad["PassExisting"] is True
        if rejection is None:
            assert all(ad["Pass" + name] is True for name in names), ad
        else:
            assert ad["Pass" + rejection] is False, ad
            parameter = "request_gpus" if rejection == "SingleGPU" else "gpus_minimum_memory"
            assert parameter in ad["Reason" + rejection]
