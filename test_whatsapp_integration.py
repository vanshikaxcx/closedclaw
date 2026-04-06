"""
Test script for WhatsApp integration
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"


async def test_send_whatsapp():
    """Test sending WhatsApp message"""
    print("\n🧪 Test 1: Send WhatsApp Message")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/munim/whatsapp/send",
            json={
                "merchant_id": "demo_merchant",
                "phone": "+919425129512",
                "message": "Test message from Arthsetu Merchant Help WhatsApp integration! 🎉"
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200


async def test_daily_briefing():
    """Test sending daily briefing"""
    print("\n🧪 Test 2: Send Daily Briefing")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/munim/whatsapp/briefing",
            json={
                "merchant_id": "demo_merchant",
                "phone": "+919425129512"
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200


async def test_webhook_text():
    """Test webhook with text command"""
    print("\n🧪 Test 3: Webhook - Text Command")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/munim/whatsapp/webhook",
            data={
                "From": "whatsapp:+919425129512",
                "Body": "aaj ka hisaab",
                "MessageSid": "TEST123"
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200


async def test_get_messages():
    """Test getting message history"""
    print("\n🧪 Test 4: Get Message History")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/munim/whatsapp/messages/demo_merchant"
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Total messages: {data.get('total', 0)}")
        print(f"Messages returned: {len(data.get('messages', []))}")
        return response.status_code == 200


async def test_health():
    """Test Arthsetu Merchant Help health endpoint"""
    print("\n🧪 Test 5: Arthsetu Merchant Help Health Check")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/munim/health")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Arthsetu Merchant Help Status: {data.get('status')}")
        print(f"Services configured:")
        for service, configured in data.get('services', {}).items():
            status = "✅" if configured else "❌"
            print(f"  {status} {service}")
        return response.status_code == 200


async def main():
    """Run all tests"""
    print("=" * 60)
    print("WhatsApp Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health),
        ("Send WhatsApp", test_send_whatsapp),
        ("Daily Briefing", test_daily_briefing),
        ("Webhook Text", test_webhook_text),
        ("Get Messages", test_get_messages),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")


if __name__ == "__main__":
    asyncio.run(main())
