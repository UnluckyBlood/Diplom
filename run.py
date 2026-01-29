#!/usr/bin/env python3
"""
Главный скрипт запуска системы мониторинга Arduino
"""

import subprocess
import sys
import os
import time
import signal
import threading

def start_web_server():
    """Запуск веб-сервера"""
    print("🌐 Запуск веб-сервера...")
    try:
        import WebServer.webserver
        # Запускаем в отдельном потоке
        import uvicorn
        config = uvicorn.Config(
            "WebServer.webserver:app",
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        print(f"❌ Ошибка веб-сервера: {e}")

def start_data_processor():
    """Запуск обработчика данных"""
    print("📡 Запуск обработчика данных...")
    try:
        import DataProcessor.main
        DataProcessor.main.main()
    except Exception as e:
        print(f"❌ Ошибка обработчика данных: {e}")

def main():
    """Главная функция"""
    print("=" * 50)
    print("🚀 ARDUINO MONITORING SYSTEM")
    print("=" * 50)
    
    # Проверяем установлены ли зависимости
    try:
        import fastapi
        import uvicorn
        import serial
        import aiohttp
        print("✅ Зависимости проверены")
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("Установите: pip install fastapi uvicorn pyserial aiohttp")
        return 1
    
    # Запускаем в отдельных потоках
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    data_thread = threading.Thread(target=start_data_processor, daemon=True)
    
    web_thread.start()
    time.sleep(2)  # Даем время веб-серверу запуститься
    
    data_thread.start()
    
    print("=" * 50)
    print("✅ СИСТЕМА УСПЕШНО ЗАПУЩЕНА")
    print("=" * 50)
    print("🌐 Веб-интерфейс: http://localhost:8000")
    print("⚡ WebSocket: ws://localhost:8000/ws")
    print("📡 API данные: http://localhost:8000/api/data")
    print("📊 API текущие: http://localhost:8000/api/current")
    print("=" * 50)
    print("\nДля остановки нажмите Ctrl+C\n")
    
    try:
        # Держим основную программу активной
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Завершение работы...")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
