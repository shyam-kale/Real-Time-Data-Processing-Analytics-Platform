"""Test login functionality directly"""
import asyncio
import sys
from sqlalchemy import select
from app.db.base import Session
from app.models.user import User
from app.core.security import verify_password, hash_password
from app.services.auth_service import login_user
from app.schemas.auth import LoginRequest


async def test_login():
    print("🔍 Testing login flow...")
    print()
    
    async with Session() as db:
        # 1. Check if user exists
        result = await db.execute(select(User).where(User.email == "shyam@dataflow.io"))
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ User not found in database!")
            print("   Run: POST /api/v1/init to seed data")
            return False
            
        print(f"✅ User found:")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Name: {user.full_name}")
        print(f"   Active: {user.is_active}")
        print(f"   Hash: {user.hashed_password[:60]}...")
        print()
        
        # 2. Test password verification
        password = "dataflow123"
        is_valid = verify_password(password, user.hashed_password)
        
        if not is_valid:
            print(f"❌ Password verification failed!")
            print(f"   Testing password: '{password}'")
            print()
            
            # Try to verify what the hash was created with
            test_hash = hash_password(password)
            print(f"   Fresh hash: {test_hash[:60]}...")
            print(f"   DB hash:    {user.hashed_password[:60]}...")
            
            # Test if fresh hash verifies
            fresh_verify = verify_password(password, test_hash)
            print(f"   Fresh hash verifies: {fresh_verify}")
            return False
        else:
            print(f"✅ Password verification successful!")
            print()
        
        # 3. Test login service
        try:
            login_req = LoginRequest(email="shyam@dataflow.io", password="dataflow123")
            token_response = await login_user(db, login_req)
            print(f"✅ Login service successful!")
            print(f"   Access token: {token_response.access_token[:50]}...")
            print(f"   Refresh token: {token_response.refresh_token[:50]}...")
            print()
            return True
        except Exception as e:
            print(f"❌ Login service failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    result = asyncio.run(test_login())
    sys.exit(0 if result else 1)
