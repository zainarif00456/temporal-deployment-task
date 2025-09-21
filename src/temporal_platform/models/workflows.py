"""
Pydantic v2 data models for workflow inputs, outputs, and state management.
All models include comprehensive validation and serialization support.
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, validator, ConfigDict
from pydantic.types import PositiveInt, NonNegativeFloat


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ActivityStatus(str, Enum):
    """Activity execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    TIMEOUT = "timeout"


class ProcessingMode(str, Enum):
    """Data processing mode."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BATCH = "batch"


class Priority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaseWorkflowModel(BaseModel):
    """Base model for all workflow-related data structures."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        extra="forbid",
        str_strip_whitespace=True,
    )
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class DataItem(BaseWorkflowModel):
    """Individual data item for processing."""
    
    content: str = Field(..., min_length=1, description="Item content")
    content_type: str = Field(default="text/plain", description="Content MIME type")
    size_bytes: PositiveInt = Field(..., description="Content size in bytes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    checksum: Optional[str] = Field(default=None, description="Content checksum for integrity")
    
    @validator("content_type")
    def validate_content_type(cls, v: str) -> str:
        """Validate content type format."""
        if "/" not in v:
            raise ValueError("Content type must be in format 'type/subtype'")
        return v.lower()


class DataBatch(BaseWorkflowModel):
    """Batch of data items for processing."""
    
    items: List[DataItem] = Field(..., min_items=1, description="Data items in the batch")
    batch_size: PositiveInt = Field(..., description="Number of items in the batch")
    total_size_bytes: PositiveInt = Field(..., description="Total batch size in bytes")
    processing_mode: ProcessingMode = Field(default=ProcessingMode.PARALLEL, description="Processing mode")
    priority: Priority = Field(default=Priority.MEDIUM, description="Batch processing priority")
    
    @validator("batch_size")
    def validate_batch_size(cls, v: int, values: Dict[str, Any]) -> int:
        """Validate batch size matches items count."""
        if "items" in values and len(values["items"]) != v:
            raise ValueError("Batch size must match the number of items")
        return v
    
    @validator("total_size_bytes")
    def validate_total_size(cls, v: int, values: Dict[str, Any]) -> int:
        """Validate total size matches sum of item sizes."""
        if "items" in values:
            actual_size = sum(item.size_bytes for item in values["items"])
            if actual_size != v:
                raise ValueError("Total size must match the sum of item sizes")
        return v


class ProcessingResult(BaseWorkflowModel):
    """Result of data processing operation."""
    
    item_id: str = Field(..., description="Processed item ID")
    status: ActivityStatus = Field(..., description="Processing status")
    processed_content: Optional[str] = Field(default=None, description="Processed content")
    processing_time_seconds: NonNegativeFloat = Field(..., description="Processing duration")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    retry_count: int = Field(default=0, ge=0, description="Number of retries performed")
    output_metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata")


class BatchProcessingResult(BaseWorkflowModel):
    """Result of batch processing operation."""
    
    batch_id: str = Field(..., description="Processed batch ID")
    total_items: PositiveInt = Field(..., description="Total number of items processed")
    successful_items: int = Field(..., ge=0, description="Number of successfully processed items")
    failed_items: int = Field(..., ge=0, description="Number of failed items")
    processing_time_seconds: NonNegativeFloat = Field(..., description="Total processing duration")
    item_results: List[ProcessingResult] = Field(..., description="Individual item results")
    
    @validator("successful_items")
    def validate_successful_items(cls, v: int, values: Dict[str, Any]) -> int:
        """Validate successful items count."""
        if "total_items" in values and v > values["total_items"]:
            raise ValueError("Successful items cannot exceed total items")
        return v
    
    @validator("failed_items")
    def validate_failed_items(cls, v: int, values: Dict[str, Any]) -> int:
        """Validate failed items count."""
        if "total_items" in values and "successful_items" in values:
            total = values["total_items"]
            successful = values["successful_items"]
            if v != total - successful:
                raise ValueError("Failed items must equal total minus successful")
        return v


class WorkflowInput(BaseWorkflowModel):
    """Input parameters for workflow execution."""
    
    dataset_id: str = Field(..., description="Dataset identifier")
    batches: List[DataBatch] = Field(..., min_items=1, description="Data batches to process")
    processing_config: Dict[str, Any] = Field(default_factory=dict, description="Processing configuration")
    execution_timeout_seconds: PositiveInt = Field(default=3600, description="Workflow execution timeout")
    parallel_batches: PositiveInt = Field(default=5, description="Number of parallel batch processors")
    enable_retry: bool = Field(default=True, description="Enable retry on failure")
    notification_webhook: Optional[str] = Field(default=None, description="Webhook URL for notifications")


class WorkflowOutput(BaseWorkflowModel):
    """Output result of workflow execution."""
    
    workflow_id: str = Field(..., description="Workflow execution ID")
    dataset_id: str = Field(..., description="Processed dataset ID")
    status: WorkflowStatus = Field(..., description="Final workflow status")
    total_batches: PositiveInt = Field(..., description="Total number of batches processed")
    successful_batches: int = Field(..., ge=0, description="Number of successful batches")
    failed_batches: int = Field(..., ge=0, description="Number of failed batches")
    total_items: PositiveInt = Field(..., description="Total number of items processed")
    successful_items: int = Field(..., ge=0, description="Number of successful items")
    failed_items: int = Field(..., ge=0, description="Number of failed items")
    processing_time_seconds: NonNegativeFloat = Field(..., description="Total processing duration")
    batch_results: List[BatchProcessingResult] = Field(..., description="Individual batch results")
    summary_statistics: Dict[str, Any] = Field(default_factory=dict, description="Processing statistics")
    error_summary: Optional[str] = Field(default=None, description="Error summary if failed")


class ActivityInput(BaseWorkflowModel):
    """Generic activity input parameters."""
    
    activity_type: str = Field(..., description="Type of activity to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Activity-specific parameters")
    timeout_seconds: PositiveInt = Field(default=300, description="Activity execution timeout")
    retry_policy: Dict[str, Any] = Field(default_factory=dict, description="Retry policy configuration")


class ActivityOutput(BaseWorkflowModel):
    """Generic activity output result."""
    
    activity_id: str = Field(..., description="Activity execution ID")
    activity_type: str = Field(..., description="Type of activity executed")
    status: ActivityStatus = Field(..., description="Activity execution status")
    result: Dict[str, Any] = Field(default_factory=dict, description="Activity result data")
    execution_time_seconds: NonNegativeFloat = Field(..., description="Activity execution duration")
    retry_count: int = Field(default=0, ge=0, description="Number of retries performed")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Error details if failed")


class LongRunningOperationInput(BaseWorkflowModel):
    """Input for long-running operations with progress tracking."""
    
    operation_type: str = Field(..., description="Type of long-running operation")
    total_work_units: PositiveInt = Field(..., description="Total number of work units")
    work_unit_size: PositiveInt = Field(default=1000, description="Size of each work unit")
    enable_heartbeat: bool = Field(default=True, description="Enable heartbeat reporting")
    heartbeat_interval_seconds: PositiveInt = Field(default=10, description="Heartbeat interval")
    enable_progress_updates: bool = Field(default=True, description="Enable progress updates")
    progress_update_interval_seconds: PositiveInt = Field(default=5, description="Progress update interval")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation-specific parameters")


class ProgressUpdate(BaseWorkflowModel):
    """Progress update for long-running operations."""
    
    operation_id: str = Field(..., description="Operation ID")
    completed_work_units: int = Field(..., ge=0, description="Completed work units")
    total_work_units: PositiveInt = Field(..., description="Total work units")
    progress_percentage: float = Field(..., ge=0, le=100, description="Progress percentage")
    estimated_remaining_seconds: Optional[float] = Field(default=None, description="ETA in seconds")
    current_stage: str = Field(default="processing", description="Current processing stage")
    throughput_units_per_second: NonNegativeFloat = Field(..., description="Processing throughput")
    
    @validator("progress_percentage")
    def validate_progress_percentage(cls, v: float, values: Dict[str, Any]) -> float:
        """Validate progress percentage calculation."""
        if "completed_work_units" in values and "total_work_units" in values:
            completed = values["completed_work_units"]
            total = values["total_work_units"]
            expected = (completed / total) * 100
            if abs(v - expected) > 0.1:  # Allow small floating point differences
                raise ValueError("Progress percentage must match completed/total ratio")
        return v


class LongRunningOperationOutput(BaseWorkflowModel):
    """Output for long-running operations."""
    
    operation_id: str = Field(..., description="Operation ID")
    operation_type: str = Field(..., description="Type of operation")
    status: ActivityStatus = Field(..., description="Operation status")
    total_work_units: PositiveInt = Field(..., description="Total work units")
    completed_work_units: int = Field(..., ge=0, description="Completed work units")
    failed_work_units: int = Field(..., ge=0, description="Failed work units")
    execution_time_seconds: NonNegativeFloat = Field(..., description="Total execution time")
    average_throughput: NonNegativeFloat = Field(..., description="Average throughput")
    final_result: Dict[str, Any] = Field(default_factory=dict, description="Final operation result")
    progress_history: List[ProgressUpdate] = Field(default_factory=list, description="Progress update history")


class NotificationEvent(BaseWorkflowModel):
    """Notification event for fire-and-forget operations."""
    
    event_type: str = Field(..., description="Type of notification event")
    source_workflow_id: str = Field(..., description="Source workflow ID")
    event_data: Dict[str, Any] = Field(default_factory=dict, description="Event data payload")
    priority: Priority = Field(default=Priority.MEDIUM, description="Event priority")
    delivery_method: str = Field(default="webhook", description="Notification delivery method")
    target_endpoint: str = Field(..., description="Target endpoint for notification")
    retry_policy: Dict[str, Any] = Field(default_factory=dict, description="Retry policy for delivery")


class HealthCheckResult(BaseWorkflowModel):
    """Health check result for system monitoring."""
    
    service_name: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    response_time_ms: NonNegativeFloat = Field(..., description="Response time in milliseconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional health details")
    dependencies: List[Dict[str, Any]] = Field(default_factory=list, description="Dependency health status")
