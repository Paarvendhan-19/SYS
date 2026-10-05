import asyncio
import uuid

class MockPaymentService:
    """Simulates our Payment Service with database-level idempotency checks."""
    def __init__(self):
        self.processed_keys = set()
        self.database_lock = asyncio.Lock()
        self.actual_charges_made = 0

    async def process_payment(self, idempotency_key):
        """Simulates processing a payment with strict uniqueness checks."""
        # Simulating strict database UNIQUE constraint check
        async with self.database_lock:
            if idempotency_key in self.processed_keys:
                return {"status": 200, "message": "Cached Success (Duplicate Prevented)"}
            
            # First time seeing this key, process payment
            self.processed_keys.add(idempotency_key)
            self.actual_charges_made += 1
            
        # Simulating external gateway latency
        await asyncio.sleep(0.1)
        return {"status": 200, "message": "Payment Success (Card Charged)"}

async def simulate_double_click():
    payment_service = MockPaymentService()
    
    # The client generates ONE key for the checkout intent
    idempotency_key = str(uuid.uuid4())
    
    print(f"Simulating network lag: User clicking 'Pay Now' 3 times instantly.")
    print(f"Idempotency Key: {idempotency_key}\n")
    
    # 3 concurrent requests arrive with the exact same key
    tasks = [
        payment_service.process_payment(idempotency_key),
        payment_service.process_payment(idempotency_key),
        payment_service.process_payment(idempotency_key)
    ]
    
    responses = await asyncio.gather(*tasks)
    
    for i, resp in enumerate(responses):
        print(f"Request {i+1} Response: {resp['message']}")
        
    print(f"\nTotal Actual Charges Made: {payment_service.actual_charges_made}")
    
    # Strict Assertion
    assert payment_service.actual_charges_made == 1, "Failed: Card was charged multiple times!"
    
    print("\n✅ TEST PASSED: Idempotency strictly prevented duplicate charges.")

if __name__ == "__main__":
    asyncio.run(simulate_double_click())
