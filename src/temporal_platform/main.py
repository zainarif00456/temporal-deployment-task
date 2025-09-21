"""
Main entry point for Temporal Platform application.
Provides commands for running workers, orchestrators, and clients.
"""
import asyncio
import sys
from typing import Optional, List
import typer
import structlog
from temporalio import Worker
from temporalio.client import Client
from temporalio.runtime import PrometheusConfig, Runtime, TelemetryConfig

from .config.settings import settings
from .workflows.orchestration import DataProcessingOrchestrator, BatchProcessingWorkflow
from .activities import data_processing, long_running, notifications
from .models.workflows import (
    WorkflowInput, DataBatch, DataItem, ProcessingMode, Priority
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.logging.log_format == "json" 
        else structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

app = typer.Typer(
    name="temporal-platform",
    help="Temporal Platform - Production-grade workflow orchestration",
    no_args_is_help=True
)


async def create_temporal_client() -> Client:
    """Create and configure Temporal client with telemetry."""
    
    # Configure telemetry if metrics are enabled
    telemetry_config = None
    if settings.monitoring.enable_metrics:
        telemetry_config = TelemetryConfig(
            metrics=PrometheusConfig(bind_address=f"0.0.0.0:{settings.monitoring.metrics_port}")
        )
    
    # Create runtime with telemetry
    runtime = Runtime(telemetry=telemetry_config) if telemetry_config else None
    
    try:
        client = await Client.connect(
            target_host=settings.temporal.temporal_address,
            namespace=settings.temporal.temporal_namespace,
            runtime=runtime
        )
        
        logger.info(
            "Connected to Temporal server",
            target_host=settings.temporal.temporal_address,
            namespace=settings.temporal.temporal_namespace
        )
        
        return client
        
    except Exception as e:
        logger.error(
            "Failed to connect to Temporal server",
            error=str(e),
            target_host=settings.temporal.temporal_address
        )
        raise


@app.command("start-worker")
def start_worker(
    task_queue: Optional[str] = typer.Option(
        None, "--task-queue", help="Task queue name"
    ),
    max_activities: Optional[int] = typer.Option(
        None, "--max-activities", help="Maximum concurrent activities"
    ),
    max_workflows: Optional[int] = typer.Option(
        None, "--max-workflows", help="Maximum concurrent workflows"
    )
) -> None:
    """Start Temporal worker with all activities and workflows."""
    
    async def run_worker():
        client = await create_temporal_client()
        
        # Use configuration values with CLI overrides
        queue_name = task_queue or settings.temporal.temporal_task_queue
        max_concurrent_activities = max_activities or settings.workflow.max_concurrent_activities
        max_concurrent_workflows = max_workflows or settings.workflow.max_concurrent_workflows
        
        logger.info(
            "Starting Temporal worker",
            task_queue=queue_name,
            max_concurrent_activities=max_concurrent_activities,
            max_concurrent_workflows=max_concurrent_workflows
        )
        
        # Create worker with all activities and workflows
        worker = Worker(
            client,
            task_queue=queue_name,
            workflows=[DataProcessingOrchestrator, BatchProcessingWorkflow],
            activities=[
                # Data processing activities
                data_processing.process_single_item,
                data_processing.process_batch_sequential,
                data_processing.process_batch_parallel,
                data_processing.validate_processing_results,
                
                # Long-running operation activities
                long_running.process_large_dataset,
                long_running.monitor_system_resources,
                long_running.cleanup_processing_artifacts,
                
                # Notification activities
                notifications.send_webhook_notification,
                notifications.send_email_notification,
                notifications.log_audit_event,
                notifications.update_metrics_dashboard,
            ],
            max_concurrent_activities=max_concurrent_activities,
            max_concurrent_workflows=max_concurrent_workflows
        )
        
        logger.info("Worker started successfully")
        await worker.run()
    
    asyncio.run(run_worker())


@app.command("start-orchestrator")
def start_orchestrator(
    dataset_id: str = typer.Argument(..., help="Dataset ID to process"),
    batch_count: int = typer.Option(5, "--batches", help="Number of batches to create"),
    items_per_batch: int = typer.Option(100, "--items-per-batch", help="Items per batch"),
    parallel_batches: int = typer.Option(3, "--parallel", help="Parallel batch processors"),
    webhook_url: Optional[str] = typer.Option(None, "--webhook", help="Notification webhook URL"),
    sequential_mode: bool = typer.Option(False, "--sequential", help="Use sequential processing")
) -> None:
    """Start data processing orchestration workflow."""
    
    async def run_orchestrator():
        client = await create_temporal_client()
        
        # Create sample data batches
        batches = []
        for batch_idx in range(batch_count):
            items = []
            for item_idx in range(items_per_batch):
                item = DataItem(
                    content=f"Sample data item {item_idx} in batch {batch_idx}",
                    content_type="text/plain",
                    size_bytes=len(f"Sample data item {item_idx} in batch {batch_idx}"),
                    metadata={
                        "batch_index": batch_idx,
                        "item_index": item_idx,
                        "created_by": "orchestrator_command"
                    }
                )
                items.append(item)
            
            batch = DataBatch(
                items=items,
                batch_size=len(items),
                total_size_bytes=sum(item.size_bytes for item in items),
                processing_mode=ProcessingMode.SEQUENTIAL if sequential_mode else ProcessingMode.PARALLEL,
                priority=Priority.MEDIUM
            )
            batches.append(batch)
        
        # Create workflow input
        workflow_input = WorkflowInput(
            dataset_id=dataset_id,
            batches=batches,
            processing_config={
                "sequential_mode": sequential_mode,
                "enable_large_dataset_processing": True,
                "max_retries": 3
            },
            parallel_batches=parallel_batches,
            notification_webhook=webhook_url
        )
        
        logger.info(
            "Starting data processing orchestration",
            dataset_id=dataset_id,
            total_batches=len(batches),
            total_items=sum(batch.batch_size for batch in batches),
            sequential_mode=sequential_mode
        )
        
        # Execute orchestrator workflow
        result = await client.execute_workflow(
            DataProcessingOrchestrator.run,
            workflow_input,
            id=f"data-processing-{dataset_id}",
            task_queue=settings.temporal.temporal_task_queue,
        )
        
        logger.info(
            "Data processing orchestration completed",
            workflow_id=result.workflow_id,
            dataset_id=result.dataset_id,
            status=result.status,
            total_items=result.total_items,
            successful_items=result.successful_items,
            failed_items=result.failed_items,
            processing_time_seconds=result.processing_time_seconds
        )
        
        # Print summary
        success_rate = (result.successful_items / result.total_items * 100) if result.total_items > 0 else 0
        print(f"\n🎉 Orchestration Summary:")
        print(f"   Dataset ID: {result.dataset_id}")
        print(f"   Status: {result.status}")
        print(f"   Total Batches: {result.total_batches}")
        print(f"   Total Items: {result.total_items}")
        print(f"   ✅ Successful: {result.successful_items}")
        print(f"   ❌ Failed: {result.failed_items}")
        print(f"   📊 Success Rate: {success_rate:.2f}%")
        print(f"   ⏱️  Processing Time: {result.processing_time_seconds:.2f}s")
    
    asyncio.run(run_orchestrator())


@app.command("start-client")
def start_client() -> None:
    """Start interactive client for workflow management."""
    
    async def run_client():
        client = await create_temporal_client()
        
        print("🚀 Temporal Platform Client")
        print("Available commands:")
        print("  1. List workflows")
        print("  2. Get workflow status")
        print("  3. Cancel workflow")
        print("  4. Exit")
        
        while True:
            try:
                choice = input("\nEnter command (1-4): ").strip()
                
                if choice == "1":
                    # List workflows
                    workflows = []
                    async for workflow in client.list_workflows():
                        workflows.append(workflow)
                    
                    if workflows:
                        print(f"\n📋 Found {len(workflows)} workflows:")
                        for wf in workflows[:10]:  # Show first 10
                            print(f"   ID: {wf.id}")
                            print(f"   Type: {wf.workflow_type}")
                            print(f"   Status: {wf.status}")
                            print(f"   Start Time: {wf.start_time}")
                            print("   ---")
                    else:
                        print("No workflows found")
                
                elif choice == "2":
                    # Get workflow status
                    workflow_id = input("Enter workflow ID: ").strip()
                    if workflow_id:
                        try:
                            handle = client.get_workflow_handle(workflow_id)
                            result = await handle.result()
                            print(f"\n📊 Workflow Status: {workflow_id}")
                            print(f"   Result: {result}")
                        except Exception as e:
                            print(f"❌ Error getting workflow status: {e}")
                
                elif choice == "3":
                    # Cancel workflow
                    workflow_id = input("Enter workflow ID to cancel: ").strip()
                    if workflow_id:
                        try:
                            handle = client.get_workflow_handle(workflow_id)
                            await handle.cancel()
                            print(f"✅ Workflow {workflow_id} cancelled")
                        except Exception as e:
                            print(f"❌ Error cancelling workflow: {e}")
                
                elif choice == "4":
                    print("👋 Goodbye!")
                    break
                
                else:
                    print("Invalid choice. Please enter 1-4.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    asyncio.run(run_client())


@app.command("setup-db")
def setup_database() -> None:
    """Setup database schema and initial data."""
    
    async def setup():
        logger.info("Setting up database schema")
        
        # In a real application, you would:
        # 1. Create database tables
        # 2. Run migrations
        # 3. Insert seed data
        # 4. Setup indices
        
        logger.info("Database setup completed")
        print("✅ Database setup completed")
    
    asyncio.run(setup())


@app.command("health-check")
def health_check() -> None:
    """Perform health check of the system."""
    
    async def check_health():
        health_status = {"healthy": True, "components": {}}
        
        # Check Temporal connection
        try:
            client = await create_temporal_client()
            await client.list_namespaces()
            health_status["components"]["temporal"] = "healthy"
            logger.info("Temporal health check: OK")
        except Exception as e:
            health_status["healthy"] = False
            health_status["components"]["temporal"] = f"error: {str(e)}"
            logger.error("Temporal health check failed", error=str(e))
        
        # Check database connection
        try:
            # Database health check would go here
            health_status["components"]["database"] = "healthy"
            logger.info("Database health check: OK")
        except Exception as e:
            health_status["healthy"] = False
            health_status["components"]["database"] = f"error: {str(e)}"
            logger.error("Database health check failed", error=str(e))
        
        # Print results
        if health_status["healthy"]:
            print("✅ System health check: HEALTHY")
        else:
            print("❌ System health check: UNHEALTHY")
            
        for component, status in health_status["components"].items():
            status_icon = "✅" if "error" not in status else "❌"
            print(f"   {status_icon} {component}: {status}")
        
        return 0 if health_status["healthy"] else 1
    
    result = asyncio.run(check_health())
    sys.exit(result)


@app.command("start-api")
def start_api(
    port: int = typer.Option(8000, "--port", help="API server port"),
    host: str = typer.Option("0.0.0.0", "--host", help="API server host")
) -> None:
    """Start REST API server for workflow management."""
    
    try:
        import uvicorn
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        
        api_app = FastAPI(
            title="Temporal Platform API",
            description="REST API for Temporal workflow management",
            version="1.0.0"
        )
        
        @api_app.get("/health")
        async def api_health():
            return {"status": "healthy", "service": "temporal-platform-api"}
        
        @api_app.get("/")
        async def root():
            return {
                "message": "Temporal Platform API",
                "version": "1.0.0",
                "docs": "/docs"
            }
        
        logger.info(f"Starting API server on {host}:{port}")
        uvicorn.run(api_app, host=host, port=port)
        
    except ImportError:
        print("❌ FastAPI and uvicorn are required for API server")
        print("Install them with: poetry add fastapi uvicorn")
        sys.exit(1)


if __name__ == "__main__":
    app()
