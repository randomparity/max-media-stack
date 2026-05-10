from __future__ import annotations

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATE_CORPUS = REPO_ROOT / "scripts" / "generate-test-corpus"
INSPECT_LOGS = REPO_ROOT / "scripts" / "mms-log-inspect"


def run_command(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        check=False,
        env=command_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def write_policy(path: Path) -> None:
    policy = {
        "name": "functional-test-policy",
        "description": "Detect common container log failures.",
        "window_minutes": 60,
        "rules": [
            {
                "id": "storage-full",
                "severity": "critical",
                "description": "Storage exhaustion blocks writes.",
                "service": "*",
                "patterns": ["no space left on device", "ENOSPC"],
                "threshold": 1,
            },
            {
                "id": "auth-failure",
                "severity": "warning",
                "description": "Repeated authentication failures.",
                "service": "*",
                "patterns": ["authentication failed", "invalid api key"],
                "threshold": 2,
            },
            {
                "id": "application-error",
                "severity": "warning",
                "description": "Application error or exception.",
                "service": "*",
                "patterns": ["\\berror\\b", "exception", "fatal"],
                "threshold": 2,
            },
        ],
    }
    path.write_text(json.dumps(policy), encoding="utf-8")


def write_notification_policy(path: Path, provider: str = "discord") -> None:
    policy = {
        "name": "functional-notification-policy",
        "description": "Detect common failures and notify operators.",
        "window_minutes": 60,
        "notifications": [
            {
                "id": f"ops-{provider}",
                "provider": provider,
                "webhook_url_env": "MMS_TEST_WEBHOOK_URL",
                "min_severity": "warning",
            }
        ],
        "rules": [
            {
                "id": "storage-full",
                "severity": "critical",
                "description": "Storage exhaustion blocks writes.",
                "service": "*",
                "patterns": ["no space left on device", "ENOSPC"],
                "threshold": 1,
            }
        ],
    }
    path.write_text(json.dumps(policy), encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class LokiHandler(BaseHTTPRequestHandler):
    requested_query = ""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        LokiHandler.requested_query = params.get("query", [""])[0]
        payload = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {
                            "service_name": "radarr",
                            "unit": "radarr.service",
                        },
                        "values": [
                            ["1770000000000000000", "fatal import exception"],
                            ["1770000000500000000", "error syncing release metadata"],
                            ["1770000001000000000", "no space left on device"],
                        ],
                    }
                ],
            },
        }
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


class WebhookHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, object]] = []

    def do_POST(self) -> None:  # noqa: N802
        body = self.rfile.read(int(self.headers["Content-Length"]))
        WebhookHandler.requests.append(
            {
                "path": self.path,
                "content_type": self.headers.get("Content-Type"),
                "payload": json.loads(body.decode()),
            }
        )
        self.send_response(204)
        self.end_headers()

    def log_message(self, _format: str, *_args: object) -> None:
        return


def loki_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), LokiHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}"


def webhook_server() -> tuple[ThreadingHTTPServer, str]:
    WebhookHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), WebhookHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}/webhook"


def test_clean_corpus_has_no_findings(tmp_path: Path) -> None:
    corpus = tmp_path / "clean.jsonl"
    policy = tmp_path / "policy.json"
    report = tmp_path / "report.json"
    write_policy(policy)

    generated = run_command(
        str(GENERATE_CORPUS),
        "--scenario",
        "clean",
        "--entries",
        "24",
        "--output",
        str(corpus),
    )
    assert generated.returncode == 0, generated.stderr

    inspected = run_command(
        str(INSPECT_LOGS),
        "--input-jsonl",
        str(corpus),
        "--policy",
        str(policy),
        "--output-json",
        str(report),
        "--fail-on",
        "critical",
    )

    assert inspected.returncode == 0, inspected.stderr
    result = read_json(report)
    assert result["summary"] == {"critical": 0, "warning": 0, "info": 0}
    assert result["findings"] == []


def test_faulty_corpus_reports_policy_findings(tmp_path: Path) -> None:
    corpus = tmp_path / "faulty.jsonl"
    policy = tmp_path / "policy.json"
    report = tmp_path / "report.json"
    write_policy(policy)

    generated = run_command(
        str(GENERATE_CORPUS),
        "--scenario",
        "faulty",
        "--entries",
        "40",
        "--output",
        str(corpus),
    )
    assert generated.returncode == 0, generated.stderr

    inspected = run_command(
        str(INSPECT_LOGS),
        "--input-jsonl",
        str(corpus),
        "--policy",
        str(policy),
        "--output-json",
        str(report),
        "--fail-on",
        "critical",
    )

    assert inspected.returncode == 1, inspected.stderr
    result = read_json(report)
    finding_ids = {finding["rule_id"] for finding in result["findings"]}
    assert finding_ids == {"application-error", "auth-failure", "storage-full"}
    assert result["summary"] == {"critical": 1, "warning": 2, "info": 0}


def test_adversarial_corpus_does_not_match_substrings(tmp_path: Path) -> None:
    corpus = tmp_path / "adversarial.jsonl"
    policy = tmp_path / "policy.json"
    report = tmp_path / "report.json"
    write_policy(policy)

    generated = run_command(
        str(GENERATE_CORPUS),
        "--scenario",
        "adversarial",
        "--entries",
        "24",
        "--output",
        str(corpus),
    )
    assert generated.returncode == 0, generated.stderr

    inspected = run_command(
        str(INSPECT_LOGS),
        "--input-jsonl",
        str(corpus),
        "--policy",
        str(policy),
        "--output-json",
        str(report),
    )

    assert inspected.returncode == 0, inspected.stderr
    result = read_json(report)
    assert result["findings"] == []


def test_malformed_policy_returns_actionable_error(tmp_path: Path) -> None:
    corpus = tmp_path / "clean.jsonl"
    policy = tmp_path / "malformed.json"
    report = tmp_path / "report.json"
    policy.write_text(
        json.dumps(
            {
                "name": "broken-policy",
                "description": "Invalid regex policy.",
                "window_minutes": 60,
                "rules": [
                    {
                        "id": "broken",
                        "severity": "warning",
                        "description": "Malformed regex.",
                        "service": "*",
                        "patterns": ["["],
                        "threshold": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    generated = run_command(
        str(GENERATE_CORPUS),
        "--scenario",
        "clean",
        "--entries",
        "4",
        "--output",
        str(corpus),
    )
    assert generated.returncode == 0, generated.stderr

    inspected = run_command(
        str(INSPECT_LOGS),
        "--input-jsonl",
        str(corpus),
        "--policy",
        str(policy),
        "--output-json",
        str(report),
    )

    assert inspected.returncode == 2
    assert "Invalid policy" in inspected.stderr
    assert "broken" in inspected.stderr


def test_loki_mode_evaluates_query_range_results(tmp_path: Path) -> None:
    policy = tmp_path / "policy.json"
    report = tmp_path / "report.json"
    write_policy(policy)
    server, loki_url = loki_server()

    try:
        inspected = run_command(
            str(INSPECT_LOGS),
            "--loki-url",
            loki_url,
            "--lookback-minutes",
            "15",
            "--policy",
            str(policy),
            "--output-json",
            str(report),
            "--fail-on",
            "critical",
        )
    finally:
        server.shutdown()

    assert inspected.returncode == 1, inspected.stderr
    result = read_json(report)
    finding_ids = {finding["rule_id"] for finding in result["findings"]}
    assert finding_ids == {"application-error", "storage-full"}
    assert LokiHandler.requested_query == '{job="mms"}'


def test_faulty_corpus_sends_discord_notification_when_enabled(tmp_path: Path) -> None:
    corpus = tmp_path / "faulty.jsonl"
    policy = tmp_path / "policy.json"
    report = tmp_path / "report.json"
    write_notification_policy(policy)
    server, webhook_url = webhook_server()

    generated = run_command(
        str(GENERATE_CORPUS),
        "--scenario",
        "faulty",
        "--entries",
        "40",
        "--output",
        str(corpus),
    )
    assert generated.returncode == 0, generated.stderr

    try:
        inspected = run_command(
            str(INSPECT_LOGS),
            "--input-jsonl",
            str(corpus),
            "--policy",
            str(policy),
            "--output-json",
            str(report),
            "--fail-on",
            "critical",
            "--notify",
            env={"MMS_TEST_WEBHOOK_URL": webhook_url},
        )
    finally:
        server.shutdown()

    assert inspected.returncode == 1, inspected.stderr
    assert len(WebhookHandler.requests) == 1
    payload = WebhookHandler.requests[0]["payload"]
    assert payload["content"].startswith("MMS log inspection found 1 issue")
    assert "storage-full" in payload["content"]


def test_clean_corpus_does_not_send_notification(tmp_path: Path) -> None:
    corpus = tmp_path / "clean.jsonl"
    policy = tmp_path / "policy.json"
    report = tmp_path / "report.json"
    write_notification_policy(policy)
    server, webhook_url = webhook_server()

    generated = run_command(
        str(GENERATE_CORPUS),
        "--scenario",
        "clean",
        "--entries",
        "24",
        "--output",
        str(corpus),
    )
    assert generated.returncode == 0, generated.stderr

    try:
        inspected = run_command(
            str(INSPECT_LOGS),
            "--input-jsonl",
            str(corpus),
            "--policy",
            str(policy),
            "--output-json",
            str(report),
            "--notify",
            env={"MMS_TEST_WEBHOOK_URL": webhook_url},
        )
    finally:
        server.shutdown()

    assert inspected.returncode == 0, inspected.stderr
    assert WebhookHandler.requests == []


def test_missing_notification_webhook_env_returns_actionable_error(tmp_path: Path) -> None:
    corpus = tmp_path / "faulty.jsonl"
    policy = tmp_path / "policy.json"
    report = tmp_path / "report.json"
    write_notification_policy(policy)

    generated = run_command(
        str(GENERATE_CORPUS),
        "--scenario",
        "faulty",
        "--entries",
        "40",
        "--output",
        str(corpus),
    )
    assert generated.returncode == 0, generated.stderr

    inspected = run_command(
        str(INSPECT_LOGS),
        "--input-jsonl",
        str(corpus),
        "--policy",
        str(policy),
        "--output-json",
        str(report),
        "--notify",
        env={"MMS_TEST_WEBHOOK_URL": ""},
    )

    assert inspected.returncode == 2
    assert "MMS_TEST_WEBHOOK_URL" in inspected.stderr


def test_generic_notification_sends_structured_report(tmp_path: Path) -> None:
    corpus = tmp_path / "faulty.jsonl"
    policy = tmp_path / "policy.json"
    report = tmp_path / "report.json"
    write_notification_policy(policy, provider="generic")
    server, webhook_url = webhook_server()

    generated = run_command(
        str(GENERATE_CORPUS),
        "--scenario",
        "faulty",
        "--entries",
        "40",
        "--output",
        str(corpus),
    )
    assert generated.returncode == 0, generated.stderr

    try:
        inspected = run_command(
            str(INSPECT_LOGS),
            "--input-jsonl",
            str(corpus),
            "--policy",
            str(policy),
            "--output-json",
            str(report),
            "--notify",
            env={"MMS_TEST_WEBHOOK_URL": webhook_url},
        )
    finally:
        server.shutdown()

    assert inspected.returncode == 1, inspected.stderr
    payload = WebhookHandler.requests[0]["payload"]
    assert payload["summary"] == {"critical": 1, "warning": 0, "info": 0}
    assert payload["findings"][0]["rule_id"] == "storage-full"


def test_slack_notification_sends_text_payload(tmp_path: Path) -> None:
    corpus = tmp_path / "faulty.jsonl"
    policy = tmp_path / "policy.json"
    report = tmp_path / "report.json"
    write_notification_policy(policy, provider="slack")
    server, webhook_url = webhook_server()

    generated = run_command(
        str(GENERATE_CORPUS),
        "--scenario",
        "faulty",
        "--entries",
        "40",
        "--output",
        str(corpus),
    )
    assert generated.returncode == 0, generated.stderr

    try:
        inspected = run_command(
            str(INSPECT_LOGS),
            "--input-jsonl",
            str(corpus),
            "--policy",
            str(policy),
            "--output-json",
            str(report),
            "--notify",
            env={"MMS_TEST_WEBHOOK_URL": webhook_url},
        )
    finally:
        server.shutdown()

    assert inspected.returncode == 1, inspected.stderr
    payload = WebhookHandler.requests[0]["payload"]
    assert payload["text"].startswith("MMS log inspection found 1 issue")
    assert "storage-full" in payload["text"]
