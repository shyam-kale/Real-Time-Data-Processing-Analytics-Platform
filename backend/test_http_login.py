"""Test login via actual HTTP endpoint"""
import requests
import json

BASE_URL = "http://localhost:8000"  # Change if deployed elsewhere

def test_http_login():
    print("🔍 Testing HTTP login endpoint...")
    print()
    
    # Test credentials
    credentials = {
        "email": "shyam@dataflow.io",
        "password": "dataflow123"
    }
    
    try:
        print(f"POST {BASE_URL}/api/v1/auth/login")
        print(f"Body: {json.dumps(credentials)}")
        print()
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=credentials,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"   Access token: {data.get('access_token', 'N/A')[:50]}...")
            print(f"   Refresh token: {data.get('refresh_token', 'N/A')[:50]}...")
            print()
            
            # Test /me endpoint
            print("Testing /api/v1/auth/me...")
            me_response = requests.get(
                f"{BASE_URL}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {data['access_token']}"}
            )
            print(f"Status: {me_response.status_code}")
            if me_response.status_code == 200:
                print(f"User: {me_response.json()}")
                print("✅ Token works!")
            else:
                print(f"❌ Token validation failed: {me_response.text}")
            
            return True
        else:
            print(f"❌ Login failed!")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server!")
        print(f"   Is the backend running at {BASE_URL}?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    result = test_http_login()
    sys.exit(0 if result else 1)
