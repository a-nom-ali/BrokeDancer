"""
Workflow Versioning

Provides version control for workflow definitions with:
- Schema validation per version
- Automatic snapshots on modification
- Version history and restore
"""

from typing import Any, Dict, List, Optional

from src.infrastructure.logging import get_logger

from .base import EntityType, VersionDiff, VersionMetadata, VersionStore

logger = get_logger(__name__)


# JSON Schema for workflow validation (v1.0.0)
WORKFLOW_SCHEMA_V1 = {
    "type": "object",
    "required": ["name", "blocks", "connections"],
    "properties": {
        "name": {"type": "string"},
        "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
        "description": {"type": "string"},
        "domain": {"type": "string"},
        "blocks": {"type": "array"},
        "connections": {"type": "array"},
        "config": {"type": "object"},
        "metadata": {"type": "object"}
    }
}


class WorkflowVersionManager:
    """
    Manages workflow versioning with schema validation.

    Usage:
        manager = WorkflowVersionManager(version_store)

        # Save a workflow
        meta = await manager.save_workflow(
            workflow_id="my_strategy",
            workflow={"name": "My Strategy", "blocks": [...], "connections": [...]},
            created_by="user@example.com"
        )

        # Get workflow history
        versions = await manager.list_workflow_versions("my_strategy")

        # Restore previous version
        await manager.restore_workflow("my_strategy", to_version=3, restored_by="admin")
    """

    def __init__(self, version_store: VersionStore):
        self._store = version_store
        self._schemas = {"1.0.0": WORKFLOW_SCHEMA_V1}

    def validate_workflow(self, workflow: Dict[str, Any]) -> List[str]:
        """
        Validate workflow against schema.

        Args:
            workflow: Workflow definition dictionary

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required fields
        required = ["name", "blocks", "connections"]
        for field in required:
            if field not in workflow:
                errors.append(f"Missing required field: {field}")

        # Enforce version field
        if "version" not in workflow:
            errors.append("Missing required field: version")
        elif not isinstance(workflow["version"], str):
            errors.append("version must be a string")

        # Validate blocks
        if "blocks" in workflow:
            if not isinstance(workflow["blocks"], list):
                errors.append("blocks must be an array")
            else:
                for i, block in enumerate(workflow["blocks"]):
                    if not isinstance(block, dict):
                        errors.append(f"Block {i} must be an object")
                        continue
                    if "id" not in block:
                        errors.append(f"Block {i} missing 'id'")
                    if "category" not in block:
                        errors.append(f"Block {i} missing 'category'")

        # Validate connections
        if "connections" in workflow:
            if not isinstance(workflow["connections"], list):
                errors.append("connections must be an array")
            else:
                block_ids = set()
                if "blocks" in workflow and isinstance(workflow["blocks"], list):
                    block_ids = {
                        b.get("id") for b in workflow["blocks"]
                        if isinstance(b, dict) and "id" in b
                    }

                for i, conn in enumerate(workflow["connections"]):
                    if not isinstance(conn, dict):
                        errors.append(f"Connection {i} must be an object")
                        continue
                    if "from" not in conn or "to" not in conn:
                        errors.append(f"Connection {i} missing 'from' or 'to'")
                    else:
                        from_block = conn.get("from", {})
                        to_block = conn.get("to", {})

                        from_id = from_block.get("blockId") if isinstance(from_block, dict) else None
                        to_id = to_block.get("blockId") if isinstance(to_block, dict) else None

                        if from_id and from_id not in block_ids:
                            errors.append(f"Connection {i} references unknown block: {from_id}")
                        if to_id and to_id not in block_ids:
                            errors.append(f"Connection {i} references unknown block: {to_id}")

        return errors

    async def save_workflow(
        self,
        workflow_id: str,
        workflow: Dict[str, Any],
        created_by: str,
        message: Optional[str] = None,
        validate: bool = True,
        tags: Optional[List[str]] = None
    ) -> VersionMetadata:
        """
        Save a workflow version.

        Args:
            workflow_id: Unique workflow identifier
            workflow: Workflow definition
            created_by: User or system ID
            message: Optional version message
            validate: Whether to validate schema (default True)
            tags: Optional tags for this version

        Returns:
            VersionMetadata of saved version

        Raises:
            ValueError: If validation fails
        """
        if validate:
            errors = self.validate_workflow(workflow)
            if errors:
                raise ValueError(f"Workflow validation failed: {'; '.join(errors)}")

        # Ensure version field is set
        if "version" not in workflow:
            workflow["version"] = "1.0.0"

        logger.info(
            "workflow_version_saved",
            workflow_id=workflow_id,
            workflow_version=workflow.get("version"),
            created_by=created_by
        )

        return await self._store.save_version(
            entity_type=EntityType.WORKFLOW,
            entity_id=workflow_id,
            data=workflow,
            created_by=created_by,
            message=message,
            tags=tags
        )

    async def get_workflow(
        self,
        workflow_id: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a workflow version.

        Args:
            workflow_id: Workflow identifier
            version: Version number (None = latest)

        Returns:
            Workflow data or None if not found
        """
        snapshot = await self._store.get_version(
            EntityType.WORKFLOW,
            workflow_id,
            version
        )
        return snapshot.data if snapshot else None

    async def list_workflow_versions(
        self,
        workflow_id: str,
        limit: int = 50
    ) -> List[VersionMetadata]:
        """
        List version history for a workflow.

        Args:
            workflow_id: Workflow identifier
            limit: Max versions to return

        Returns:
            List of VersionMetadata, newest first
        """
        return await self._store.list_versions(
            EntityType.WORKFLOW,
            workflow_id,
            limit=limit
        )

    async def restore_workflow(
        self,
        workflow_id: str,
        to_version: int,
        restored_by: str
    ) -> Optional[VersionMetadata]:
        """
        Restore a workflow to a previous version.

        Creates a new version with the old data.

        Args:
            workflow_id: Workflow identifier
            to_version: Version to restore to
            restored_by: User performing the restore

        Returns:
            Metadata of new version, or None if source not found
        """
        result = await self._store.rollback(
            EntityType.WORKFLOW,
            workflow_id,
            to_version,
            created_by=restored_by
        )

        if result:
            logger.info(
                "workflow_restored",
                workflow_id=workflow_id,
                from_version=to_version,
                new_version=result.version,
                restored_by=restored_by
            )

        return result

    async def diff_workflows(
        self,
        workflow_id: str,
        from_version: int,
        to_version: int
    ) -> Optional[VersionDiff]:
        """
        Get diff between two workflow versions.

        Args:
            workflow_id: Workflow identifier
            from_version: Source version
            to_version: Target version

        Returns:
            VersionDiff or None if versions not found
        """
        return await self._store.diff_versions(
            EntityType.WORKFLOW,
            workflow_id,
            from_version,
            to_version
        )
