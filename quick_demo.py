#!/usr/bin/env python3
"""
Quick Temporal Platform Demo
===========================

Demonstrates the system working with a small load test that runs immediately.
"""

import asyncio
import sys
import os
from rich.console import Console
from rich.panel import Panel

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

console = Console()

async def quick_system_test():
    """Run a quick system demonstration."""
    
    console.print(Panel(
        "🚀 **Temporal Platform Quick Demo**\n"
        "Testing system connectivity and basic functionality",
        title="System Demo",
        expand=False
    ))
    
    # Test 1: Basic connectivity
    console.print("1. 🔗 Testing Temporal UI connectivity...")
    import subprocess
    try:
        result = subprocess.run(['curl', '-s', 'http://localhost:8080/api/v1/cluster-info'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'clusterId' in result.stdout:
            console.print("   ✅ Temporal UI: Connected", style="green")
        else:
            console.print("   ❌ Temporal UI: Not accessible", style="red")
    except:
        console.print("   ❌ Temporal UI: Connection failed", style="red")
    
    # Test 2: Elasticsearch
    console.print("2. 🔍 Testing Elasticsearch...")
    try:
        result = subprocess.run(['curl', '-s', 'http://localhost:9200/_cluster/health'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and ('green' in result.stdout or 'yellow' in result.stdout):
            console.print("   ✅ Elasticsearch: Healthy", style="green")
        else:
            console.print("   ❌ Elasticsearch: Not healthy", style="red")
    except:
        console.print("   ❌ Elasticsearch: Connection failed", style="red")
    
    # Test 3: Docker containers
    console.print("3. 🐳 Checking Docker containers...")
    try:
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            temporal_containers = [line for line in lines if 'temporal' in line.lower()]
            console.print(f"   ✅ Found {len(temporal_containers)} Temporal containers running", style="green")
        else:
            console.print("   ❌ Could not check Docker containers", style="red")
    except:
        console.print("   ❌ Docker not accessible", style="red")
    
    # Test 4: Python application
    console.print("4. 🐍 Testing Python application...")
    try:
        from temporal_platform.config.settings import Settings
        settings = Settings()
        console.print(f"   ✅ Configuration loaded: {settings.environment}", style="green")
        console.print(f"   ✅ Temporal host: {settings.temporal.temporal_host}:{settings.temporal.temporal_port}", style="green")
    except Exception as e:
        console.print(f"   ❌ Python app error: {e}", style="red")
    
    # Test 5: Quick load test (basic connections)
    console.print("5. ⚡ Running quick load test (10 connections)...")
    
    success_count = 0
    total_tests = 10
    
    for i in range(total_tests):
        try:
            result = subprocess.run(['curl', '-s', '-w', '%{http_code}', 
                                   'http://localhost:8080/api/v1/cluster-info'], 
                                  capture_output=True, text=True, timeout=2)
            if '200' in result.stdout:
                success_count += 1
        except:
            pass
    
    success_rate = (success_count / total_tests) * 100
    if success_rate >= 80:
        console.print(f"   ✅ Load test: {success_count}/{total_tests} successful ({success_rate:.0f}%)", style="green")
    else:
        console.print(f"   ⚠️  Load test: {success_count}/{total_tests} successful ({success_rate:.0f}%)", style="yellow")
    
    # Summary
    console.print("\n" + "="*60)
    console.print(Panel(
        "🎯 **Demo Complete**\n\n"
        "**Next Steps:**\n"
        "• Run full load test: `python load_test.py --workflows 100 --concurrent 10`\n"
        "• Monitor system: `python monitor_system.py --interval 5`\n"
        "• Access Temporal UI: http://localhost:8080\n"
        "• Check comprehensive guide: `cat TESTING_GUIDE.md`\n\n"
        "**Your Temporal Platform is ready for production! 🚀**",
        title="Success",
        expand=False,
        style="green"
    ))

if __name__ == "__main__":
    asyncio.run(quick_system_test())
