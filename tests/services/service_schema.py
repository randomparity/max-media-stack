"""Validation logic for MMS service definitions (``services/*.yml``).

A service file holds a single top-level mapping whose key is the service name
(equal to the filename stem). Both the ``quadlet_service`` role and the restore
dispatch in ``playbooks/restore.yml`` look the definition up by that key, so the
key, the filename, and the inner ``name`` field must all agree.

``validate_service_definition`` returns a list of human-readable error strings;
an empty list means the definition is valid.
"""

from __future__ import annotations

# Must stay in sync with the handler list asserted in playbooks/restore.yml.
VALID_BACKUP_TYPES = ("arr", "sabnzbd", "jellyfin", "plex", "immich", "open-notebook")

REQUIRED_KEYS = ("name", "description", "image", "volumes", "environment", "backup_type")


def _validate_image(image: object) -> list[str]:
    if not isinstance(image, str):
        return ["image: must be a string"]
    if "@sha256:" in image:  # digest-pinned is the strongest form
        return []
    name, _, tag = image.rpartition(":")
    if not name or not tag or "/" in tag:
        return [f"image: '{image}' is not tag-pinned (expected name:tag)"]
    if tag == "latest":
        return ["image: 'latest' tag is not allowed; pin an explicit version"]
    return []


def validate_service_definition(stem: str, data: object) -> list[str]:
    """Validate a parsed service definition against the MMS contract.

    Args:
        stem: The filename stem, e.g. ``radarr`` for ``services/radarr.yml``.
        data: The parsed YAML document (expected: a single-key mapping).

    Returns:
        A list of error messages; empty if the definition is valid.
    """
    if not isinstance(data, dict):
        return [f"{stem}: top-level document must be a mapping"]
    if list(data.keys()) != [stem]:
        return [
            f"{stem}: top-level key must be exactly '{stem}', "
            f"got {list(data.keys())}"
        ]

    service = data[stem]
    if not isinstance(service, dict):
        return [f"{stem}: '{stem}' must map to a mapping"]

    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in service:
            errors.append(f"missing required key: {key}")

    if service.get("name") not in (None, stem):
        errors.append(
            f"name '{service.get('name')}' must equal the filename stem '{stem}'"
        )

    if "image" in service:
        errors.extend(_validate_image(service["image"]))

    for list_key in ("volumes", "environment"):
        value = service.get(list_key)
        if value is not None and not isinstance(value, list):
            errors.append(f"{list_key}: must be a list")
    if isinstance(service.get("volumes"), list) and not service["volumes"]:
        errors.append("volumes: must not be empty")

    backup_type = service.get("backup_type")
    if backup_type is not None and backup_type not in VALID_BACKUP_TYPES:
        errors.append(
            f"backup_type '{backup_type}' has no restore handler; "
            f"valid types: {', '.join(VALID_BACKUP_TYPES)}"
        )

    return errors
