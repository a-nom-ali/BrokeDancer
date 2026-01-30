"""
Retention Policy Enforcement

Determines which versions to delete based on retention policy rules.
"""

from datetime import datetime
from typing import List

from .base import RetentionPolicy, VersionMetadata


def apply_policy(
    versions: List[VersionMetadata],
    policy: RetentionPolicy
) -> List[VersionMetadata]:
    """
    Determine which versions to delete based on retention policy.

    Args:
        versions: List of version metadata (newest first)
        policy: Retention policy to apply

    Returns:
        List of versions that should be deleted
    """
    if not versions:
        return []

    to_delete = []
    now = datetime.utcnow()

    for i, meta in enumerate(versions):
        # Always keep the N latest
        if i < policy.keep_latest:
            continue

        # Keep tagged versions if policy says so
        if policy.keep_tagged and meta.tags:
            continue

        should_delete = False

        # Check max age
        if policy.max_age:
            age = now - meta.created_at
            if age > policy.max_age:
                should_delete = True

        # Check max versions (after keep_latest)
        if policy.max_versions:
            # Count how many we've kept so far (excluding those marked for deletion)
            kept_count = i - len(to_delete)
            if kept_count >= policy.max_versions:
                should_delete = True

        if should_delete:
            to_delete.append(meta)

    return to_delete
