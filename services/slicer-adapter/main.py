import os
import time

api_url = os.environ.get("SLICER_API_URL", "http://slicer_api:3000")

print("==================================================")
print("🤖 SLICER ADAPTER (Dummy V1) STARTED!")
print(f"🔗 Target Slicer API URL: {api_url}")
print("==================================================")
print("[*] Waiting for RabbitMQ & MinIO connections... (mock)")

while True:
    print("[*] Adapter heartbeat - waiting for slice jobs...")
    time.sleep(10)
