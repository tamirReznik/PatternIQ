#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Simple test to verify Python execution
print("Hello from PatternIQ batch test!")
print(f"Current directory: {os.getcwd()}")
print(f"Python version: {sys.version}")
print(f"Date: 2025-10-04")

# Check if src directory exists
src_path = Path("src")
if src_path.exists():
    print(f"✅ Found src directory at: {src_path.absolute()}")
else:
    print("❌ src directory not found")

# Check reports directory
reports_path = Path("reports")
if reports_path.exists():
    reports = list(reports_path.glob("*"))
    print(f"📊 Reports directory contains {len(reports)} files")
    for report in reports:
        print(f"   - {report.name}")
else:
    print("📊 Reports directory not found")
