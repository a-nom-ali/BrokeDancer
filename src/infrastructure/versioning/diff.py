"""
Diff Utilities

Provides structural diffing for JSON data with human-readable output
and change detection for versioned entities.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import EntityType, VersionDiff


class ChangeType(Enum):
    """Type of change in a diff"""
    ADD = "add"
    REMOVE = "remove"
    MODIFY = "modify"


@dataclass
class Change:
    """A single change in a diff"""
    path: str
    change_type: ChangeType
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize change to dictionary"""
        return {
            "path": self.path,
            "type": self.change_type.value,
            "old": self.old_value,
            "new": self.new_value
        }


def compute_diff(
    entity_type: EntityType,
    entity_id: str,
    from_version: int,
    to_version: int,
    from_data: Dict[str, Any],
    to_data: Dict[str, Any]
) -> VersionDiff:
    """
    Compute structural diff between two versions.

    Uses recursive comparison to find changes.

    Args:
        entity_type: Type of entity
        entity_id: Entity identifier
        from_version: Source version number
        to_version: Target version number
        from_data: Source version data
        to_data: Target version data

    Returns:
        VersionDiff with changes and summary
    """
    changes = _diff_dicts(from_data, to_data, "")

    # Generate summary
    adds = sum(1 for c in changes if c.change_type == ChangeType.ADD)
    removes = sum(1 for c in changes if c.change_type == ChangeType.REMOVE)
    modifies = sum(1 for c in changes if c.change_type == ChangeType.MODIFY)

    summary = f"{adds} additions, {removes} removals, {modifies} modifications"

    return VersionDiff(
        entity_type=entity_type,
        entity_id=entity_id,
        from_version=from_version,
        to_version=to_version,
        changes=[c.to_dict() for c in changes],
        summary=summary
    )


def _diff_dicts(
    old: Dict[str, Any],
    new: Dict[str, Any],
    path: str
) -> List[Change]:
    """
    Recursively diff two dictionaries.

    Args:
        old: Old dictionary
        new: New dictionary
        path: Current path in the structure (e.g., "config.settings")

    Returns:
        List of Change objects
    """
    changes = []

    all_keys = set(old.keys()) | set(new.keys())

    for key in all_keys:
        current_path = f"{path}.{key}" if path else key

        if key not in old:
            # Key added
            changes.append(Change(
                path=current_path,
                change_type=ChangeType.ADD,
                new_value=new[key]
            ))
        elif key not in new:
            # Key removed
            changes.append(Change(
                path=current_path,
                change_type=ChangeType.REMOVE,
                old_value=old[key]
            ))
        elif old[key] != new[key]:
            # Key modified
            if isinstance(old[key], dict) and isinstance(new[key], dict):
                # Recurse into nested dicts
                changes.extend(_diff_dicts(old[key], new[key], current_path))
            elif isinstance(old[key], list) and isinstance(new[key], list):
                # Diff lists
                changes.extend(_diff_lists(old[key], new[key], current_path))
            else:
                # Simple value change
                changes.append(Change(
                    path=current_path,
                    change_type=ChangeType.MODIFY,
                    old_value=old[key],
                    new_value=new[key]
                ))

    return changes


def _diff_lists(
    old: List[Any],
    new: List[Any],
    path: str
) -> List[Change]:
    """
    Diff two lists.

    Simplified implementation - treats lists as a single unit if different.
    For complex list diffing (item-level changes), consider using a library
    like deepdiff.

    Args:
        old: Old list
        new: New list
        path: Current path

    Returns:
        List of Change objects
    """
    changes = []

    if old != new:
        changes.append(Change(
            path=path,
            change_type=ChangeType.MODIFY,
            old_value=old,
            new_value=new
        ))

    return changes


def compute_dict_diff(
    old: Dict[str, Any],
    new: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Simple dict diff for config comparison.

    Args:
        old: Old dictionary
        new: New dictionary

    Returns:
        Dictionary with changes list and count
    """
    changes = _diff_dicts(old, new, "")
    return {
        "changes": [c.to_dict() for c in changes],
        "change_count": len(changes)
    }
