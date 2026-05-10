from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def read_repo_file(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_notification_defaults_are_disabled_and_use_private_env_file() -> None:
    defaults = read_repo_file("roles/logging/defaults/main.yml")

    assert "logging_inspection_notifications_enabled: false" in defaults
    assert "logging_inspection_environment_file:" in defaults
    assert "notifications.env" in defaults


def test_log_inspection_service_enables_notifications_conditionally() -> None:
    service = read_repo_file("roles/logging/templates/mms-log-inspect.service.j2")

    assert "{% if logging_inspection_notifications_enabled %}" in service
    assert "EnvironmentFile={{ logging_inspection_environment_file }}" in service
    assert "--notify" in service


def test_notification_environment_file_is_private_and_operator_owned() -> None:
    setup = read_repo_file("roles/logging/tasks/setup.yml")

    assert "Create log inspection notification environment file" in setup
    assert "mode: \"0600\"" in setup
    assert "force: false" in setup
