import time
import random
import requests
from datetime import datetime

def simulate_arduino():
    """Simulate Arduino data for testing"""
    print("🧪 Arduino Simulator Started")
    print("📡 Sending data to: http://localhost:8000/api/data")
    print("Press Ctrl+C to stop\n")
    
    temperature = 22.0
    humidity = 55.0
    hit_count = 0
    
    try:
        while True:
            # Randomly change values
            temperature += random.uniform(-0.5, 0.5)
            humidity += random.uniform(-1, 1)
            
            # Keep within reasonable limits
            temperature = max(15, min(35, temperature))
            humidity = max(30, min(80, humidity))
            
            # Occasionally simulate a hit
            hit_detected = random.random() < 0.1  # 10% chance
            if hit_detected:
                hit_count += 1
            
            # Create data packet
            data = {
                "type": "realtime",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "temperature": round(temperature, 1),
                    "humidity": round(humidity, 1),
                    "hit_detected": 1 if hit_detected else 0,
                    "hit_interval": random.randint(100, 500) if hit_detected else 0,
                    "hit_count": hit_count
                }
            }
            
            try:
                # Send to web server
                response = requests.post(
                    "http://localhost:8000/api/data",
                    json=data,
                    timeout=2
                )
                
                if response.status_code == 200:
                    print(f"📤 Sent: {data['data']['temperature']}°C, {data['data']['humidity']}%", 
                          end="")
                    if hit_detected:
                        print(f" [HIT #{hit_count}]")
                    else:
                        print("")
                else:
                    print(f"⚠️ Server error: {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                print("❌ Web server not running. Start it first!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
            
            time.sleep(2)  # 2 second interval
            
    except KeyboardInterrupt:
        print("\n\n✅ Simulator stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")

def test_web_server():
    """Test if web server is responding"""
    print("🔍 Testing web server connection...")
    try:
        response = requests.get("http://localhost:8000/api/status", timeout=2)
        if response.status_code == 200:
            print("✅ Web server is running")
            return True
        else:
            print(f"⚠️ Web server returned: {response.status_code}")
            return False
    except:
        print("❌ Web server is not running")
        return False

if __name__ == "__main__":
    if test_web_server():
        simulate_arduino()
    else:
        print("\n💡 Start the web server first:")
        print("   python WebServer\\webserver.py")
        print("\nOr run the full system:")
        print("   .\\run_system.bat")
