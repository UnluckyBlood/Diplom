import sys
import subprocess
import os

def check_python():
    """Проверяем доступные версии Python"""
    print("🔍 Поиск Python...")
    
    # Проверяем разные команды
    commands = ['python', 'py', 'python3']
    
    for cmd in commands:
        try:
            result = subprocess.run([cmd, '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  shell=True)
            if result.returncode == 0:
                print(f"✅ Найден: {cmd} → {result.stdout.strip()}")
                return cmd
        except:
            continue
    
    print("❌ Python не найден!")
    print("\nУстановите Python с сайта: https://www.python.org/downloads/")
    print("ВАЖНО: При установке отметьте 'Add Python to PATH'")
    return None

def install_packages(python_cmd):
    """Устанавливаем необходимые пакеты"""
    print("\n📦 Установка библиотек...")
    
    packages = [
        'fastapi',
        'uvicorn[standard]', 
        'pyserial',
        'requests',
        'websockets'
    ]
    
    for package in packages:
        print(f"Установка {package}...")
        try:
            subprocess.run([python_cmd, '-m', 'pip', 'install', package], 
                         check=True,
                         shell=True)
            print(f"✅ {package} установлен")
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка установки {package}: {e}")

def main():
    print("=" * 50)
    print("   УСТАНОВКА ARDUINO MONITORING SYSTEM")
    print("=" * 50)
    
    python_cmd = check_python()
    
    if python_cmd:
        # Проверяем pip
        try:
            subprocess.run([python_cmd, '-m', 'pip', '--version'], 
                         capture_output=True, 
                         check=True,
                         shell=True)
            print("✅ PIP доступен")
        except:
            print("❌ PIP не доступен")
            print("Обновляем pip...")
            subprocess.run([python_cmd, '-m', 'ensurepip', '--upgrade'], 
                         shell=True)
        
        # Устанавливаем пакеты
        install_packages(python_cmd)
        
        print("\n" + "=" * 50)
        print("✅ УСТАНОВКА ЗАВЕРШЕНА!")
        print("=" * 50)
        print("\nЗапустите систему:")
        print(f"1. Веб-сервер: {python_cmd} WebServer\\webserver.py")
        print(f"2. Обработчик: {python_cmd} DataProcessor\\simple_main.py")
        print("3. Браузер: http://localhost:8000")
        
    input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()
