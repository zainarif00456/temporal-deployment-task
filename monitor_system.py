#!/usr/bin/env python3
"""
Temporal Platform System Monitor
===============================

Real-time monitoring of Temporal Platform components during load testing.
Tracks performance metrics, resource utilization, and system health.

Usage:
    python monitor_system.py --interval 5 --duration 300
"""

import asyncio
import time
import sys
import os
import json
from typing import Dict, Any, List
from datetime import datetime
import argparse
import psutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from temporal_platform.config.settings import Settings

console = Console()

class SystemMonitor:
    """Real-time system monitoring for Temporal Platform."""
    
    def __init__(self, interval: int = 5):
        self.settings = Settings()
        self.interval = interval
        self.metrics_history: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        
    async def collect_docker_metrics(self) -> Dict[str, Any]:
        """Collect Docker container metrics."""
        try:
            import docker
            client = docker.from_env()
            
            metrics = {}
            containers = [
                'deployment-task-temporal-server-1',
                'deployment-task-postgres-1', 
                'deployment-task-elasticsearch-1',
                'temporal-ui-working'
            ]
            
            for container_name in containers:
                try:
                    container = client.containers.get(container_name)
                    stats = container.stats(stream=False)
                    
                    # Calculate CPU percentage
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                               stats['precpu_stats']['cpu_usage']['total_usage']
                    system_cpu_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                      stats['precpu_stats']['system_cpu_usage']
                    cpu_percent = (cpu_delta / system_cpu_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
                    
                    # Memory usage
                    memory_usage = stats['memory_stats']['usage']
                    memory_limit = stats['memory_stats']['limit']
                    memory_percent = (memory_usage / memory_limit) * 100.0
                    
                    metrics[container_name] = {
                        'status': container.status,
                        'cpu_percent': cpu_percent,
                        'memory_usage_mb': memory_usage / (1024 * 1024),
                        'memory_percent': memory_percent,
                        'network_rx_bytes': stats['networks']['deployment-task_temporal-network']['rx_bytes'] if 'networks' in stats else 0,
                        'network_tx_bytes': stats['networks']['deployment-task_temporal-network']['tx_bytes'] if 'networks' in stats else 0,
                    }
                except Exception as e:
                    metrics[container_name] = {'error': str(e)}
                    
            return metrics
        except Exception as e:
            return {'error': f"Docker not available: {e}"}
            
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect host system metrics."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=None),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
            'network_connections': len(psutil.net_connections()),
            'processes': len(psutil.pids()),
        }
        
    async def test_temporal_connectivity(self) -> Dict[str, Any]:
        """Test Temporal server connectivity and response times."""
        import aiohttp
        
        results = {}
        timeout = aiohttp.ClientTimeout(total=5)
        
        # Test Temporal UI
        try:
            start_time = time.time()
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get('http://localhost:8080/api/v1/cluster-info') as response:
                    response_time = time.time() - start_time
                    results['temporal_ui'] = {
                        'status_code': response.status,
                        'response_time_ms': response_time * 1000,
                        'healthy': response.status == 200
                    }
        except Exception as e:
            results['temporal_ui'] = {'error': str(e), 'healthy': False}
            
        # Test Elasticsearch
        try:
            start_time = time.time()
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get('http://localhost:9200/_cluster/health') as response:
                    response_time = time.time() - start_time
                    data = await response.json()
                    results['elasticsearch'] = {
                        'status_code': response.status,
                        'response_time_ms': response_time * 1000,
                        'cluster_status': data.get('status', 'unknown'),
                        'healthy': response.status == 200 and data.get('status') in ['green', 'yellow']
                    }
        except Exception as e:
            results['elasticsearch'] = {'error': str(e), 'healthy': False}
            
        return results
        
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system metrics."""
        timestamp = datetime.now()
        
        # Collect all metrics concurrently
        system_task = asyncio.create_task(self.collect_system_metrics())
        docker_task = asyncio.create_task(self.collect_docker_metrics()) 
        connectivity_task = asyncio.create_task(self.test_temporal_connectivity())
        
        system_metrics = await system_task
        docker_metrics = await docker_task
        connectivity_metrics = await connectivity_task
        
        return {
            'timestamp': timestamp.isoformat(),
            'uptime_seconds': (timestamp - self.start_time).total_seconds(),
            'system': system_metrics,
            'docker': docker_metrics,
            'connectivity': connectivity_metrics
        }
        
    def create_dashboard_layout(self, metrics: Dict[str, Any]) -> Layout:
        """Create a rich dashboard layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )
        
        # Header
        uptime_mins = metrics['uptime_seconds'] / 60
        layout["header"].update(Panel(
            f"🚀 Temporal Platform Monitor • Uptime: {uptime_mins:.1f}m • Interval: {self.interval}s",
            style="bold blue"
        ))
        
        # System metrics table
        system_table = Table(title="🖥️  System Resources")
        system_table.add_column("Metric", style="cyan")
        system_table.add_column("Value", style="green")
        system_table.add_column("Status", style="yellow")
        
        system = metrics['system']
        system_table.add_row("CPU Usage", f"{system['cpu_percent']:.1f}%", 
                            "🟢" if system['cpu_percent'] < 80 else "🟡" if system['cpu_percent'] < 95 else "🔴")
        system_table.add_row("Memory Usage", f"{system['memory_percent']:.1f}%",
                            "🟢" if system['memory_percent'] < 80 else "🟡" if system['memory_percent'] < 95 else "🔴")
        system_table.add_row("Disk Usage", f"{system['disk_usage_percent']:.1f}%",
                            "🟢" if system['disk_usage_percent'] < 80 else "🟡" if system['disk_usage_percent'] < 95 else "🔴")
        system_table.add_row("Load Average", f"{system['load_average'][0]:.2f}, {system['load_average'][1]:.2f}, {system['load_average'][2]:.2f}", "")
        system_table.add_row("Connections", f"{system['network_connections']}", "")
        system_table.add_row("Processes", f"{system['processes']}", "")
        
        layout["left"].update(system_table)
        
        # Docker containers table
        docker_table = Table(title="🐳 Docker Containers")
        docker_table.add_column("Container", style="cyan")
        docker_table.add_column("Status", style="green")
        docker_table.add_column("CPU %", style="yellow")
        docker_table.add_column("Memory MB", style="blue")
        
        if 'error' not in metrics['docker']:
            for container, data in metrics['docker'].items():
                if 'error' not in data:
                    docker_table.add_row(
                        container.replace('deployment-task-', '').replace('-1', ''),
                        data['status'],
                        f"{data['cpu_percent']:.1f}%",
                        f"{data['memory_usage_mb']:.0f}"
                    )
                else:
                    docker_table.add_row(container, "❌ Error", "-", "-")
        else:
            docker_table.add_row("Docker", "❌ Not Available", "-", "-")
            
        layout["right"].update(docker_table)
        
        # Connectivity status
        connectivity_info = ""
        if 'temporal_ui' in metrics['connectivity']:
            ui_status = "🟢" if metrics['connectivity']['temporal_ui'].get('healthy') else "🔴"
            ui_time = metrics['connectivity']['temporal_ui'].get('response_time_ms', 0)
            connectivity_info += f"Temporal UI: {ui_status} ({ui_time:.0f}ms) • "
            
        if 'elasticsearch' in metrics['connectivity']:
            es_status = "🟢" if metrics['connectivity']['elasticsearch'].get('healthy') else "🔴"
            es_time = metrics['connectivity']['elasticsearch'].get('response_time_ms', 0)
            connectivity_info += f"Elasticsearch: {es_status} ({es_time:.0f}ms)"
            
        layout["footer"].update(Panel(connectivity_info, title="🌐 Connectivity"))
        
        return layout
        
    async def monitor_continuously(self, duration: int = None):
        """Run continuous monitoring with live dashboard."""
        console.print("🚀 Starting system monitoring...")
        
        end_time = time.time() + duration if duration else None
        
        with Live(console=console, refresh_per_second=0.5) as live:
            while True:
                if end_time and time.time() > end_time:
                    break
                    
                try:
                    # Collect metrics
                    metrics = await self.collect_all_metrics()
                    self.metrics_history.append(metrics)
                    
                    # Update dashboard
                    layout = self.create_dashboard_layout(metrics)
                    live.update(layout)
                    
                    # Wait for next interval
                    await asyncio.sleep(self.interval)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    console.print(f"❌ Monitoring error: {e}", style="red")
                    await asyncio.sleep(self.interval)
                    
    def save_metrics_history(self, filename: str = None):
        """Save collected metrics to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_metrics_{timestamp}.json"
            
        with open(filename, 'w') as f:
            json.dump(self.metrics_history, f, indent=2, default=str)
            
        console.print(f"📁 Metrics saved to: {filename}", style="green")

async def main():
    """Main entry point for system monitoring."""
    parser = argparse.ArgumentParser(description="Temporal Platform System Monitor")
    parser.add_argument("--interval", type=int, default=5, help="Monitoring interval in seconds")
    parser.add_argument("--duration", type=int, help="Monitoring duration in seconds (unlimited if not specified)")
    parser.add_argument("--save-metrics", action="store_true", help="Save metrics history to file")
    
    args = parser.parse_args()
    
    monitor = SystemMonitor(interval=args.interval)
    
    try:
        await monitor.monitor_continuously(duration=args.duration)
        
        if args.save_metrics:
            monitor.save_metrics_history()
            
    except KeyboardInterrupt:
        console.print("\n⚠️  Monitoring stopped by user", style="yellow")
        if args.save_metrics:
            monitor.save_metrics_history()

if __name__ == "__main__":
    asyncio.run(main())
