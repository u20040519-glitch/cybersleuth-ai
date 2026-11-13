import httpx
import asyncio

BASE = "http://127.0.0.1:8000"

async def test_rate_limit():
    async with httpx.AsyncClient() as client:
        print("=== Testing Rate Limiting on Login (5/min) ===")
        for i in range(7):
            r = await client.post(f"{BASE}/api/auth/login", json={
                "email": "test@nexus.ai",
                "password": "wrongpass"
            })
            msg = ""
            if r.status_code == 429:
                data = r.json()
                msg = f" - RATE LIMITED: {data.get('message', '')}"
            print(f"  Request {i+1}: Status {r.status_code}{msg}")

        print()
        print("=== Testing Rate Limiting on Register (3/min) ===")
        for i in range(5):
            r = await client.post(f"{BASE}/api/auth/register", json={
                "full_name": f"Test User {i}",
                "email": f"ratetest{i}@nexus.ai",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "accept_terms": True,
                "accept_privacy": True
            })
            msg = ""
            if r.status_code == 429:
                data = r.json()
                msg = f" - RATE LIMITED: {data.get('message', '')}"
            print(f"  Request {i+1}: Status {r.status_code}{msg}")

    print("=== Rate limiting tests completed ===")

asyncio.run(test_rate_limit())
