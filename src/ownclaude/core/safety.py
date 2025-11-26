"""Safety and permissions system for PBOS AI."""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import deque

from loguru import logger

from .config import Config, SystemPermissions


class OperationType(Enum):
    """Types of operations that can be performed."""
    APP_OPEN = "app_open"
    APP_CLOSE = "app_close"
    FILE_CREATE = "file_create"
    FILE_APPEND = "file_append"
    FILE_MODIFY = "file_modify"
    FILE_DELETE = "file_delete"
    FILE_READ = "file_read"
    FILE_OPEN = "file_open"
    FILE_SEARCH = "file_search"
    DIR_CREATE = "dir_create"
    DIR_DELETE = "dir_delete"
    DIR_LIST = "dir_list"
    BROWSER_OPEN = "browser_open"
    BROWSER_CLOSE = "browser_close"
    SYSTEM_COMMAND = "system_command"


class Operation:
    """Represents an operation to be performed."""

    def __init__(
        self,
        operation_type: OperationType,
        target: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize operation.

        Args:
            operation_type: Type of operation.
            target: Target of the operation (file path, app name, etc).
            details: Additional operation details.
        """
        self.operation_type = operation_type
        self.target = target
        self.details = details or {}
        self.timestamp = datetime.now()
        self.id = f"{self.timestamp.timestamp()}_{operation_type.value}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert operation to dictionary.

        Returns:
            Dictionary representation of the operation.
        """
        return {
            "id": self.id,
            "type": self.operation_type.value,
            "target": self.target,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class RollbackManager:
    """Manages operation rollback."""

    def __init__(self, max_operations: int = 10):
        """Initialize rollback manager.

        Args:
            max_operations: Maximum number of operations to keep for rollback.
        """
        self.max_operations = max_operations
        self.operations: deque = deque(maxlen=max_operations)
        self.rollback_data: Dict[str, Any] = {}

    def record_operation(
        self,
        operation: Operation,
        rollback_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record an operation for potential rollback.

        Args:
            operation: The operation that was performed.
            rollback_info: Information needed to rollback the operation.
        """
        self.operations.append(operation)
        if rollback_info:
            self.rollback_data[operation.id] = rollback_info
        logger.debug(f"Recorded operation: {operation.operation_type.value}")

    def can_rollback(self, operation_id: str) -> bool:
        """Check if an operation can be rolled back.

        Args:
            operation_id: ID of the operation.

        Returns:
            True if rollback is possible, False otherwise.
        """
        return operation_id in self.rollback_data

    def rollback(self, operation_id: str) -> bool:
        """Attempt to rollback an operation.

        Args:
            operation_id: ID of the operation to rollback.

        Returns:
            True if rollback was successful, False otherwise.
        """
        if not self.can_rollback(operation_id):
            logger.warning(f"Cannot rollback operation: {operation_id}")
            return False

        rollback_info = self.rollback_data[operation_id]
        operation = next(
            (op for op in self.operations if op.id == operation_id),
            None
        )

        if not operation:
            return False

        try:
            # Perform rollback based on operation type
            if operation.operation_type == OperationType.FILE_CREATE:
                # Delete the created file
                file_path = Path(rollback_info['path'])
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Rolled back file creation: {file_path}")
                    return True

            elif operation.operation_type == OperationType.FILE_DELETE:
                # Restore the deleted file from backup
                backup_content = rollback_info.get('content')
                if backup_content:
                    file_path = Path(rollback_info['path'])
                    file_path.write_text(backup_content)
                    logger.info(f"Rolled back file deletion: {file_path}")
                    return True

            elif operation.operation_type in (
                OperationType.FILE_MODIFY,
                OperationType.FILE_APPEND
            ):
                # Restore previous content
                original_content = rollback_info.get('original_content')
                if original_content:
                    file_path = Path(rollback_info['path'])
                    file_path.write_text(original_content)
                    logger.info(f"Rolled back file modification: {file_path}")
                    return True

            # Other operation types may not support rollback
            logger.warning(f"Rollback not implemented for: {operation.operation_type}")
            return False

        except Exception as e:
            logger.error(f"Rollback failed for {operation_id}: {e}")
            return False

    def get_history(self) -> List[Dict[str, Any]]:
        """Get operation history.

        Returns:
            List of operations as dictionaries.
        """
        return [op.to_dict() for op in self.operations]

    def clear(self) -> None:
        """Clear operation history."""
        self.operations.clear()
        self.rollback_data.clear()
        logger.info("Operation history cleared")


class SafetyManager:
    """Manages safety checks and permissions."""

    def __init__(self, config: Config):
        """Initialize safety manager.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.permissions = config.system_permissions
        self.security = config.security
        self.rollback_manager = RollbackManager(
            max_operations=self.security.max_rollback_operations
        )

    def check_permission(self, operation: Operation) -> tuple[bool, Optional[str]]:
        """Check if an operation is permitted.

        Args:
            operation: Operation to check.

        Returns:
            Tuple of (is_permitted, reason_if_denied).
        """
        # Check type-based permissions
        if operation.operation_type in [
            OperationType.APP_OPEN,
            OperationType.APP_CLOSE
        ]:
            if not self.permissions.allow_app_control:
                return False, "Application control is disabled"

        elif operation.operation_type in [
            OperationType.FILE_CREATE,
            OperationType.FILE_APPEND,
            OperationType.FILE_MODIFY,
            OperationType.FILE_DELETE,
            OperationType.FILE_READ,
            OperationType.FILE_OPEN,
            OperationType.FILE_SEARCH,
            OperationType.DIR_CREATE,
            OperationType.DIR_DELETE,
            OperationType.DIR_LIST
        ]:
            if not self.permissions.allow_file_operations:
                return False, "File operations are disabled"

            # Check sensitive paths
            if self._is_sensitive_path(operation.target):
                return False, f"Access to sensitive path denied: {operation.target}"

        elif operation.operation_type in [
            OperationType.BROWSER_OPEN,
            OperationType.BROWSER_CLOSE
        ]:
            if not self.permissions.allow_browser_control:
                return False, "Browser control is disabled"

        elif operation.operation_type == OperationType.SYSTEM_COMMAND:
            if not self.permissions.allow_system_commands:
                return False, "System commands are disabled"

        return True, None

    def requires_confirmation(self, operation: Operation) -> bool:
        """Check if an operation requires user confirmation.

        Args:
            operation: Operation to check.

        Returns:
            True if confirmation is required, False otherwise.
        """
        confirmations = self.permissions.require_confirmation

        if operation.operation_type == OperationType.FILE_DELETE:
            return confirmations.file_deletion

        elif operation.operation_type == OperationType.DIR_DELETE:
            return confirmations.file_deletion

        elif operation.operation_type == OperationType.APP_CLOSE:
            return confirmations.app_closure

        elif operation.operation_type == OperationType.SYSTEM_COMMAND:
            return confirmations.system_commands

        elif operation.operation_type in (OperationType.FILE_MODIFY, OperationType.FILE_APPEND):
            return confirmations.file_modification

        return False

    def _is_sensitive_path(self, path: str) -> bool:
        """Check if a path is in the sensitive paths list.

        Args:
            path: Path to check.

        Returns:
            True if path is sensitive, False otherwise.
        """
        path_obj = Path(path).resolve()

        for sensitive in self.security.sensitive_paths:
            sensitive_obj = Path(sensitive)
            try:
                # Check if path is within or is a sensitive path
                path_obj.relative_to(sensitive_obj)
                return True
            except ValueError:
                continue

        return False

    def log_operation(
        self,
        operation: Operation,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Log an operation.

        Args:
            operation: The operation that was performed.
            success: Whether the operation succeeded.
            error: Error message if operation failed.
        """
        if not self.config.logging.log_operations:
            return

        log_entry = {
            "timestamp": operation.timestamp.isoformat(),
            "operation": operation.to_dict(),
            "success": success,
            "error": error
        }

        if success:
            logger.info(f"Operation completed: {operation.operation_type.value} on {operation.target}")
        else:
            logger.warning(f"Operation failed: {operation.operation_type.value} on {operation.target} - {error}")

    def can_rollback(self) -> bool:
        """Check if rollback is enabled.

        Returns:
            True if rollback is enabled, False otherwise.
        """
        return self.security.enable_rollback

    def record_for_rollback(
        self,
        operation: Operation,
        rollback_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record an operation for potential rollback.

        Args:
            operation: The operation that was performed.
            rollback_info: Information needed to rollback the operation.
        """
        if self.can_rollback():
            self.rollback_manager.record_operation(operation, rollback_info)

    def rollback_operation(self, operation_id: str) -> bool:
        """Rollback an operation.

        Args:
            operation_id: ID of the operation to rollback.

        Returns:
            True if rollback was successful, False otherwise.
        """
        if not self.can_rollback():
            logger.warning("Rollback is disabled")
            return False

        return self.rollback_manager.rollback(operation_id)

    def get_operation_history(self) -> List[Dict[str, Any]]:
        """Get operation history.

        Returns:
            List of operations as dictionaries.
        """
        return self.rollback_manager.get_history()
