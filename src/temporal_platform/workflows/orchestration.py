"""
Main orchestration workflows implementing Pattern 1: Orchestration.
Demonstrates parent-child workflow relationships with sequential and parallel execution.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
import structlog

from ..models.workflows import (
    WorkflowInput, WorkflowOutput, WorkflowStatus, DataBatch, 
    BatchProcessingResult, NotificationEvent, Priority, ProcessingMode,
    LongRunningOperationInput
)
from ..activities.data_processing import (
    process_batch_sequential, process_batch_parallel, validate_processing_results
)
from ..activities.long_running import process_large_dataset, monitor_system_resources
from ..activities.notifications import (
    send_webhook_notification, log_audit_event, update_metrics_dashboard
)
from ..config.settings import settings

logger = structlog.get_logger(__name__)


@workflow.defn
class DataProcessingOrchestrator:
    """
    Main orchestrator workflow that coordinates multiple child workflows.
    Implements Pattern 1: Orchestration with both sequential and parallel execution.
    """
    
    def __init__(self) -> None:
        self._workflow_input: Optional[WorkflowInput] = None
        self._batch_results: List[BatchProcessingResult] = []
        self._processing_start_time: Optional[float] = None
        
    @workflow.run
    async def run(self, workflow_input: WorkflowInput) -> WorkflowOutput:
        """
        Main orchestrator workflow execution.
        
        Args:
            workflow_input: Input parameters for the entire workflow
            
        Returns:
            WorkflowOutput with comprehensive processing results
        """
        self._workflow_input = workflow_input
        self._processing_start_time = workflow.now().timestamp()
        
        workflow_id = workflow.info().workflow_id
        
        logger.info(
            "Starting data processing orchestration",
            workflow_id=workflow_id,
            dataset_id=workflow_input.dataset_id,
            total_batches=len(workflow_input.batches),
            parallel_batches=workflow_input.parallel_batches
        )
        
        try:
            # Stage 1: Fire-and-forget audit logging
            await self._log_workflow_start(workflow_input)
            
            # Stage 2: Start system monitoring (fire-and-forget)
            monitoring_task = workflow.start_activity(
                monitor_system_resources,
                schedule_to_close_timeout=timedelta(minutes=1),
                retry_policy=RetryPolicy(maximum_attempts=2)
            )
            
            # Stage 3: Process batches (orchestration)
            if workflow_input.processing_config.get("sequential_mode", False):
                self._batch_results = await self._process_batches_sequential(workflow_input)
            else:
                self._batch_results = await self._process_batches_parallel(workflow_input)
            
            # Stage 4: Validate results
            validation_result = await workflow.execute_activity(
                validate_processing_results,
                self._batch_results,
                schedule_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=30),
                    backoff_coefficient=2.0,
                    maximum_attempts=3
                )
            )
            
            # Stage 5: Long-running post-processing (if needed)
            if workflow_input.processing_config.get("enable_large_dataset_processing", False):
                await self._execute_long_running_processing(workflow_input)
            
            # Stage 6: Send completion notifications (fire-and-forget)
            await self._send_completion_notifications(workflow_input, validation_result)
            
            # Stage 7: Update metrics (fire-and-forget) 
            await self._update_processing_metrics(workflow_input, validation_result)
            
            # Collect system monitoring results if available
            try:
                monitoring_result = await monitoring_task
                logger.debug("System monitoring completed", monitoring_result=monitoring_result)
            except Exception as e:
                logger.warning("System monitoring failed", error=str(e))
            
            # Create final workflow output
            output = self._create_workflow_output(workflow_input, validation_result)
            
            logger.info(
                "Data processing orchestration completed",
                workflow_id=workflow_id,
                status=output.status,
                successful_items=output.successful_items,
                failed_items=output.failed_items,
                processing_time_seconds=output.processing_time_seconds
            )
            
            return output
            
        except Exception as e:
            logger.error(
                "Data processing orchestration failed",
                workflow_id=workflow_id,
                dataset_id=workflow_input.dataset_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Send failure notification
            await self._send_failure_notification(workflow_input, str(e))
            
            # Create failed workflow output
            return self._create_failed_workflow_output(workflow_input, str(e))
    
    async def _process_batches_sequential(self, workflow_input: WorkflowInput) -> List[BatchProcessingResult]:
        """Process batches sequentially using child workflows."""
        batch_results = []
        
        logger.info(
            "Starting sequential batch processing",
            total_batches=len(workflow_input.batches)
        )
        
        for i, batch in enumerate(workflow_input.batches):
            logger.debug(
                "Processing batch sequentially",
                batch_index=i + 1,
                batch_id=batch.id,
                batch_size=batch.batch_size
            )
            
            # Execute child workflow for batch processing
            child_workflow_id = f"{workflow.info().workflow_id}-batch-{i+1}"
            
            batch_result = await workflow.execute_child_workflow(
                BatchProcessingWorkflow.run,
                batch,
                id=child_workflow_id,
                execution_timeout=timedelta(minutes=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(minutes=2),
                    backoff_coefficient=2.0,
                    maximum_attempts=workflow_input.processing_config.get("max_retries", 3)
                )
            )
            
            batch_results.append(batch_result)
            
            # Update progress metrics
            await workflow.start_activity(
                update_metrics_dashboard,
                "batch_processing_progress",
                (i + 1) / len(workflow_input.batches) * 100,
                {"dataset_id": workflow_input.dataset_id, "mode": "sequential"},
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=2)
            )
        
        return batch_results
    
    async def _process_batches_parallel(self, workflow_input: WorkflowInput) -> List[BatchProcessingResult]:
        """Process batches in parallel using child workflows with concurrency limits."""
        logger.info(
            "Starting parallel batch processing",
            total_batches=len(workflow_input.batches),
            max_parallel=workflow_input.parallel_batches
        )
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(workflow_input.parallel_batches)
        
        async def process_batch_with_semaphore(batch_index: int, batch: DataBatch) -> BatchProcessingResult:
            """Process batch with semaphore for concurrency control."""
            async with semaphore:
                child_workflow_id = f"{workflow.info().workflow_id}-batch-{batch_index+1}"
                
                logger.debug(
                    "Processing batch in parallel",
                    batch_index=batch_index + 1,
                    batch_id=batch.id,
                    batch_size=batch.batch_size
                )
                
                return await workflow.execute_child_workflow(
                    BatchProcessingWorkflow.run,
                    batch,
                    id=child_workflow_id,
                    execution_timeout=timedelta(minutes=30),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=5),
                        maximum_interval=timedelta(minutes=2),
                        backoff_coefficient=2.0,
                        maximum_attempts=workflow_input.processing_config.get("max_retries", 3)
                    )
                )
        
        # Execute all batches in parallel with concurrency limits
        tasks = [
            process_batch_with_semaphore(i, batch) 
            for i, batch in enumerate(workflow_input.batches)
        ]
        
        batch_results = await asyncio.gather(*tasks)
        
        return list(batch_results)
    
    async def _execute_long_running_processing(self, workflow_input: WorkflowInput) -> None:
        """Execute long-running post-processing operations."""
        logger.info("Starting long-running post-processing")
        
        # Create long-running operation input
        operation_input = LongRunningOperationInput(
            operation_type="post_processing",
            total_work_units=sum(batch.batch_size for batch in workflow_input.batches),
            work_unit_size=1000,
            enable_heartbeat=True,
            heartbeat_interval_seconds=10,
            enable_progress_updates=True,
            progress_update_interval_seconds=5,
            parameters={
                "dataset_id": workflow_input.dataset_id,
                "processing_mode": "post_processing",
                "complexity_factor": 0.5
            }
        )
        
        # Execute long-running operation
        await workflow.execute_activity(
            process_large_dataset,
            operation_input,
            schedule_to_close_timeout=timedelta(hours=2),
            heartbeat_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=10),
                maximum_interval=timedelta(minutes=5),
                backoff_coefficient=2.0,
                maximum_attempts=2
            )
        )
    
    async def _log_workflow_start(self, workflow_input: WorkflowInput) -> None:
        """Log workflow start event for audit trail."""
        workflow.start_activity(
            log_audit_event,
            "workflow_started",
            "system",
            workflow_input.dataset_id,
            "data_processing_orchestration",
            {
                "workflow_id": workflow.info().workflow_id,
                "total_batches": len(workflow_input.batches),
                "total_items": sum(batch.batch_size for batch in workflow_input.batches)
            },
            schedule_to_close_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
    
    async def _send_completion_notifications(
        self, 
        workflow_input: WorkflowInput, 
        validation_result: Dict[str, Any]
    ) -> None:
        """Send completion notifications as fire-and-forget operations."""
        if workflow_input.notification_webhook:
            notification = NotificationEvent(
                event_type="workflow_completed",
                source_workflow_id=workflow.info().workflow_id,
                event_data={
                    "dataset_id": workflow_input.dataset_id,
                    "validation_result": validation_result,
                    "processing_summary": {
                        "total_batches": len(self._batch_results),
                        "successful_items": validation_result["statistics"]["successful_items"],
                        "failed_items": validation_result["statistics"]["failed_items"],
                        "success_rate": validation_result["statistics"]["success_rate_percentage"]
                    }
                },
                priority=Priority.MEDIUM,
                target_endpoint=workflow_input.notification_webhook
            )
            
            workflow.start_activity(
                send_webhook_notification,
                notification,
                schedule_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=30),
                    maximum_attempts=3
                )
            )
    
    async def _send_failure_notification(self, workflow_input: WorkflowInput, error_message: str) -> None:
        """Send failure notification as fire-and-forget operation."""
        if workflow_input.notification_webhook:
            notification = NotificationEvent(
                event_type="workflow_failed",
                source_workflow_id=workflow.info().workflow_id,
                event_data={
                    "dataset_id": workflow_input.dataset_id,
                    "error_message": error_message,
                    "processing_summary": {
                        "total_batches": len(workflow_input.batches),
                        "completed_batches": len(self._batch_results)
                    }
                },
                priority=Priority.HIGH,
                target_endpoint=workflow_input.notification_webhook
            )
            
            workflow.start_activity(
                send_webhook_notification,
                notification,
                schedule_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )
    
    async def _update_processing_metrics(
        self, 
        workflow_input: WorkflowInput, 
        validation_result: Dict[str, Any]
    ) -> None:
        """Update processing metrics as fire-and-forget operations."""
        labels = {"dataset_id": workflow_input.dataset_id}
        
        # Update various metrics
        metrics_updates = [
            ("workflow_completed_total", 1, labels),
            ("items_processed_total", validation_result["statistics"]["total_items"], labels),
            ("items_successful_total", validation_result["statistics"]["successful_items"], labels),
            ("items_failed_total", validation_result["statistics"]["failed_items"], labels),
            ("processing_time_seconds", validation_result["statistics"]["total_processing_time_seconds"], labels),
            ("success_rate_percentage", validation_result["statistics"]["success_rate_percentage"], labels)
        ]
        
        for metric_name, metric_value, metric_labels in metrics_updates:
            workflow.start_activity(
                update_metrics_dashboard,
                metric_name,
                metric_value,
                metric_labels,
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=2)
            )
    
    def _create_workflow_output(
        self, 
        workflow_input: WorkflowInput, 
        validation_result: Dict[str, Any]
    ) -> WorkflowOutput:
        """Create successful workflow output."""
        processing_time = workflow.now().timestamp() - (self._processing_start_time or 0)
        
        return WorkflowOutput(
            workflow_id=workflow.info().workflow_id,
            dataset_id=workflow_input.dataset_id,
            status=WorkflowStatus.COMPLETED,
            total_batches=len(self._batch_results),
            successful_batches=sum(
                1 for r in self._batch_results 
                if r.successful_items == r.total_items
            ),
            failed_batches=sum(
                1 for r in self._batch_results 
                if r.successful_items < r.total_items
            ),
            total_items=validation_result["statistics"]["total_items"],
            successful_items=validation_result["statistics"]["successful_items"],
            failed_items=validation_result["statistics"]["failed_items"],
            processing_time_seconds=processing_time,
            batch_results=self._batch_results,
            summary_statistics=validation_result["statistics"]
        )
    
    def _create_failed_workflow_output(
        self, 
        workflow_input: WorkflowInput, 
        error_message: str
    ) -> WorkflowOutput:
        """Create failed workflow output."""
        processing_time = workflow.now().timestamp() - (self._processing_start_time or 0)
        
        return WorkflowOutput(
            workflow_id=workflow.info().workflow_id,
            dataset_id=workflow_input.dataset_id,
            status=WorkflowStatus.FAILED,
            total_batches=len(workflow_input.batches),
            successful_batches=0,
            failed_batches=len(workflow_input.batches),
            total_items=sum(batch.batch_size for batch in workflow_input.batches),
            successful_items=0,
            failed_items=sum(batch.batch_size for batch in workflow_input.batches),
            processing_time_seconds=processing_time,
            batch_results=self._batch_results,
            summary_statistics={},
            error_summary=error_message
        )


@workflow.defn
class BatchProcessingWorkflow:
    """
    Child workflow for processing individual batches.
    Demonstrates parent-child workflow relationships.
    """
    
    @workflow.run
    async def run(self, data_batch: DataBatch) -> BatchProcessingResult:
        """
        Process a single data batch.
        
        Args:
            data_batch: The batch of data to process
            
        Returns:
            BatchProcessingResult with processing outcome
        """
        logger.info(
            "Starting batch processing workflow",
            batch_id=data_batch.id,
            batch_size=data_batch.batch_size,
            processing_mode=data_batch.processing_mode
        )
        
        try:
            # Choose processing strategy based on batch configuration
            if data_batch.processing_mode == ProcessingMode.SEQUENTIAL:
                result = await workflow.execute_activity(
                    process_batch_sequential,
                    data_batch,
                    schedule_to_close_timeout=timedelta(
                        seconds=data_batch.batch_size * 10 + 300
                    ),  # Dynamic timeout based on batch size
                    heartbeat_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=2),
                        maximum_interval=timedelta(minutes=1),
                        backoff_coefficient=2.0,
                        maximum_attempts=settings.workflow.activity_retry_maximum_attempts
                    )
                )
            else:
                result = await workflow.execute_activity(
                    process_batch_parallel,
                    data_batch,
                    schedule_to_close_timeout=timedelta(
                        seconds=max(data_batch.batch_size * 2, 300)
                    ),  # Shorter timeout for parallel processing
                    heartbeat_timeout=timedelta(seconds=20),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=2),
                        maximum_interval=timedelta(minutes=1),
                        backoff_coefficient=2.0,
                        maximum_attempts=settings.workflow.activity_retry_maximum_attempts
                    )
                )
            
            logger.info(
                "Batch processing workflow completed",
                batch_id=data_batch.id,
                successful_items=result.successful_items,
                failed_items=result.failed_items,
                processing_time_seconds=result.processing_time_seconds
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Batch processing workflow failed",
                batch_id=data_batch.id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Create failed result
            return BatchProcessingResult(
                batch_id=data_batch.id,
                total_items=data_batch.batch_size,
                successful_items=0,
                failed_items=data_batch.batch_size,
                processing_time_seconds=0,
                item_results=[]
            )
