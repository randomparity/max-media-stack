"""Contract tests for service definitions in ``services/*.yml``.

These guard the data-driven core: the generic ``quadlet_service`` role and the
restore dispatch in ``playbooks/restore.yml`` both read these files by key, so a
malformed or incomplete definition breaks deploy/restore at runtime with no
earlier signal. The tests below turn that runtime footgun into a fast unit
failure.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.services.service_schema import (
    VALID_BACKUP_TYPES,
    validate_service_definition,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = REPO_ROOT / "services"


def _load(stem: str) -> dict:
    return yaml.safe_load((SERVICES_DIR / f"{stem}.yml").read_text(encoding="utf-8"))


def _service_stems() -> list[str]:
    return sorted(p.stem for p in SERVICES_DIR.glob("*.yml"))


def test_validator_flags_a_broken_definition() -> None:
    """A definition wrong in several ways yields one error per violation."""
    broken = {
        "radarr": {
            # missing: description, volumes, environment
            "name": "sonarr",  # mismatched with top-level key and filename
            "image": "lscr.io/linuxserver/radarr:latest",  # unpinned tag
            "backup_type": "bogus",  # no restore handler
        }
    }

    errors = validate_service_definition("radarr", broken)

    joined = "\n".join(errors)
    assert "description" in joined
    assert "volumes" in joined
    assert "environment" in joined
    assert "name" in joined  # name != stem
    assert "latest" in joined  # unpinned image
    assert "bogus" in joined  # unknown backup_type


def test_valid_definition_has_no_errors() -> None:
    good = {
        "radarr": {
            "name": "radarr",
            "description": "Radarr - Movie Manager",
            "image": "lscr.io/linuxserver/radarr:6.2.1.10461-ls306",
            "volumes": ["{{ mms_config_dir }}/radarr:/config:Z"],
            "environment": ["PUID=0"],
            "backup_type": "arr",
        }
    }

    assert validate_service_definition("radarr", good) == []


@pytest.mark.parametrize("stem", _service_stems())
def test_real_service_definition_is_valid(stem: str) -> None:
    errors = validate_service_definition(stem, _load(stem))
    assert errors == [], f"services/{stem}.yml: " + "; ".join(errors)


def test_backup_types_match_restore_dispatch() -> None:
    """The validator's known types must stay in sync with restore.yml.

    ``playbooks/restore.yml`` asserts ``_restore_backup_type in [...]``; if a new
    handler is added there but not here (or vice versa) the two drift silently.
    """
    restore = (REPO_ROOT / "playbooks" / "restore.yml").read_text(encoding="utf-8")
    for backup_type in VALID_BACKUP_TYPES:
        assert f"'{backup_type}'" in restore, (
            f"backup_type '{backup_type}' is known to the validator but not "
            "listed in playbooks/restore.yml"
        )
