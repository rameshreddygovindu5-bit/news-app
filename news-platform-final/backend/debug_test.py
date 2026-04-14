from fastapi.testclient import TestClient
from auth_server import app

# Create test client
client = TestClient(app)

# Test the root endpoint first
print("Testing root endpoint:")
response = client.get("/")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test the login endpoint
print("\nTesting login endpoint:")
response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test with wrong credentials
print("\nTesting login with wrong credentials:")
response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
