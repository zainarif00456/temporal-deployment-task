"""
Long-running operations activities implementing Pattern 4.
Demonstrates heartbeat reporting and progress monitoring for large dataset processing.
"""
import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from temporalio import activity
import structlog

from ..models.workflows import (
    LongRunningOperationInput, LongRunningOperationOutput, ProgressUpdate,
    ActivityStatus
)
from ..exceptions.core import (
    ActivityExecutionError, ActivityTimeoutError, InsufficientResourcesError
)
from ..config.settings import settings

logger = structlog.get_logger(__name__)


@activity.defn
async def process_large_dataset(
    operation_input: LongRunningOperationInput
) -> LongRunningOperationOutput:
    """
    Process a large dataset with heartbeat reporting and progress updates.
    Implements Pattern 4: Long-Running Operations with progress monitoring.
    
    Args:
        operation_input: Configuration for the long-running operation
        
    Returns:
        LongRunningOperationOutput with final results and progress history
        
    Raises:
        ActivityExecutionError: When operation fails
        ActivityTimeoutError: When operation times out
        InsufficientResourcesError: When system resources are insufficient
    """
    start_time = time.time()
    progress_history: List[ProgressUpdate] = []
    
    logger.info(
        "Starting large dataset processing",
        operation_id=operation_input.id,
        operation_type=operation_input.operation_type,
        total_work_units=operation_input.total_work_units,
        work_unit_size=operation_input.work_unit_size
    )
    
    try:
        # Initialize progress tracking
        completed_units = 0
        failed_units = 0
        last_progress_update = time.time()
        last_heartbeat = time.time()
        
        # Calculate work unit batches
        work_units_per_batch = min(operation_input.work_unit_size, 1000)
        total_batches = (operation_input.total_work_units + work_units_per_batch - 1) // work_units_per_batch
        
        logger.info(
            "Dataset processing configuration",
            operation_id=operation_input.id,
            work_units_per_batch=work_units_per_batch,
            total_batches=total_batches
        )
        
        # Process work units in batches
        for batch_idx in range(total_batches):
            batch_start_time = time.time()
            
            # Calculate work units in this batch
            units_in_batch = min(
                work_units_per_batch,
                operation_input.total_work_units - completed_units
            )
            
            logger.debug(
                "Processing batch",
                operation_id=operation_input.id,
                batch_idx=batch_idx + 1,
                total_batches=total_batches,
                units_in_batch=units_in_batch
            )
            
            # Simulate batch processing
            try:
                await _process_work_unit_batch(
                    operation_input, 
                    units_in_batch, 
                    batch_idx
                )
                completed_units += units_in_batch
                
            except Exception as e:
                logger.error(
                    "Batch processing failed",
                    operation_id=operation_input.id,
                    batch_idx=batch_idx + 1,
                    error=str(e)
                )
                failed_units += units_in_batch
                # Continue processing other batches
            
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            # Send heartbeat if enabled and interval reached
            if (operation_input.enable_heartbeat and 
                current_time - last_heartbeat >= operation_input.heartbeat_interval_seconds):
                
                progress_msg = (
                    f"Processed {completed_units}/{operation_input.total_work_units} "
                    f"work units ({failed_units} failed)"
                )
                activity.heartbeat(progress_msg)
                last_heartbeat = current_time
                
                logger.debug(
                    "Heartbeat sent",
                    operation_id=operation_input.id,
                    completed_units=completed_units,
                    failed_units=failed_units
                )
            
            # Send progress update if enabled and interval reached
            if (operation_input.enable_progress_updates and 
                current_time - last_progress_update >= operation_input.progress_update_interval_seconds):
                
                # Calculate progress metrics
                progress_percentage = (completed_units / operation_input.total_work_units) * 100
                throughput = completed_units / elapsed_time if elapsed_time > 0 else 0
                
                # Estimate remaining time
                remaining_units = operation_input.total_work_units - completed_units
                eta_seconds = remaining_units / throughput if throughput > 0 else None
                
                progress_update = ProgressUpdate(
                    operation_id=operation_input.id,
                    completed_work_units=completed_units,
                    total_work_units=operation_input.total_work_units,
                    progress_percentage=progress_percentage,
                    estimated_remaining_seconds=eta_seconds,
                    current_stage=f"Batch {batch_idx + 1}/{total_batches}",
                    throughput_units_per_second=throughput
                )
                
                progress_history.append(progress_update)
                last_progress_update = current_time
                
                logger.info(
                    "Progress update",
                    operation_id=operation_input.id,
                    progress_percentage=progress_percentage,
                    completed_units=completed_units,
                    throughput=throughput,
                    eta_seconds=eta_seconds
                )
            
            # Check for activity timeout
            activity_info = activity.info()
            if activity_info.heartbeat_timeout:
                remaining_timeout = activity_info.heartbeat_timeout.total_seconds()
                if remaining_timeout < operation_input.heartbeat_interval_seconds:
                    logger.warning(
                        "Approaching activity timeout",
                        operation_id=operation_input.id,
                        remaining_timeout_seconds=remaining_timeout
                    )
        
        # Final processing statistics
        total_processing_time = time.time() - start_time
        average_throughput = completed_units / total_processing_time if total_processing_time > 0 else 0
        
        # Determine final status
        if failed_units == 0:
            final_status = ActivityStatus.COMPLETED
        elif completed_units == 0:
            final_status = ActivityStatus.FAILED
        else:
            final_status = ActivityStatus.COMPLETED  # Partial success
        
        # Create final result
        final_result = {
            "processing_summary": {
                "total_batches_processed": total_batches,
                "successful_units": completed_units,
                "failed_units": failed_units,
                "success_rate": (completed_units / operation_input.total_work_units) * 100,
                "average_batch_time_seconds": total_processing_time / total_batches,
            },
            "performance_metrics": {
                "total_processing_time_seconds": total_processing_time,
                "average_throughput_units_per_second": average_throughput,
                "peak_throughput_units_per_second": max(
                    (p.throughput_units_per_second for p in progress_history), 
                    default=0
                ),
            },
            "operation_metadata": operation_input.parameters
        }
        
        output = LongRunningOperationOutput(
            operation_id=operation_input.id,
            operation_type=operation_input.operation_type,
            status=final_status,
            total_work_units=operation_input.total_work_units,
            completed_work_units=completed_units,
            failed_work_units=failed_units,
            execution_time_seconds=total_processing_time,
            average_throughput=average_throughput,
            final_result=final_result,
            progress_history=progress_history
        )
        
        logger.info(
            "Large dataset processing completed",
            operation_id=operation_input.id,
            status=final_status,
            completed_units=completed_units,
            failed_units=failed_units,
            processing_time_seconds=total_processing_time,
            average_throughput=average_throughput
        )
        
        return output
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Large dataset processing failed: {str(e)}"
        
        logger.error(
            error_msg,
            operation_id=operation_input.id,
            processing_time_seconds=processing_time,
            error=str(e),
            error_type=type(e).__name__
        )
        
        # Create failed result
        output = LongRunningOperationOutput(
            operation_id=operation_input.id,
            operation_type=operation_input.operation_type,
            status=ActivityStatus.FAILED,
            total_work_units=operation_input.total_work_units,
            completed_work_units=completed_units if 'completed_units' in locals() else 0,
            failed_work_units=operation_input.total_work_units,
            execution_time_seconds=processing_time,
            average_throughput=0,
            final_result={"error": error_msg, "error_type": type(e).__name__},
            progress_history=progress_history if 'progress_history' in locals() else []
        )
        
        return output


async def _process_work_unit_batch(
    operation_input: LongRunningOperationInput,
    units_in_batch: int,
    batch_idx: int
) -> None:
    """
    Process a batch of work units with simulated work and error injection.
    
    Args:
        operation_input: Operation configuration
        units_in_batch: Number of units in this batch
        batch_idx: Index of the current batch
        
    Raises:
        Exception: Simulated processing errors
    """
    # Simulate processing time based on work unit size and complexity
    base_processing_time = 0.1  # Base time per unit
    complexity_factor = operation_input.parameters.get("complexity_factor", 1.0)
    processing_time = base_processing_time * units_in_batch * complexity_factor
    
    # Add some randomness to simulate real-world variability
    import random
    processing_time *= random.uniform(0.8, 1.2)
    
    # Simulate occasional failures (5% failure rate)
    if random.random() < 0.05:
        error_types = [
            "Network timeout",
            "Memory allocation failed",
            "Database connection lost",
            "Invalid data format",
            "Resource temporarily unavailable"
        ]
        raise Exception(f"Batch processing failed: {random.choice(error_types)}")
    
    # Simulate CPU-intensive work with periodic yielding
    chunk_size = 0.5  # Process in 0.5 second chunks
    chunks = int(processing_time / chunk_size)
    
    for i in range(chunks):
        await asyncio.sleep(chunk_size)
        
        # Yield control periodically
        if i % 5 == 0:
            await asyncio.sleep(0)
    
    # Handle remaining time
    remaining_time = processing_time - (chunks * chunk_size)
    if remaining_time > 0:
        await asyncio.sleep(remaining_time)


@activity.defn
async def monitor_system_resources() -> Dict[str, Any]:
    """
    Monitor system resources during long-running operations.
    Provides resource utilization metrics for capacity planning.
    
    Returns:
        Dictionary with system resource metrics
    """
    start_time = time.time()
    
    try:
        import psutil
        
        # Get CPU utilization
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Get memory utilization  
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)
        
        # Get disk utilization
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_free_gb = disk.free / (1024**3)
        
        # Get network I/O
        network = psutil.net_io_counters()
        
        monitoring_time = time.time() - start_time
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring_time_seconds": monitoring_time,
            "cpu": {
                "utilization_percent": cpu_percent,
                "core_count": cpu_count,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            },
            "memory": {
                "utilization_percent": memory_percent,
                "total_gb": memory.total / (1024**3),
                "available_gb": memory_available_gb,
                "used_gb": memory.used / (1024**3)
            },
            "disk": {
                "utilization_percent": disk_percent,
                "total_gb": disk.total / (1024**3),
                "free_gb": disk_free_gb,
                "used_gb": disk.used / (1024**3)
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_received": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_received": network.packets_recv
            }
        }
        
        logger.debug(
            "System resource monitoring completed",
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            monitoring_time_seconds=monitoring_time
        )
        
        return metrics
        
    except ImportError:
        # Fallback when psutil is not available
        logger.warning("psutil not available, using mock resource metrics")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring_time_seconds": time.time() - start_time,
            "cpu": {"utilization_percent": 50.0, "core_count": 4},
            "memory": {
                "utilization_percent": 60.0,
                "total_gb": 16.0,
                "available_gb": 6.4,
                "used_gb": 9.6
            },
            "disk": {
                "utilization_percent": 70.0,
                "total_gb": 500.0,
                "free_gb": 150.0,
                "used_gb": 350.0
            },
            "network": {
                "bytes_sent": 1024*1024*100,  # 100 MB
                "bytes_received": 1024*1024*200,  # 200 MB
                "packets_sent": 10000,
                "packets_received": 15000
            }
        }
    
    except Exception as e:
        logger.error(
            "System resource monitoring failed",
            error=str(e),
            error_type=type(e).__name__
        )
        
        raise ActivityExecutionError(
            f"Resource monitoring failed: {str(e)}",
            activity_type="monitor_system_resources",
            cause=e
        )


@activity.defn
async def cleanup_processing_artifacts(operation_id: str) -> Dict[str, Any]:
    """
    Clean up temporary files and resources after long-running operations.
    
    Args:
        operation_id: The operation ID to clean up
        
    Returns:
        Dictionary with cleanup results
    """
    start_time = time.time()
    
    logger.info(
        "Starting cleanup of processing artifacts",
        operation_id=operation_id
    )
    
    try:
        # Simulate cleanup operations
        cleanup_tasks = [
            "Remove temporary files",
            "Clear cache entries", 
            "Release memory buffers",
            "Close database connections",
            "Update processing logs"
        ]
        
        completed_tasks = []
        failed_tasks = []
        
        for task in cleanup_tasks:
            try:
                # Simulate cleanup work
                await asyncio.sleep(0.1)
                completed_tasks.append(task)
                
                logger.debug(
                    "Cleanup task completed",
                    operation_id=operation_id,
                    task=task
                )
                
            except Exception as e:
                failed_tasks.append({"task": task, "error": str(e)})
                logger.error(
                    "Cleanup task failed",
                    operation_id=operation_id,
                    task=task,
                    error=str(e)
                )
        
        cleanup_time = time.time() - start_time
        
        result = {
            "operation_id": operation_id,
            "cleanup_time_seconds": cleanup_time,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "total_tasks": len(cleanup_tasks),
            "success_rate": len(completed_tasks) / len(cleanup_tasks) * 100
        }
        
        logger.info(
            "Cleanup completed",
            operation_id=operation_id,
            completed_tasks=len(completed_tasks),
            failed_tasks=len(failed_tasks),
            cleanup_time_seconds=cleanup_time
        )
        
        return result
        
    except Exception as e:
        cleanup_time = time.time() - start_time
        error_msg = f"Cleanup failed: {str(e)}"
        
        logger.error(
            error_msg,
            operation_id=operation_id,
            cleanup_time_seconds=cleanup_time,
            error=str(e)
        )
        
        return {
            "operation_id": operation_id,
            "cleanup_time_seconds": cleanup_time,
            "error": error_msg,
            "completed_tasks": [],
            "failed_tasks": cleanup_tasks,
            "total_tasks": len(cleanup_tasks) if 'cleanup_tasks' in locals() else 0,
            "success_rate": 0.0
        }
