"""
DAML-RAG Framework Exceptions

This module defines a unified exception hierarchy for the framework.
All exceptions include context information, recovery suggestions,
and preserve the original stack trace when re-raised.

Requirements: 9.1, 9.2, 9.3
"""

from typing import Dict, Any, Optional
import traceback


class DAMLRAGError(Exception):
    """
    Base exception class for all DAML-RAG framework errors.
    
    All framework exceptions inherit from this class and include:
    - context: Additional context information about the error
    - suggestion: Recovery suggestions for the user
    - cause: The original exception that caused this error
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            context: Additional context information as a dictionary
            suggestion: Recovery suggestion for the user
            cause: The original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.suggestion = suggestion
        self._cause = cause
        
        if cause is not None:
            self.__cause__ = cause
    
    @property
    def cause(self) -> Optional[Exception]:
        """Return the original exception that caused this error."""
        return self._cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the exception to a dictionary for logging/serialization."""
        result = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
        }
        
        if self.suggestion:
            result["suggestion"] = self.suggestion
        
        if self._cause:
            result["cause"] = {
                "type": type(self._cause).__name__,
                "message": str(self._cause),
            }
        
        return result
    
    def __str__(self) -> str:
        """Return a formatted string representation of the error."""
        parts = [self.message]
        
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")
        
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        
        if self._cause:
            parts.append(f"Caused by: {type(self._cause).__name__}: {self._cause}")
        
        return " | ".join(parts)
    
    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"context={self.context!r}, "
            f"suggestion={self.suggestion!r}, "
            f"cause={self._cause!r})"
        )


class ConfigurationError(DAMLRAGError):
    """Exception raised for configuration-related errors."""
    pass


class ToolNotFoundError(DAMLRAGError):
    """Exception raised when a requested tool is not found in the registry."""
    
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        ctx = context or {}
        if tool_name:
            ctx["tool_name"] = tool_name
        
        super().__init__(message, context=ctx, suggestion=suggestion, cause=cause)
        self.tool_name = tool_name


class ToolExecutionError(DAMLRAGError):
    """Exception raised when a tool execution fails."""
    
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        ctx = context or {}
        if tool_name:
            ctx["tool_name"] = tool_name
        
        super().__init__(message, context=ctx, suggestion=suggestion, cause=cause)
        self.tool_name = tool_name


class DAGExecutionError(DAMLRAGError):
    """Exception raised when DAG execution fails."""
    
    def __init__(
        self,
        message: str,
        dag_name: Optional[str] = None,
        failed_node: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        ctx = context or {}
        if dag_name:
            ctx["dag_name"] = dag_name
        if failed_node:
            ctx["failed_node"] = failed_node
        
        super().__init__(message, context=ctx, suggestion=suggestion, cause=cause)
        self.dag_name = dag_name
        self.failed_node = failed_node


class CacheError(DAMLRAGError):
    """Exception raised for cache-related errors."""
    pass


class ValidationError(DAMLRAGError):
    """Exception raised for validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        expected: Optional[Any] = None,
        received: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        ctx = context or {}
        if field:
            ctx["field"] = field
        if expected is not None:
            ctx["expected"] = str(expected)
        if received is not None:
            ctx["received"] = str(received)
        
        super().__init__(message, context=ctx, suggestion=suggestion, cause=cause)
        self.field = field
        self.expected = expected
        self.received = received


class RetrievalError(DAMLRAGError):
    """Exception raised for retrieval-related errors."""
    pass


class GenerationError(DAMLRAGError):
    """Exception raised for generation-related errors."""
    pass


class TimeoutError(DAMLRAGError):
    """Exception raised when an operation times out."""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        ctx = context or {}
        if timeout_seconds is not None:
            ctx["timeout_seconds"] = timeout_seconds
        
        super().__init__(message, context=ctx, suggestion=suggestion, cause=cause)
        self.timeout_seconds = timeout_seconds


class ConnectionError(DAMLRAGError):
    """Exception raised for connection-related errors."""
    pass


# Utility functions for error handling

def wrap_exception(
    error: Exception,
    message: str,
    error_class: type = DAMLRAGError,
    context: Optional[Dict[str, Any]] = None,
    suggestion: Optional[str] = None
) -> DAMLRAGError:
    """
    Wrap an exception in a DAML-RAG error while preserving the stack trace.
    """
    return error_class(
        message=message,
        context=context,
        suggestion=suggestion,
        cause=error
    )


def format_error_chain(error: Exception, max_depth: int = 5) -> str:
    """Format an error chain for logging."""
    lines = []
    current = error
    depth = 0
    
    while current is not None and depth < max_depth:
        prefix = "  " * depth
        if isinstance(current, DAMLRAGError):
            lines.append(f"{prefix}{current.__class__.__name__}: {current.message}")
            if current.context:
                lines.append(f"{prefix}  Context: {current.context}")
            if current.suggestion:
                lines.append(f"{prefix}  Suggestion: {current.suggestion}")
        else:
            lines.append(f"{prefix}{current.__class__.__name__}: {current}")
        
        current = getattr(current, "__cause__", None)
        depth += 1
    
    if current is not None:
        lines.append(f"{'  ' * depth}... (truncated)")
    
    return "\n".join(lines)
