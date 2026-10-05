# Final 5-Minute Pitch Script
**Team Members:** Vetrivel, Nithiya, Saaiprasath

---

### [0:00 - 1:30] Problem, Requirements, & HLD (90 sec)
**🎤 Vetrivel (System Architect):**
"Good morning Jury. We are Vetrivel, Nithiya, and Saaiprasath. Drawing from our rapid deployment experience on Zoho Catalyst, we tackled the core challenge of SALESTORM: 10,000 eager customers competing for 100 limited-stock units. Our strict guarantees were zero overselling and exactly-once order creation under massive load.
Our High-Level Design intercepts traffic through an API Gateway with WAF rate-limiting. We split our domain into independent microservices. We made the checkout and inventory reservation strictly synchronous to guarantee stock, while decoupling the Payment and Order processing asynchronously using Kafka to ensure lightning-fast response times."

### [1:30 - 2:30] Critical Design: The 100th Unit Scenario (60 sec)
**🎤 Nithiya (Reliability Engineer):**
"To handle the massive concurrency spike, we implemented a dual-layer defense. First, we use a Redis atomic `DECR` cache to shed 9,900 losers instantly. To prevent 'Ghost Units' during pod crashes, every Redis key has a strict TTL and a background cron reconciler.
To answer the jury's exact question regarding the 100th unit: Only 100 winners proceed to PostgreSQL. We use Optimistic Concurrency Control (OCC). If multiple users hit the database simultaneously, version checks prevent overwrites. To solve the 'Thundering Herd' problem of retries locking up threads, we implemented an **Exponential Backoff with Jitter** retry algorithm. This staggers the final commits mathematically, guaranteeing zero locks and zero overselling."

### [2:30 - 4:00] Payment, Order & LLD Patterns (90 sec)
**🎤 Saaiprasath (Data & API Engineer):**
"For the payment and order flow, reliability is paramount. We implemented the **Circuit Breaker** pattern to protect our internal threads from external Stripe or PayPal timeouts. 
To prevent duplicate charges on browser refreshes, our database enforces a strict `UNIQUE` constraint on the `reservation_id` tied to a successful payment. You cannot pay for a reservation twice.
Finally, to guarantee the order is created after a successful charge, we utilize the **Transactional Outbox Pattern**. The payment record and the Kafka event are saved in the exact same database transaction, ensuring zero dropped orders even if the server crashes."

### [4:00 - 5:00] Scalability, Validation & Closing (60 sec)
**🎤 Vetrivel (System Architect):**
"We didn't just theorize this; we proved it. In our submission, you'll find a Python multithreading validation script utilizing `concurrent.futures` simulating 10,000 exact simultaneous threads, mathematically proving our architecture sheds the load seamlessly.
By relying on Redis for traffic shedding, OCC with Jitter for persistence, and Kafka for asynchronous scale, we have delivered a robust, highly defensible flash-sale architecture. Thank you."
