"""Verify the memory graph and its native restore in two disposable SurrealKV databases."""

import argparse
from base64 import b64encode
from contextlib import contextmanager
import json
import os
from pathlib import Path
from secrets import token_hex
import shutil
import socket
import subprocess
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import Request, urlopen


NAMESPACE = "graph_example"
DATABASE = "memory"
USER = "example"
CLAIMS = {
    1: "Drift is below 0.20 mm.",
    2: "Under procedure 2 and condition X, drift is below 0.25 mm.",
}
REPORTS = {
    1: ("X: drift 0.12 mm. Y: drift 0.34 mm.", "Procedure 1 verified the instrument at 20 N."),
    2: ("X: drift 0.19 mm. Y: drift 0.40 mm.", "Procedure 2 verified the instrument at 10 N."),
}


@contextmanager
def database(executable, work, name, password, env):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        address = f"127.0.0.1:{reservation.getsockname()[1]}"
    endpoint = f"http://{address}"
    with (work / f"{name}.log").open("wb") as log:
        process = subprocess.Popen(
            [executable, "start", "--bind", address, "--username", USER, "--password", password,
             "--default-namespace", NAMESPACE, "--default-database", DATABASE, f"surrealkv:{name}"],
            cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            deadline = monotonic() + 15
            while process.poll() is None and monotonic() < deadline:
                try:
                    with urlopen(f"{endpoint}/health", timeout=1):
                        break
                except URLError:
                    sleep(0.1)
            else:
                raise RuntimeError((work / f"{name}.log").read_text(encoding="utf-8"))
            yield endpoint
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)


def query(endpoint, password, sql, *, error=None):
    credentials = b64encode(f"{USER}:{password}".encode()).decode()
    request = Request(f"{endpoint}/sql", data=sql.encode(), headers={
        "Authorization": f"Basic {credentials}", "Accept": "application/json",
        "Surreal-NS": NAMESPACE, "Surreal-DB": DATABASE,
    })
    with urlopen(request, timeout=10) as response:
        statements = json.load(response)
    failures = [statement["result"] for statement in statements if statement["status"] == "ERR"]
    if error is not None:
        if not any(error in message for message in failures):
            raise AssertionError(f"Expected SQL error containing {error!r}, got {statements!r}")
    elif failures:
        raise RuntimeError(f"SurrealQL failed: {failures}\n{sql}")
    return [statement["result"] for statement in statements]


def expect(actual, expected):
    if actual != expected:
        raise AssertionError(f"Expected {expected!r}, got {actual!r}")


def edge(name, source, target, kind, *, condition=None, line=None):
    fields = [f"id: graph_edge:{name}", f"in: {source}", f"out: {target}", f"type: '{kind}'"]
    if condition is not None:
        fields.append(f"condition: {json.dumps(condition)}")
    if line is not None:
        fields.append(f"line: {line}")
    return "INSERT RELATION INTO graph_edge { " + ", ".join(fields) + " };"


def publish(revision):
    claim = f"graph_version:claim_v{revision}"
    result = f"graph_version:result_v{revision}"
    snapshot = f"graph_snapshot:report_v{revision}"
    support = f"graph_edge:support_v{revision}"
    result_text, method = REPORTS[revision]
    report = "Actuator acceptance report\n" + result_text + "\n" + method + "\n"
    versions = {"claim": claim, "result": result, "report": snapshot, "support": support}
    statements = ["BEGIN TRANSACTION;"]
    if revision == 1:
        statements += [f"CREATE graph_object:{name};" for name in versions]
        statements.append("CREATE graph_version:section SET text = 'Actuator acceptance';")
    statements += [
        f"CREATE {claim} SET text = {json.dumps(CLAIMS[revision])};",
        f"CREATE {result} SET text = {json.dumps(result_text)};",
        f"CREATE {snapshot} SET path = 'report.txt', text = {json.dumps(report)};",
        edge(f"part_v{revision}", result, "graph_version:section", "part_of"),
        edge(f"source_v{revision}", result, snapshot, "from_snapshot", line=2),
        edge(f"support_v{revision}", result, claim, "supports", condition="X"),
        edge(f"claim_basis_v{revision}", claim, result, "has_basis"),
        edge(f"support_basis_v{revision}", support, snapshot, "has_basis", line=3),
    ]
    if revision == 1:
        statements.append(edge("contradiction", result, claim, "contradicts", condition="Y"))
    for name, version in versions.items():
        statements.append(edge(f"{name}_version_v{revision}", version, f"graph_object:{name}", "version_of"))
        statements.append(f"UPDATE graph_object:{name} SET head = {version};")
    statements += [f"CREATE graph_publication:release_v{revision} SET claim = {claim};", "COMMIT TRANSACTION;"]
    return "\n".join(statements)


def check_revision(endpoint, password, revision):
    result = f"graph_version:result_v{revision}"
    claim = f"graph_version:claim_v{revision}"
    support = f"graph_edge:support_v{revision}"
    snapshot = f"graph_snapshot:report_v{revision}"
    outgoing, filtered, incoming, reverse, wrong_condition, wrong_direction = query(endpoint, password, f"""
        RETURN {result}->graph_edge.{{id, in, out}};
        RETURN {result}->(graph_edge WHERE type = 'supports' AND condition = 'X').{{id, in, out}};
        RETURN {claim}<-graph_edge.{{id, in, out}};
        RETURN {claim}<-(graph_edge WHERE type = 'supports' AND condition = 'X').{{id, in, out}};
        RETURN {result}->(graph_edge WHERE type = 'supports' AND condition = 'Y');
        RETURN {claim}->(graph_edge WHERE type = 'supports');
    """)
    expected_edge = {"id": support, "in": result, "out": claim}
    for adjacent in (outgoing, filtered, incoming, reverse):
        expect([item for item in adjacent if item["id"] == support], [expected_edge])
    expect(filtered, [expected_edge])
    expect(reverse, [expected_edge])
    expect(wrong_condition, [])
    expect(wrong_direction, [])
    if revision == 1:
        [contradiction] = query(endpoint, password, f"""
            RETURN {result}->(graph_edge WHERE type = 'contradicts' AND condition = 'Y').{{id, in, out}};
        """)
        expect(contradiction, [{"id": "graph_edge:contradiction", "in": result, "out": claim}])
        expect(contradiction[0] in outgoing and contradiction[0] in incoming, True)

    parent, basis, location, edge_basis, reverse_basis, stored, report, exact_claim = query(endpoint, password, f"""
        RETURN {result}->(graph_edge WHERE type = 'part_of').out;
        RETURN {claim}->(graph_edge WHERE type = 'has_basis')->graph_version.{{id, text}};
        RETURN {result}->(graph_edge WHERE type = 'from_snapshot').{{out, line}};
        RETURN {support}->(graph_edge WHERE type = 'has_basis').{{id, out, line}};
        RETURN {snapshot}<-(graph_edge WHERE type = 'has_basis').{{id, in, line}};
        SELECT id, in, out, type, condition FROM ONLY {support};
        RETURN {support}->(graph_edge WHERE type = 'has_basis')->graph_snapshot.{{id, path, text}};
        SELECT text FROM ONLY {claim};
    """)
    expect(parent, ["graph_version:section"])
    expect(basis, [{"id": result, "text": REPORTS[revision][0]}])
    expect(location, [{"out": snapshot, "line": 2}])
    basis_id = f"graph_edge:support_basis_v{revision}"
    expect(edge_basis, [{"id": basis_id, "out": snapshot, "line": 3}])
    expect(reverse_basis, [{"id": basis_id, "in": support, "line": 3}])
    expect(stored, {**expected_edge, "type": "supports", "condition": "X"})
    expect(exact_claim["text"], CLAIMS[revision])
    [original] = report
    expect(original["id"], snapshot)
    expect(original["path"], "report.txt")
    lines = original["text"].splitlines()
    expect((lines[location[0]["line"] - 1], lines[edge_basis[0]["line"] - 1]), REPORTS[revision])


def check_history(endpoint, password):
    check_revision(endpoint, password, 1)
    check_revision(endpoint, password, 2)
    heads, history, receipts = query(endpoint, password, """
        SELECT id, head FROM graph_object ORDER BY id;
        RETURN graph_object:support<-(graph_edge WHERE type = 'version_of').in;
        SELECT id, claim FROM graph_publication ORDER BY id;
    """)
    expect({item["id"]: item["head"] for item in heads}, {
        "graph_object:claim": "graph_version:claim_v2", "graph_object:result": "graph_version:result_v2",
        "graph_object:report": "graph_snapshot:report_v2", "graph_object:support": "graph_edge:support_v2",
    })
    expect(sorted(history), ["graph_edge:support_v1", "graph_edge:support_v2"])
    expect(receipts, [
        {"id": f"graph_publication:release_v{revision}", "claim": f"graph_version:claim_v{revision}"}
        for revision in CLAIMS
    ])


STATE = """
    SELECT * FROM graph_object ORDER BY id;
    SELECT * FROM graph_version ORDER BY id;
    SELECT * FROM graph_snapshot ORDER BY id;
    SELECT * FROM graph_edge ORDER BY id;
    SELECT * FROM graph_publication ORDER BY id;
"""


def check_failed_writes(endpoint, password):
    before = query(endpoint, password, STATE)
    query(endpoint, password, f"""
        BEGIN TRANSACTION;
        CREATE graph_version:uncommitted SET text = 'This version must never be visible';
        UPDATE graph_object:claim SET head = graph_version:uncommitted;
        {edge("uncommitted", "graph_version:result_v2", "graph_version:uncommitted", "supports")}
        CREATE graph_publication:uncommitted SET claim = graph_version:uncommitted;
        {edge("failed_basis", "graph_edge:uncommitted", "graph_snapshot:missing", "has_basis")}
        COMMIT TRANSACTION;
    """, error="graph_snapshot:missing")
    query(endpoint, password,
          edge("support_v1", "graph_version:result_v1", "graph_version:claim_v1", "supports", condition="Y"),
          error="already exists")
    expect(query(endpoint, password, STATE), before)
    return before


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surreal", default="surreal", help="Path to the SurrealDB CLI")
    parser.add_argument("--work-dir", type=Path, default=Path("tmp"), help="Parent of disposable files")
    args = parser.parse_args()
    executable = shutil.which(args.surreal)
    if not executable:
        parser.error(f"SurrealDB CLI not found: {args.surreal}")
    executable = str(Path(executable).resolve())
    schema = Path(__file__).with_suffix(".surql").read_text(encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("SURREAL_")}
    print(subprocess.check_output([executable, "version"], env=env, text=True).strip(), flush=True)
    password = token_hex(16)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="memory-graph-", dir=args.work_dir.resolve()) as temporary:
        work = Path(temporary)
        dump = work / "graph.surql"
        cli = ["--namespace", NAMESPACE, "--database", DATABASE, "--username", USER, "--password", password]
        with database(executable, work, "source", password, env) as source:
            query(source, password, schema)
            query(source, password, publish(1))
            check_revision(source, password, 1)
            query(source, password, publish(2))
            expected_state = check_failed_writes(source, password)
            check_history(source, password)
            print("Source graph: directional edge IDs, evidence, history and failed writes verified.", flush=True)
            subprocess.run([executable, "export", "--endpoint", source, *cli, str(dump)],
                           cwd=work, env=env, check=True, timeout=30)
        with database(executable, work, "restored", password, env) as restored:
            [info] = query(restored, password, "INFO FOR DB;")
            expect(info["tables"], {})
            subprocess.run([executable, "import", "--endpoint", restored, *cli, str(dump)],
                           cwd=work, env=env, check=True, timeout=30)
            expect(check_failed_writes(restored, password), expected_state)
            check_history(restored, password)
            print("Independent restore: identical records, native traversals and write constraints verified.", flush=True)


if __name__ == "__main__":
    main()
