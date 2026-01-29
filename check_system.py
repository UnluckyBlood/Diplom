import sys
import os
import subprocess
import time

def check_file(file_path):
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        return f"✅ {file_path} ({size} bytes)"
    else:
        return f"❌ {file_path} (MISSING)"

def main():
    print("=" * 50)
    print("ARDUINO MONITORING SYSTEM - QUICK CHECK")
    print("=" * 50)
    
    # Проверка файлов
    files_to_check = [
        "WebServer/webserver.py",
        "DataProcessor/simple_main.py",
        "AI/simple_ai.py",
        "requirements.txt"
    ]
    
    for file in files_to_check:
        print(check_file(file))
    
    print("\n" + "=" * 50)
    print("QUICK START:")
    print("=" * 50)
    print("1. Ensure Arduino is connected to COM3")
    print("2. Run: run_system.bat")
    print("3. Open: http://localhost:8000")
    print("4. For testing without Arduino: python test_simulator.py")
    
    print("\n" + "=" * 50)
    print("COMMANDS:")
    print("=" * 50)
    print("Start system:          .\run_system.bat")
    print("Start web only:        python WebServer\webserver.py")
    print("Start processor only:  python DataProcessor\simple_main.py")
    print("Test simulator:        python test_simulator.py")

if __name__ == "__main__":
    main()
