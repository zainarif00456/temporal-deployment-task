"""
Custom exception hierarchy for Temporal Platform.
Provides structured error handling with proper error propagation and context.
"""
from typing import Any, Dict, Optional
from enum import Enum


class ErrorCode(Enum):
    """Structured error codes for consistent error handling."""
    
    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    
    # Temporal-specific errors
    TEMPORAL_CONNECTION_ERROR = "TEMPORAL_CONNECTION_ERROR"
    WORKFLOW_EXECUTION_ERROR = "WORKFLOW_EXECUTION_ERROR"
    ACTIVITY_EXECUTION_ERROR = "ACTIVITY_EXECUTION_ERROR"
    WORKFLOW_TIMEOUT_ERROR = "WORKFLOW_TIMEOUT_ERROR"
    ACTIVITY_TIMEOUT_ERROR = "ACTIVITY_TIMEOUT_ERROR"
    WORKFLOW_CANCELLED_ERROR = "WORKFLOW_CANCELLED_ERROR"
    WORKFLOW_FAILED_ERROR = "WORKFLOW_FAILED_ERROR"
    
    # Data processing errors
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    DATA_PROCESSING_ERROR = "DATA_PROCESSING_ERROR"
    DATA_CORRUPTION_ERROR = "DATA_CORRUPTION_ERROR"
    
    # Infrastructure errors
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    ELASTICSEARCH_CONNECTION_ERROR = "ELASTICSEARCH_CONNECTION_ERROR"
    ELASTICSEARCH_QUERY_ERROR = "ELASTICSEARCH_QUERY_ERROR"
    
    # Resource errors
    RESOURCE_NOT_FOUND_ERROR = "RESOURCE_NOT_FOUND_ERROR"
    RESOURCE_ALREADY_EXISTS_ERROR = "RESOURCE_ALREADY_EXISTS_ERROR"
    RESOURCE_LOCKED_ERROR = "RESOURCE_LOCKED_ERROR"
    INSUFFICIENT_RESOURCES_ERROR = "INSUFFICIENT_RESOURCES_ERROR"
    
    # Security errors
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"


class TemporalPlatformError(Exception):
    """
    Base exception for all Temporal Platform errors.
    Provides structured error information with context and error codes.
    """
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize TemporalPlatformError.
        
        Args:
            message: Human-readable error message
            error_code: Structured error code for programmatic handling
            context: Additional context information
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause
    
    def __str__(self) -> str:
        """String representation of the error."""
        context_str = ""
        if self.context:
            context_items = [f"{k}={v}" for k, v in self.context.items()]
            context_str = f" | Context: {', '.join(context_items)}"
        
        cause_str = ""
        if self.cause:
            cause_str = f" | Caused by: {type(self.cause).__name__}: {self.cause}"
        
        return f"[{self.error_code.value}] {self.message}{context_str}{cause_str}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            "error_type": type(self).__name__,
            "error_code": self.error_code.value,
            "message": self.message,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
        }


class ValidationError(TemporalPlatformError):
    """Raised when data validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if field is not None:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)
        
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            context=context,
            cause=cause,
        )


class ConfigurationError(TemporalPlatformError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if config_key is not None:
            context["config_key"] = config_key
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIGURATION_ERROR,
            context=context,
            cause=cause,
        )


class TemporalConnectionError(TemporalPlatformError):
    """Raised when unable to connect to Temporal server."""
    
    def __init__(
        self,
        message: str,
        address: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if address is not None:
            context["temporal_address"] = address
        
        super().__init__(
            message=message,
            error_code=ErrorCode.TEMPORAL_CONNECTION_ERROR,
            context=context,
            cause=cause,
        )


class WorkflowExecutionError(TemporalPlatformError):
    """Raised when workflow execution fails."""
    
    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        workflow_type: Optional[str] = None,
        run_id: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if workflow_id is not None:
            context["workflow_id"] = workflow_id
        if workflow_type is not None:
            context["workflow_type"] = workflow_type
        if run_id is not None:
            context["run_id"] = run_id
        
        super().__init__(
            message=message,
            error_code=ErrorCode.WORKFLOW_EXECUTION_ERROR,
            context=context,
            cause=cause,
        )


class ActivityExecutionError(TemporalPlatformError):
    """Raised when activity execution fails."""
    
    def __init__(
        self,
        message: str,
        activity_type: Optional[str] = None,
        activity_id: Optional[str] = None,
        attempt: Optional[int] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if activity_type is not None:
            context["activity_type"] = activity_type
        if activity_id is not None:
            context["activity_id"] = activity_id
        if attempt is not None:
            context["attempt"] = attempt
        
        super().__init__(
            message=message,
            error_code=ErrorCode.ACTIVITY_EXECUTION_ERROR,
            context=context,
            cause=cause,
        )


class WorkflowTimeoutError(TemporalPlatformError):
    """Raised when workflow execution times out."""
    
    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if workflow_id is not None:
            context["workflow_id"] = workflow_id
        if timeout_seconds is not None:
            context["timeout_seconds"] = timeout_seconds
        
        super().__init__(
            message=message,
            error_code=ErrorCode.WORKFLOW_TIMEOUT_ERROR,
            context=context,
            cause=cause,
        )


class ActivityTimeoutError(TemporalPlatformError):
    """Raised when activity execution times out."""
    
    def __init__(
        self,
        message: str,
        activity_type: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if activity_type is not None:
            context["activity_type"] = activity_type
        if timeout_seconds is not None:
            context["timeout_seconds"] = timeout_seconds
        
        super().__init__(
            message=message,
            error_code=ErrorCode.ACTIVITY_TIMEOUT_ERROR,
            context=context,
            cause=cause,
        )


class DataProcessingError(TemporalPlatformError):
    """Raised when data processing fails."""
    
    def __init__(
        self,
        message: str,
        data_type: Optional[str] = None,
        record_count: Optional[int] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if data_type is not None:
            context["data_type"] = data_type
        if record_count is not None:
            context["record_count"] = record_count
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DATA_PROCESSING_ERROR,
            context=context,
            cause=cause,
        )


class DatabaseConnectionError(TemporalPlatformError):
    """Raised when database connection fails."""
    
    def __init__(
        self,
        message: str,
        database_type: Optional[str] = None,
        host: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if database_type is not None:
            context["database_type"] = database_type
        if host is not None:
            context["host"] = host
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_CONNECTION_ERROR,
            context=context,
            cause=cause,
        )


class ElasticsearchConnectionError(TemporalPlatformError):
    """Raised when Elasticsearch connection fails."""
    
    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        index: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if host is not None:
            context["elasticsearch_host"] = host
        if index is not None:
            context["elasticsearch_index"] = index
        
        super().__init__(
            message=message,
            error_code=ErrorCode.ELASTICSEARCH_CONNECTION_ERROR,
            context=context,
            cause=cause,
        )


class ResourceNotFoundError(TemporalPlatformError):
    """Raised when a required resource is not found."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if resource_type is not None:
            context["resource_type"] = resource_type
        if resource_id is not None:
            context["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_NOT_FOUND_ERROR,
            context=context,
            cause=cause,
        )


class InsufficientResourcesError(TemporalPlatformError):
    """Raised when system resources are insufficient."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        required: Optional[str] = None,
        available: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if resource_type is not None:
            context["resource_type"] = resource_type
        if required is not None:
            context["required"] = required
        if available is not None:
            context["available"] = available
        
        super().__init__(
            message=message,
            error_code=ErrorCode.INSUFFICIENT_RESOURCES_ERROR,
            context=context,
            cause=cause,
        )


class AuthenticationError(TemporalPlatformError):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str,
        user_id: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if user_id is not None:
            context["user_id"] = user_id
        
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            context=context,
            cause=cause,
        )


class RateLimitError(TemporalPlatformError):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
        retry_after_seconds: Optional[int] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = {}
        if limit is not None:
            context["limit"] = limit
        if window_seconds is not None:
            context["window_seconds"] = window_seconds
        if retry_after_seconds is not None:
            context["retry_after_seconds"] = retry_after_seconds
        
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_ERROR,
            context=context,
            cause=cause,
        )
