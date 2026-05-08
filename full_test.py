import requests
import json
import time

time.sleep(1)
BASE_URL = "http://127.0.0.1:8000"

print("\n" + "="*60)
print("🧪 FASTAPI BACKEND COMPLETE TEST")
print("="*60 + "\n")

# Test 1: Health Check
try:
    r = requests.get(f"{BASE_URL}/health")
    print(f"✅ Test 1 - Health Check: {r.status_code}")
    print(f"   Response: {json.dumps(r.json(), indent=2)}\n")
except Exception as e:
    print(f"❌ Test 1 - Health Check Failed: {e}\n")

# Test 2: Login
token = None
try:
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": "admin@gmail.com", "password": "123456"})
    print(f"✅ Test 2 - Login: {r.status_code}")
    if r.status_code == 200:
        result = r.json()
        token = result["access_token"]
        print(f"   Access Token: {token[:40]}...")
        print(f"   Token Type: {result['token_type']}")
        print(f"   Role: {result['role']}\n")
    else:
        print(f"   ERROR: {r.text}\n")
except Exception as e:
    print(f"❌ Test 2 - Login Failed: {e}\n")

# Test 3: Get Employees (should be empty list)
try:
    r = requests.get(f"{BASE_URL}/employees")
    print(f"✅ Test 3 - Get Employees: {r.status_code}")
    print(f"   Response: {json.dumps(r.json(), indent=2)}")
    print(f"   Count: {len(r.json())} employees\n")
except Exception as e:
    print(f"❌ Test 3 - Get Employees Failed: {e}\n")

# Test 4: Create Employee (with token)
if token:
    try:
        headers = {"Authorization": f"Bearer {token}"}
        emp_data = {"name": "John Smith", "email": "john@company.com", "position": "Senior Developer"}
        r = requests.post(f"{BASE_URL}/employees", json=emp_data, headers=headers)
        print(f"✅ Test 4 - Create Employee (Super Admin): {r.status_code}")
        print(f"   Response: {json.dumps(r.json(), indent=2)}\n")
    except Exception as e:
        print(f"❌ Test 4 - Create Employee Failed: {e}\n")

# Test 5: Get Employees Again (should have 1)
try:
    r = requests.get(f"{BASE_URL}/employees")
    print(f"✅ Test 5 - Get Employees (after create): {r.status_code}")
    employees = r.json()
    print(f"   Total Employees: {len(employees)}")
    if employees:
        print(f"   First Employee:")
        print(f"     - Name: {employees[0].get('name')}")
        print(f"     - Email: {employees[0].get('email')}")
        print(f"     - Position: {employees[0].get('position')}\n")
except Exception as e:
    print(f"❌ Test 5 - Get Employees Failed: {e}\n")

# Test 6: Register New User
try:
    r = requests.post(f"{BASE_URL}/auth/register", json={"email": "user@example.com", "password": "pass123"})
    print(f"✅ Test 6 - Register User: {r.status_code}")
    print(f"   Email: {r.json().get('email')}")
    print(f"   Role: {r.json().get('role')}\n")
except Exception as e:
    print(f"❌ Test 6 - Register Failed: {e}\n")

# Test 7: Login as new user (should fail to create employee)
try:
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": "user@example.com", "password": "pass123"})
    if r.status_code == 200:
        user_token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {user_token}"}
        emp_data = {"name": "Jane Doe", "email": "jane@company.com", "position": "Developer"}
        r2 = requests.post(f"{BASE_URL}/employees", json=emp_data, headers=headers)
        print(f"✅ Test 7 - Create Employee as Regular User: {r2.status_code}")
        if r2.status_code != 200:
            print(f"   Expected 403 Forbidden: {r2.json()['detail']}\n")
        else:
            print(f"   WARNING: Should have been forbidden!\n")
except Exception as e:
    print(f"❌ Test 7 - Role-based access control test Failed: {e}\n")

print("="*60)
print("✅ TEST SUITE COMPLETED!")
print("="*60)
