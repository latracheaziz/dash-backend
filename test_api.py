import requests
import time
import json

time.sleep(2)

print("Testing FastAPI Backend")
print("=" * 50)

# Test 1: Health check
try:
    r = requests.get('http://127.0.0.1:8000/health')
    print(f"✓ Health Check: {r.status_code}")
    print(f"  Response: {r.json()}")
except Exception as e:
    print(f"✗ Health Check Failed: {e}")

print()

# Test 2: Login
try:
    data = {'email': 'admin@gmail.com', 'password': '123456'}
    r = requests.post('http://127.0.0.1:8000/auth/login', json=data)
    print(f"✓ Login: {r.status_code}")
    if r.status_code == 200:
        result = r.json()
        print(f"  Token: {result['access_token'][:50]}...")
        print(f"  Role: {result.get('role', 'N/A')}")
        token = result['access_token']
        
        # Test 3: Get Employees (public)
        print()
        r = requests.get('http://127.0.0.1:8000/employees')
        print(f"✓ Get Employees (public): {r.status_code}")
        print(f"  Response: {r.json()}")
        
        # Test 4: Create Employee (requires token)
        print()
        headers = {'Authorization': f'Bearer {token}'}
        emp_data = {'name': 'John Doe', 'email': 'john@example.com', 'position': 'Developer'}
        r = requests.post('http://127.0.0.1:8000/employees', json=emp_data, headers=headers)
        print(f"✓ Create Employee (with token): {r.status_code}")
        print(f"  Response: {json.dumps(r.json(), indent=2)}")
    else:
        print(f"  Error: {r.text}")
except Exception as e:
    print(f"✗ Login Failed: {e}")
