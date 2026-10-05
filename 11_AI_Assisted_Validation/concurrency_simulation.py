import concurrent.futures
import threading
import time

class MockRedisCache:
    """Simulates Redis atomic DECR operations to shed traffic."""
    def __init__(self, initial_stock):
        self.stock = initial_stock
        self.lock = threading.Lock()

    def decr(self):
        """Simulates atomic decrement with thread locking."""
        with self.lock:
            self.stock -= 1
            return self.stock

def simulate_checkout_thread(redis_cache, results, results_lock):
    """Simulates a single customer thread attempting to buy."""
    stock_remaining = redis_cache.decr()
    
    with results_lock:
        if stock_remaining >= 0:
            results['success'] += 1
        else:
            results['rejected'] += 1

def main():
    TOTAL_THREADS = 10000
    AVAILABLE_UNITS = 100
    
    redis_cache = MockRedisCache(AVAILABLE_UNITS)
    results = {'success': 0, 'rejected': 0}
    results_lock = threading.Lock()
    
    print(f"Simulating {TOTAL_THREADS} concurrent threads hitting Redis DECR...")
    start_time = time.time()
    
    # Fire all 10,000 threads concurrently using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=2000) as executor:
        futures = [executor.submit(simulate_checkout_thread, redis_cache, results, results_lock) for _ in range(TOTAL_THREADS)]
        concurrent.futures.wait(futures)
        
    print(f"\nSimulation completed in {time.time() - start_time:.3f} seconds")
    print(f"Successful Reservations: {results['success']}")
    print(f"Rejected Requests: {results['rejected']}")
    
    # Mathematical proof assertions
    assert results['success'] == 100, f"Expected 100 successes, got {results['success']}"
    assert results['rejected'] == 9900, f"Expected 9900 rejections, got {results['rejected']}"
    
    print("\n✅ TEST PASSED: Exactly 100 units reserved, 9900 safely shed (No Overselling).")

if __name__ == "__main__":
    main()
