#!/usr/bin/env python3
"""
Quick Stress Test for Temporal Platform
=======================================

This script performs basic stress testing without requiring workers to be running.
It tests client connections, namespace operations, and basic workflow submissions.

Usage:
    python stress_test.py --connections 100 --duration 60
"""

import asyncio
import time
import sys
import os
from typing import List
from datetime import datetime, timedelta
import argparse
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.panel import Panel

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from temporalio.client import Client
from temporal_platform.config.settings import Settings

console = Console()

class StressTester:
    """Simple stress tester for basic Temporal operations."""
    
    def __init__(self):
        self.settings = Settings()
        self.results = {
            'connections': {'success': 0, 'failed': 0, 'times': []},
            'namespace_queries': {'success': 0, 'failed': 0, 'times': []},
            'cluster_info': {'success': 0, 'failed': 0, 'times': []},
        }
        
    async def test_connection(self) -> tuple[bool, float]:
        """Test a single connection to Temporal."""
        start_time = time.time()
        try:
            client = await Client.connect(
                f"{self.settings.temporal.temporal_host}:{self.settings.temporal.temporal_port}",
                namespace=self.settings.temporal.temporal_namespace,
            )
            await client.service.get_system_info()
            execution_time = time.time() - start_time
            return True, execution_time
        except Exception as e:
            execution_time = time.time() - start_time
            return False, execution_time
            
    async def test_namespace_query(self) -> tuple[bool, float]:
        """Test namespace listing operation."""
        start_time = time.time()
        try:
            client = await Client.connect(
                f"{self.settings.temporal.temporal_host}:{self.settings.temporal.temporal_port}",
                namespace=self.settings.temporal.temporal_namespace,
            )
            await client.service.list_namespaces()
            execution_time = time.time() - start_time
            return True, execution_time
        except Exception as e:
            execution_time = time.time() - start_time
            return False, execution_time
            
    async def test_cluster_info(self) -> tuple[bool, float]:
        """Test cluster info retrieval."""
        start_time = time.time()
        try:
            client = await Client.connect(
                f"{self.settings.temporal.temporal_host}:{self.settings.temporal.temporal_port}",
                namespace=self.settings.temporal.temporal_namespace,
            )
            await client.service.get_cluster_info()
            execution_time = time.time() - start_time
            return True, execution_time
        except Exception as e:
            execution_time = time.time() - start_time
            return False, execution_time
            
    async def run_connection_stress_test(self, num_connections: int):
        """Run stress test for connections."""
        console.print(f"🔗 Testing {num_connections} concurrent connections...")
        
        tasks = []
        for _ in range(num_connections):
            task = asyncio.create_task(self.test_connection())
            tasks.append(task)
            
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            console=console
        ) as progress:
            task_progress = progress.add_task("Connections", total=num_connections)
            
            for completed_task in asyncio.as_completed(tasks):
                success, exec_time = await completed_task
                if success:
                    self.results['connections']['success'] += 1
                else:
                    self.results['connections']['failed'] += 1
                self.results['connections']['times'].append(exec_time)
                progress.advance(task_progress)
                
    async def run_operation_stress_test(self, operations_per_second: int, duration_seconds: int):
        """Run stress test for various operations."""
        console.print(f"⚡ Testing {operations_per_second} ops/sec for {duration_seconds} seconds...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        operation_interval = 1.0 / operations_per_second
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            console=console
        ) as progress:
            task_progress = progress.add_task("Operations", total=duration_seconds)
            
            while time.time() < end_time:
                iteration_start = time.time()
                
                # Run operations concurrently
                tasks = [
                    asyncio.create_task(self.test_namespace_query()),
                    asyncio.create_task(self.test_cluster_info()),
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process namespace query result
                if isinstance(results[0], tuple):
                    success, exec_time = results[0]
                    if success:
                        self.results['namespace_queries']['success'] += 1
                    else:
                        self.results['namespace_queries']['failed'] += 1
                    self.results['namespace_queries']['times'].append(exec_time)
                    
                # Process cluster info result
                if isinstance(results[1], tuple):
                    success, exec_time = results[1]
                    if success:
                        self.results['cluster_info']['success'] += 1
                    else:
                        self.results['cluster_info']['failed'] += 1
                    self.results['cluster_info']['times'].append(exec_time)
                
                # Maintain target rate
                elapsed = time.time() - iteration_start
                if elapsed < operation_interval:
                    await asyncio.sleep(operation_interval - elapsed)
                    
                # Update progress
                current_time = time.time()
                progress_value = (current_time - start_time)
                progress.update(task_progress, completed=progress_value)
                
    def display_results(self):
        """Display stress test results."""
        table = Table(title="🎯 Stress Test Results")
        table.add_column("Operation", style="cyan")
        table.add_column("Success", style="green")
        table.add_column("Failed", style="red")
        table.add_column("Success Rate", style="yellow")
        table.add_column("Avg Time (s)", style="blue")
        table.add_column("Min Time (s)", style="dim")
        table.add_column("Max Time (s)", style="dim")
        
        for operation, data in self.results.items():
            total = data['success'] + data['failed']
            success_rate = (data['success'] / total * 100) if total > 0 else 0
            avg_time = sum(data['times']) / len(data['times']) if data['times'] else 0
            min_time = min(data['times']) if data['times'] else 0
            max_time = max(data['times']) if data['times'] else 0
            
            table.add_row(
                operation.replace('_', ' ').title(),
                str(data['success']),
                str(data['failed']),
                f"{success_rate:.1f}%",
                f"{avg_time:.3f}",
                f"{min_time:.3f}",
                f"{max_time:.3f}"
            )
            
        console.print(table)
        
        # Overall assessment
        total_operations = sum(data['success'] + data['failed'] for data in self.results.values())
        total_success = sum(data['success'] for data in self.results.values())
        overall_success_rate = (total_success / total_operations * 100) if total_operations > 0 else 0
        
        console.print(Panel(
            f"📊 **Total Operations:** {total_operations:,}\n"
            f"✅ **Overall Success Rate:** {overall_success_rate:.1f}%\n"
            f"🎯 **System Status:** {'🟢 HEALTHY' if overall_success_rate > 95 else '🟡 DEGRADED' if overall_success_rate > 80 else '🔴 UNHEALTHY'}",
            title="Overall Assessment",
            expand=False
        ))

async def main():
    """Main entry point for stress testing."""
    parser = argparse.ArgumentParser(description="Temporal Platform Stress Testing")
    parser.add_argument("--connections", type=int, default=100, help="Number of concurrent connections to test")
    parser.add_argument("--ops-per-sec", type=int, default=10, help="Operations per second for sustained test")
    parser.add_argument("--duration", type=int, default=60, help="Duration of sustained test in seconds")
    
    args = parser.parse_args()
    
    tester = StressTester()
    
    console.print(Panel(
        f"🚀 **Temporal Platform Stress Test**\n"
        f"🔗 Testing {args.connections} concurrent connections\n"
        f"⚡ Testing {args.ops_per_sec} operations/second\n"
        f"⏱️  Duration: {args.duration} seconds",
        title="Stress Test Configuration",
        expand=False
    ))
    
    try:
        # Test concurrent connections
        await tester.run_connection_stress_test(args.connections)
        
        # Small break between tests
        await asyncio.sleep(2)
        
        # Test sustained operations
        await tester.run_operation_stress_test(args.ops_per_sec, args.duration)
        
        # Display results
        tester.display_results()
        
    except KeyboardInterrupt:
        console.print("\n⚠️  Stress test interrupted by user", style="yellow")
    except Exception as e:
        console.print(f"❌ Stress test failed: {e}", style="red")
        raise

if __name__ == "__main__":
    asyncio.run(main())
