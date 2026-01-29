#!/usr/bin/env python3
"""
Установка зависимостей для работы с GPU (исправленная версия)
"""

import subprocess
import sys
import platform
import importlib.util

def check_python_version():
    """Проверка версии Python"""
    version = sys.version_info
    print(f"🐍 Python версия: {version.major}.{version.minor}.{version.micro}")
    return version

def install_pytorch_cuda():
    """Установка PyTorch с поддержкой CUDA для Windows"""
    print("\n📦 Установка PyTorch с поддержкой CUDA...")
    
    # Проверяем, есть ли уже torch
    torch_spec = importlib.util.find_spec("torch")
    if torch_spec:
        try:
            import torch
            print(f"✅ PyTorch уже установлен: {torch.__version__}")
            if hasattr(torch, 'version'):
                print(f"   CUDA доступна: {torch.cuda.is_available()}")
            return True
        except:
            pass
    
    # Для Windows с Python 3.14 и 5060 Ti (CUDA 12.x)
    pytorch_cmd = [
        sys.executable, "-m", "pip", "install",
        "torch", "torchvision", "torchaudio",
        "--index-url", "https://download.pytorch.org/whl/cu121"
    ]
    
    print(f"Выполняется: {' '.join(pytorch_cmd)}")
    
    try:
        subprocess.check_call(pytorch_cmd)
        print("✅ PyTorch с CUDA установлен")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки PyTorch: {e}")
        
        # Попробуем альтернативный вариант
        print("🔄 Попытка альтернативной установки...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "torch", "torchvision", "torchaudio",
                "--extra-index-url", "https://download.pytorch.org/whl/cu121"
            ])
            print("✅ PyTorch установлен (альтернативный метод)")
            return True
        except Exception as e2:
            print(f"❌ Вторая попытка также не удалась: {e2}")
            return False

def install_other_packages():
    """Установка остальных пакетов"""
    packages = [
        'scikit-learn',
        'pandas',
        'numpy',
        'joblib'
    ]
    
    for package in packages:
        print(f"📦 Установка {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} установлен")
        except Exception as e:
            print(f"⚠️ Ошибка установки {package}: {e}")

def check_cuda_driver():
    """Проверка драйверов CUDA"""
    print("\n🔍 Проверка драйверов CUDA...")
    
    # Проверка через nvidia-smi
    try:
        result = subprocess.run(
            ['nvidia-smi'],
            capture_output=True,
            text=True,
            shell=True
        )
        if result.returncode == 0:
            print("✅ NVIDIA драйверы обнаружены")
            # Парсим вывод для получения информации
            lines = result.stdout.split('\n')
            for line in lines[:10]:  # Первые 10 строк
                if "NVIDIA-SMI" in line:
                    print(f"   {line.strip()}")
                if "Driver Version" in line:
                    print(f"   {line.strip()}")
                if "CUDA Version" in line:
                    print(f"   {line.strip()}")
                if "5060 Ti" in line or "RTX 5060" in line:
                    print(f"   Видеокарта: {line.strip()}")
            return True
        else:
            print("❌ nvidia-smi не найден или не работает")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки драйверов: {e}")
        return False

def check_gpu_availability():
    """Проверка доступности GPU через PyTorch"""
    print("\n🔍 Проверка доступности GPU через PyTorch...")
    
    try:
        import torch
        
        if torch.cuda.is_available():
            print(f"✅ GPU доступен!")
            print(f"   Устройство: {torch.cuda.get_device_name(0)}")
            print(f"   CUDA версия: {torch.version.cuda}")
            
            # Показываем информацию о памяти
            print(f"   Всего памяти: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            print(f"   Доступно сейчас: {torch.cuda.memory_allocated() / 1024**3:.1f} GB")
            
            # Тест GPU
            print("\n🧪 Тестирование GPU...")
            x = torch.randn(1000, 1000).cuda()
            y = torch.randn(1000, 1000).cuda()
            z = torch.matmul(x, y)
            print(f"   Тест вычислений выполнен успешно!")
            print(f"   Результат на GPU: {z[0,0]:.4f}")
            
            return True
        else:
            print("❌ GPU не доступен для PyTorch")
            print("   Возможные причины:")
            print("   1. Неправильная версия PyTorch")
            print("   2. Отсутствуют драйверы CUDA")
            print("   3. Версия CUDA не совместима")
            return False
            
    except ImportError:
        print("❌ PyTorch не установлен")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке GPU: {e}")
        return False

def install_cuda_toolkit():
    """Предлагаем установить CUDA Toolkit если нужно"""
    print("\n💡 Рекомендации по установке CUDA:")
    print("=" * 60)
    print("Для вашей видеокарты RTX 5060 Ti требуется:")
    print("1. NVIDIA драйвер версии 535 или выше")
    print("2. CUDA Toolkit 11.8 или 12.x")
    print("\nСсылки для скачивания:")
    print("• Драйверы: https://www.nvidia.com/Download/index.aspx")
    print("• CUDA Toolkit: https://developer.nvidia.com/cuda-downloads")
    print("=" * 60)

def main():
    print("=" * 60)
    print("🤖 УСТАНОВКА AI С ПОДДЕРЖКОЙ GPU (ИСПРАВЛЕННАЯ)")
    print("=" * 60)
    
    # Проверка версии Python
    py_version = check_python_version()
    
    # Проверка драйверов
    cuda_drivers_ok = check_cuda_driver()
    
    if not cuda_drivers_ok:
        print("\n⚠️ ВНИМАНИЕ: Драйверы NVIDIA не обнаружены")
        install_cuda_toolkit()
        response = input("\nПродолжить установку без GPU? (y/n): ")
        if response.lower() != 'y':
            print("Установка прервана")
            return
    
    # Установка PyTorch
    pytorch_installed = install_pytorch_cuda()
    
    if pytorch_installed:
        # Проверка GPU
        gpu_available = check_gpu_availability()
        
        if not gpu_available:
            print("\n⚠️ ВНИМАНИЕ: PyTorch не видит GPU")
            print("Попробуйте следующие шаги:")
            print("1. Обновите драйверы NVIDIA")
            print("2. Установите CUDA Toolkit 12.1")
            print("3. Перезагрузите компьютер")
            print("4. Запустите этот скрипт снова")
    
    # Установка остальных пакетов
    install_other_packages()
    
    print("\n" + "=" * 60)
    print("✅ Установка завершена!")
    
    # Финальная проверка
    try:
        import torch
        if torch.cuda.is_available():
            print(f"🎉 GPU готов к использованию: {torch.cuda.get_device_name(0)}")
            print(f"   В simple_ai.py установите use_gpu=True")
        else:
            print("📊 GPU не доступен, будет использоваться CPU")
            print(f"   В simple_ai.py установите use_gpu=False")
    except:
        print("📊 PyTorch установлен, но есть проблемы с импортом")
    
    print("=" * 60)

if __name__ == "__main__":
    main()