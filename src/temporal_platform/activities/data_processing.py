"""
Data processing activities implementing async operations with retry policies.
Demonstrates Pattern 2: Async Operations with proper timeout handling and error recovery.
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from temporalio import activity
import structlog

from ..models.workflows import (
    DataItem, DataBatch, ProcessingResult, BatchProcessingResult,
    ActivityStatus, ProcessingMode
)
from ..exceptions.core import (
    DataProcessingError, ActivityExecutionError, ActivityTimeoutError
)
from ..config.settings import settings

logger = structlog.get_logger(__name__)


@activity.defn
async def process_single_item(data_item: DataItem) -> ProcessingResult:
    """
    Process a single data item with error handling and validation.
    
    Args:
        data_item: The data item to process
        
    Returns:
        ProcessingResult with processing outcome
        
    Raises:
        DataProcessingError: When processing fails
        ActivityTimeoutError: When processing times out
    """
    start_time = time.time()
    
    try:
        logger.info(
            "Starting item processing",
            item_id=data_item.id,
            content_type=data_item.content_type,
            size_bytes=data_item.size_bytes
        )
        
        # Simulate processing with configurable delay
        processing_delay = min(data_item.size_bytes / 10000, 10)  # Max 10 seconds
        
        # Check if we have enough time before timeout
        remaining_time = activity.info().heartbeat_timeout
        if remaining_time and processing_delay > remaining_time.total_seconds():
            raise ActivityTimeoutError(
                "Processing time would exceed activity timeout",
                activity_type="process_single_item",
                timeout_seconds=remaining_time.total_seconds()
            )
        
        # Simulate async processing work
        await asyncio.sleep(processing_delay)
        
        # Send heartbeat to prevent timeout
        activity.heartbeat("Processing item", data_item.id)
        
        # Process content (example: uppercase transformation)
        processed_content = data_item.content.upper()
        
        # Validate checksum if provided
        if data_item.checksum:
            # Simulate checksum validation
            await asyncio.sleep(0.1)
            logger.debug("Checksum validated", item_id=data_item.id)
        
        processing_time = time.time() - start_time
        
        result = ProcessingResult(
            item_id=data_item.id,
            status=ActivityStatus.COMPLETED,
            processed_content=processed_content,
            processing_time_seconds=processing_time,
            output_metadata={
                "original_size": data_item.size_bytes,
                "processed_size": len(processed_content.encode('utf-8')),
                "content_type": data_item.content_type,
                "processing_method": "uppercase_transform"
            }
        )
        
        logger.info(
            "Item processing completed",
            item_id=data_item.id,
            processing_time_seconds=processing_time,
            status=result.status
        )
        
        return result
        
    except asyncio.TimeoutError as e:
        processing_time = time.time() - start_time
        error_msg = f"Item processing timed out after {processing_time:.2f} seconds"
        
        logger.error(
            error_msg,
            item_id=data_item.id,
            processing_time_seconds=processing_time,
            error=str(e)
        )
        
        return ProcessingResult(
            item_id=data_item.id,
            status=ActivityStatus.TIMEOUT,
            processing_time_seconds=processing_time,
            error_message=error_msg,
            retry_count=activity.info().attempt
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Item processing failed: {str(e)}"
        
        logger.error(
            error_msg,
            item_id=data_item.id,
            processing_time_seconds=processing_time,
            error=str(e),
            error_type=type(e).__name__
        )
        
        # Raise custom exception for retry handling
        raise DataProcessingError(
            error_msg,
            data_type="DataItem",
            cause=e
        )


@activity.defn
async def process_batch_sequential(data_batch: DataBatch) -> BatchProcessingResult:
    """
    Process a batch of data items sequentially.
    
    Args:
        data_batch: The batch of data items to process
        
    Returns:
        BatchProcessingResult with batch processing outcome
    """
    start_time = time.time()
    item_results: List[ProcessingResult] = []
    successful_count = 0
    failed_count = 0
    
    logger.info(
        "Starting sequential batch processing",
        batch_id=data_batch.id,
        batch_size=data_batch.batch_size,
        mode=data_batch.processing_mode
    )
    
    for i, item in enumerate(data_batch.items):
        try:
            # Send heartbeat with progress
            progress = f"Processing item {i+1}/{data_batch.batch_size}"
            activity.heartbeat(progress)
            
            result = await process_single_item(item)
            item_results.append(result)
            
            if result.status == ActivityStatus.COMPLETED:
                successful_count += 1
            else:
                failed_count += 1
                
        except Exception as e:
            logger.error(
                "Item processing failed in batch",
                batch_id=data_batch.id,
                item_id=item.id,
                error=str(e)
            )
            
            # Create failed result
            failed_result = ProcessingResult(
                item_id=item.id,
                status=ActivityStatus.FAILED,
                processing_time_seconds=0,
                error_message=str(e),
                retry_count=0
            )
            item_results.append(failed_result)
            failed_count += 1
    
    processing_time = time.time() - start_time
    
    batch_result = BatchProcessingResult(
        batch_id=data_batch.id,
        total_items=data_batch.batch_size,
        successful_items=successful_count,
        failed_items=failed_count,
        processing_time_seconds=processing_time,
        item_results=item_results
    )
    
    logger.info(
        "Sequential batch processing completed",
        batch_id=data_batch.id,
        successful_items=successful_count,
        failed_items=failed_count,
        processing_time_seconds=processing_time
    )
    
    return batch_result


@activity.defn
async def process_batch_parallel(data_batch: DataBatch) -> BatchProcessingResult:
    """
    Process a batch of data items in parallel with concurrency limits.
    
    Args:
        data_batch: The batch of data items to process
        
    Returns:
        BatchProcessingResult with batch processing outcome
    """
    start_time = time.time()
    
    logger.info(
        "Starting parallel batch processing",
        batch_id=data_batch.id,
        batch_size=data_batch.batch_size,
        mode=data_batch.processing_mode
    )
    
    # Create semaphore for concurrency control
    max_concurrent = min(settings.workflow.max_concurrent_activities, data_batch.batch_size)
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(item: DataItem) -> ProcessingResult:
        """Process item with semaphore for concurrency control."""
        async with semaphore:
            try:
                return await process_single_item(item)
            except Exception as e:
                logger.error(
                    "Item processing failed in parallel batch",
                    batch_id=data_batch.id,
                    item_id=item.id,
                    error=str(e)
                )
                
                return ProcessingResult(
                    item_id=item.id,
                    status=ActivityStatus.FAILED,
                    processing_time_seconds=0,
                    error_message=str(e),
                    retry_count=0
                )
    
    # Process all items in parallel
    tasks = [process_with_semaphore(item) for item in data_batch.items]
    
    # Send periodic heartbeats while waiting
    async def heartbeat_sender():
        """Send periodic heartbeats during parallel processing."""
        while not all(task.done() for task in tasks):
            completed = sum(1 for task in tasks if task.done())
            progress = f"Processing {completed}/{len(tasks)} items"
            activity.heartbeat(progress)
            await asyncio.sleep(2)  # Heartbeat every 2 seconds
    
    # Start heartbeat sender
    heartbeat_task = asyncio.create_task(heartbeat_sender())
    
    try:
        # Wait for all processing to complete
        item_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions from gather
        processed_results = []
        for i, result in enumerate(item_results):
            if isinstance(result, Exception):
                logger.error(
                    "Task failed with exception",
                    batch_id=data_batch.id,
                    item_index=i,
                    error=str(result)
                )
                processed_results.append(ProcessingResult(
                    item_id=data_batch.items[i].id,
                    status=ActivityStatus.FAILED,
                    processing_time_seconds=0,
                    error_message=str(result),
                    retry_count=0
                ))
            else:
                processed_results.append(result)
        
    finally:
        # Cancel heartbeat sender
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
    
    # Calculate results
    successful_count = sum(1 for r in processed_results if r.status == ActivityStatus.COMPLETED)
    failed_count = len(processed_results) - successful_count
    processing_time = time.time() - start_time
    
    batch_result = BatchProcessingResult(
        batch_id=data_batch.id,
        total_items=data_batch.batch_size,
        successful_items=successful_count,
        failed_items=failed_count,
        processing_time_seconds=processing_time,
        item_results=processed_results
    )
    
    logger.info(
        "Parallel batch processing completed",
        batch_id=data_batch.id,
        successful_items=successful_count,
        failed_items=failed_count,
        processing_time_seconds=processing_time,
        max_concurrent=max_concurrent
    )
    
    return batch_result


@activity.defn
async def validate_processing_results(
    batch_results: List[BatchProcessingResult]
) -> Dict[str, Any]:
    """
    Validate and aggregate processing results from multiple batches.
    
    Args:
        batch_results: List of batch processing results to validate
        
    Returns:
        Dictionary with validation results and aggregated statistics
    """
    start_time = time.time()
    
    logger.info(
        "Starting batch results validation",
        batch_count=len(batch_results)
    )
    
    total_items = sum(batch.total_items for batch in batch_results)
    total_successful = sum(batch.successful_items for batch in batch_results)
    total_failed = sum(batch.failed_items for batch in batch_results)
    total_processing_time = sum(batch.processing_time_seconds for batch in batch_results)
    
    # Validate consistency
    validation_errors = []
    
    for batch in batch_results:
        # Check if items count matches
        if batch.total_items != len(batch.item_results):
            validation_errors.append(
                f"Batch {batch.batch_id}: item count mismatch"
            )
        
        # Check if success/failure counts match
        actual_successful = sum(
            1 for r in batch.item_results 
            if r.status == ActivityStatus.COMPLETED
        )
        if actual_successful != batch.successful_items:
            validation_errors.append(
                f"Batch {batch.batch_id}: successful count mismatch"
            )
    
    # Calculate statistics
    avg_processing_time = total_processing_time / len(batch_results) if batch_results else 0
    success_rate = (total_successful / total_items * 100) if total_items > 0 else 0
    
    # Calculate throughput
    if total_processing_time > 0:
        throughput = total_items / total_processing_time
    else:
        throughput = 0
    
    validation_time = time.time() - start_time
    
    results = {
        "validation_successful": len(validation_errors) == 0,
        "validation_errors": validation_errors,
        "validation_time_seconds": validation_time,
        "statistics": {
            "total_batches": len(batch_results),
            "total_items": total_items,
            "successful_items": total_successful,
            "failed_items": total_failed,
            "success_rate_percentage": success_rate,
            "total_processing_time_seconds": total_processing_time,
            "average_batch_processing_time_seconds": avg_processing_time,
            "throughput_items_per_second": throughput
        }
    }
    
    logger.info(
        "Batch results validation completed",
        validation_successful=results["validation_successful"],
        error_count=len(validation_errors),
        total_items=total_items,
        success_rate=success_rate,
        validation_time_seconds=validation_time
    )
    
    return results
