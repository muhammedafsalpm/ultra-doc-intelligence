#!/usr/bin/env python3
import subprocess
import sys
import os
import webbrowser
import time

def main():
    print("🚀 Starting Ultra Doc-Intelligence...")
    print("=" * 50)
    
    # Check if backend dependencies are installed
    print("📦 Checking dependencies...")
    try:
        import sentence_transformers
        import fastapi
        import uvicorn
    except ImportError:
        print("⚠️  Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"])
    
    # Start backend
    print("🔄 Starting backend server...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for backend to start
    time.sleep(3)
    
    # Open browser
    print("🌐 Opening browser...")
    webbrowser.open("http://localhost:8000")
    webbrowser.open("http://localhost:8000/docs")  # API docs
    
    print("\n✅ System is running!")
    print("📍 Frontend: http://localhost:8000")
    print("📍 API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        backend_process.terminate()
        backend_process.wait()
        print("✅ Shutdown complete")

if __name__ == "__main__":
    main()
