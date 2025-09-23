#!/usr/bin/env python3
"""
Temporal Platform Load Testing Script
=====================================

This script tests the system with 1000+ concurrent workflow executions to demonstrate:
- Scalability and performance under load
- Fault tolerance and error handling
- Retry mechanisms and recovery
- Resource utilization and monitoring

Usage:
    python load_test.py --workflows 1000 --concurrent 50 --batch-size 10
"""

import asyncio
import time
import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
import statistics
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.live import Live
from rich import print as rprint

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporal_platform.config.settings import Settings
from temporal_platform.models.workflows import (
    DataItem, DataBatch, WorkflowInput, ProcessingMode, Priority
)
from temporal_platform.workflows.orchestration import DataProcessingOrchestrator

console = Console()

@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    total_workflows: int = 1000
    concurrent_limit: int = 50
    batch_size_per_workflow: int = 10
    items_per_batch: int = 20
    test_duration_minutes: int = 30
    ramp_up_time_seconds: int = 60
    enable_monitoring: bool = True
    failure_rate_threshold: float = 0.05  # 5% failure rate threshold

@dataclass
class WorkflowResult:
    """Result of a single workflow execution."""
    workflow_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    items_processed: int = 0

class LoadTestMetrics:
    """Collects and tracks load testing metrics."""
    
    def __init__(self):
        self.results: List[WorkflowResult] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        
    def add_result(self, result: WorkflowResult):
        """Add a workflow result."""
        self.results.append(result)
        
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive test summary."""
        completed = [r for r in self.results if r.status == "completed"]
        failed = [r for r in self.results if r.status == "failed"]
        
        execution_times = [r.execution_time_seconds for r in completed if r.execution_time_seconds]
        
        return {
            "total_workflows": len(self.results),
            "completed": len(completed),
            "failed": len(failed),
            "success_rate": len(completed) / len(self.results) if self.results else 0,
            "failure_rate": len(failed) / len(self.results) if self.results else 0,
            "avg_execution_time": statistics.mean(execution_times) if execution_times else 0,
            "median_execution_time": statistics.median(execution_times) if execution_times else 0,
            "min_execution_time": min(execution_times) if execution_times else 0,
            "max_execution_time": max(execution_times) if execution_times else 0,
            "p95_execution_time": statistics.quantiles(execution_times, n=20)[18] if len(execution_times) > 20 else 0,
            "p99_execution_time": statistics.quantiles(execution_times, n=100)[98] if len(execution_times) > 100 else 0,
            "total_items_processed": sum(r.items_processed for r in completed),
            "throughput_workflows_per_second": len(completed) / (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
        }

class TemporalLoadTester:
    """Main load testing orchestrator."""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.settings = Settings()
        self.metrics = LoadTestMetrics()
        self.client: Optional[Client] = None
        
    async def initialize(self):
        """Initialize Temporal client."""
        try:
            self.client = await Client.connect(
                f"{self.settings.temporal.temporal_host}:{self.settings.temporal.temporal_port}",
                namespace=self.settings.temporal.temporal_namespace,
            )
            console.print("✅ Connected to Temporal server", style="green")
        except Exception as e:
            console.print(f"❌ Failed to connect to Temporal: {e}", style="red")
            raise
            
    def create_test_data(self, workflow_id: str) -> WorkflowInput:
        """Create test data for a workflow."""
        batches = []
        
        for batch_idx in range(self.config.batch_size_per_workflow):
            items = []
            for item_idx in range(self.config.items_per_batch):
                item = DataItem(
                    content=f"Load test data - WF:{workflow_id} - Batch:{batch_idx} - Item:{item_idx}",
                    content_type="text/plain",
                    size_bytes=len(f"Load test data - WF:{workflow_id} - Batch:{batch_idx} - Item:{item_idx}"),
                    metadata={
                        "workflow_id": workflow_id,
                        "batch_index": batch_idx,
                        "item_index": item_idx,
                        "test_timestamp": datetime.now().isoformat(),
                        "load_test": True
                    }
                )
                items.append(item)
                
            batch = DataBatch(
                items=items,
                batch_size=len(items),
                total_size_bytes=sum(item.size_bytes for item in items),
                processing_mode=ProcessingMode.PARALLEL,
                priority=Priority.MEDIUM
            )
            batches.append(batch)
            
        return WorkflowInput(
            dataset_id=f"load-test-dataset-{workflow_id}",
            batches=batches,
            parallel_batches=min(2, len(batches))  # Process max 2 batches in parallel
        )
        
    async def execute_single_workflow(self, workflow_index: int) -> WorkflowResult:
        """Execute a single workflow and track its performance."""
        workflow_id = f"load-test-{workflow_index:06d}"
        result = WorkflowResult(
            workflow_id=workflow_id,
            start_time=datetime.now()
        )
        
        try:
            # Create test data
            workflow_input = self.create_test_data(workflow_id)
            result.items_processed = sum(len(batch.items) for batch in workflow_input.batches)
            
            # Execute workflow
            result.status = "running"
            
            workflow_handle = await self.client.start_workflow(
                DataProcessingOrchestrator.run,
                workflow_input,
                id=workflow_id,
                task_queue=self.settings.temporal.temporal_task_queue,
                execution_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=30),
                    maximum_attempts=3,
                )
            )
            
            # Wait for completion
            workflow_result = await workflow_handle.result()
            
            result.end_time = datetime.now()
            result.execution_time_seconds = (result.end_time - result.start_time).total_seconds()
            result.status = "completed"
            
        except Exception as e:
            result.end_time = datetime.now()
            result.execution_time_seconds = (result.end_time - result.start_time).total_seconds()
            result.status = "failed"
            result.error_message = str(e)
            
        return result
        
    async def execute_batch_workflows(self, workflow_indices: List[int]) -> List[WorkflowResult]:
        """Execute a batch of workflows concurrently."""
        tasks = []
        
        for index in workflow_indices:
            task = asyncio.create_task(self.execute_single_workflow(index))
            tasks.append(task)
            
        return await asyncio.gather(*tasks, return_exceptions=True)
        
    async def run_load_test(self):
        """Run the complete load test."""
        console.print(Panel(
            f"🚀 Starting Load Test\n"
            f"📊 Total Workflows: {self.config.total_workflows:,}\n"
            f"⚡ Concurrent Limit: {self.config.concurrent_limit}\n"
            f"📦 Batches per Workflow: {self.config.batch_size_per_workflow}\n"
            f"📝 Items per Batch: {self.config.items_per_batch}\n"
            f"📈 Total Items: {self.config.total_workflows * self.config.batch_size_per_workflow * self.config.items_per_batch:,}",
            title="Load Test Configuration",
            expand=False
        ))
        
        # Initialize metrics
        self.metrics.start_time = datetime.now()
        
        # Create workflow batches
        workflow_batches = []
        for i in range(0, self.config.total_workflows, self.config.concurrent_limit):
            batch = list(range(i, min(i + self.config.concurrent_limit, self.config.total_workflows)))
            workflow_batches.append(batch)
            
        # Execute workflows with progress tracking
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            overall_task = progress.add_task("Overall Progress", total=self.config.total_workflows)
            batch_task = progress.add_task("Current Batch", total=len(workflow_batches))
            
            for batch_idx, workflow_indices in enumerate(workflow_batches):
                progress.update(batch_task, description=f"Batch {batch_idx + 1}/{len(workflow_batches)}")
                
                # Execute batch
                batch_results = await self.execute_batch_workflows(workflow_indices)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        # Handle exceptions from gather
                        error_result = WorkflowResult(
                            workflow_id=f"error-{len(self.metrics.results)}",
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            status="failed",
                            error_message=str(result)
                        )
                        self.metrics.add_result(error_result)
                    else:
                        self.metrics.add_result(result)
                        
                progress.update(overall_task, advance=len(workflow_indices))
                progress.update(batch_task, advance=1)
                
                # Add small delay between batches to prevent overwhelming
                await asyncio.sleep(0.1)
                
        self.metrics.end_time = datetime.now()
        
    def display_results(self):
        """Display comprehensive test results."""
        summary = self.metrics.get_summary()
        
        # Main results table
        table = Table(title="🎯 Load Test Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Details", style="dim")
        
        table.add_row("Total Workflows", f"{summary['total_workflows']:,}", "")
        table.add_row("✅ Completed", f"{summary['completed']:,}", f"{summary['success_rate']:.1%} success rate")
        table.add_row("❌ Failed", f"{summary['failed']:,}", f"{summary['failure_rate']:.1%} failure rate")
        table.add_row("📊 Total Items Processed", f"{summary['total_items_processed']:,}", "")
        table.add_row("⚡ Throughput", f"{summary['throughput_workflows_per_second']:.2f} wf/sec", "")
        
        table.add_section()
        table.add_row("⏱️  Avg Execution Time", f"{summary['avg_execution_time']:.2f}s", "")
        table.add_row("📈 Median Execution Time", f"{summary['median_execution_time']:.2f}s", "")
        table.add_row("⚡ Min Execution Time", f"{summary['min_execution_time']:.2f}s", "")
        table.add_row("🐌 Max Execution Time", f"{summary['max_execution_time']:.2f}s", "")
        table.add_row("📊 95th Percentile", f"{summary['p95_execution_time']:.2f}s", "")
        table.add_row("📊 99th Percentile", f"{summary['p99_execution_time']:.2f}s", "")
        
        console.print(table)
        
        # Performance assessment
        total_duration = (self.metrics.end_time - self.metrics.start_time).total_seconds()
        
        console.print(Panel(
            f"🕒 **Total Test Duration:** {total_duration:.1f} seconds\n"
            f"📈 **Overall Throughput:** {summary['total_items_processed'] / total_duration:.0f} items/second\n"
            f"🎯 **System Performance:** {'🟢 EXCELLENT' if summary['success_rate'] > 0.95 else '🟡 GOOD' if summary['success_rate'] > 0.90 else '🔴 NEEDS IMPROVEMENT'}\n"
            f"🔧 **Fault Tolerance:** {'🟢 ROBUST' if summary['failure_rate'] < self.config.failure_rate_threshold else '🟡 ACCEPTABLE' if summary['failure_rate'] < 0.10 else '🔴 FRAGILE'}",
            title="📊 Performance Assessment",
            expand=False
        ))
        
        # Error analysis
        if summary['failed'] > 0:
            error_table = Table(title="❌ Error Analysis")
            error_table.add_column("Error Type", style="red")
            error_table.add_column("Count", style="yellow")
            error_table.add_column("Percentage", style="dim")
            
            error_counts = {}
            for result in self.metrics.results:
                if result.status == "failed" and result.error_message:
                    error_type = result.error_message.split(':')[0] if ':' in result.error_message else result.error_message
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
                    
            for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / summary['failed']) * 100
                error_table.add_row(error_type, str(count), f"{percentage:.1f}%")
                
            console.print(error_table)
            
    def save_results(self, filename: str = None):
        """Save detailed results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"load_test_results_{timestamp}.json"
            
        results_data = {
            "config": {
                "total_workflows": self.config.total_workflows,
                "concurrent_limit": self.config.concurrent_limit,
                "batch_size_per_workflow": self.config.batch_size_per_workflow,
                "items_per_batch": self.config.items_per_batch,
            },
            "summary": self.metrics.get_summary(),
            "detailed_results": [
                {
                    "workflow_id": r.workflow_id,
                    "start_time": r.start_time.isoformat(),
                    "end_time": r.end_time.isoformat() if r.end_time else None,
                    "status": r.status,
                    "execution_time_seconds": r.execution_time_seconds,
                    "items_processed": r.items_processed,
                    "error_message": r.error_message
                }
                for r in self.metrics.results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
            
        console.print(f"📁 Results saved to: {filename}", style="green")

async def main():
    """Main entry point for the load test."""
    parser = argparse.ArgumentParser(description="Temporal Platform Load Testing")
    parser.add_argument("--workflows", type=int, default=1000, help="Total number of workflows to execute")
    parser.add_argument("--concurrent", type=int, default=50, help="Maximum concurrent workflows")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of batches per workflow")
    parser.add_argument("--items-per-batch", type=int, default=10, help="Number of items per batch")
    parser.add_argument("--save-results", action="store_true", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    # Create configuration
    config = LoadTestConfig(
        total_workflows=args.workflows,
        concurrent_limit=args.concurrent,
        batch_size_per_workflow=args.batch_size,
        items_per_batch=args.items_per_batch
    )
    
    # Initialize and run load test
    tester = TemporalLoadTester(config)
    
    try:
        await tester.initialize()
        await tester.run_load_test()
        
        tester.display_results()
        
        if args.save_results:
            tester.save_results()
            
    except KeyboardInterrupt:
        console.print("\n⚠️  Load test interrupted by user", style="yellow")
    except Exception as e:
        console.print(f"❌ Load test failed: {e}", style="red")
        raise

if __name__ == "__main__":
    asyncio.run(main())
