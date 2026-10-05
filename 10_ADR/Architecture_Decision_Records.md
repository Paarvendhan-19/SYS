# Phase 7: Architecture Decision Records (ADRs)

## ADR 1: Redis vs. Memcached for Traffic Shedding
* **Context:** We need an in-memory cache to absorb 10,000 concurrent requests and shed 9,900 losers instantly.
* **Decision:** We chose **Redis**.
* **Alternatives Considered:** Memcached, database-only admission control.
* **Reasoning:** Redis natively supports the atomic `DECR` command out of the box, guaranteeing thread-safe decrements within a single-threaded event loop. Furthermore, we mandate that every Redis reservation key includes a short TTL (Time to Live) and a background cron reconciliation job to automatically release "Ghost Units" if a microservice crashes before persisting to the DB. Memcached lacks atomic counter operations, persistence, and the advanced data structures required for this.
* **Trade-offs:** Introduces Redis as a critical infrastructure dependency. Requires TTL management and cron reconciliation. Adds operational complexity but eliminates database overload.

## ADR 2: Optimistic Concurrency Control (OCC) vs. Pessimistic Locking
* **Context:** The final 100 successful requests hit the PostgreSQL database simultaneously to claim inventory.
* **Decision:** We chose **Optimistic Concurrency Control (OCC)** with a `version` column.
* **Alternatives Considered:** Pessimistic Locking (`SELECT ... FOR UPDATE`), Serializable Isolation Level.
* **Reasoning:** Pessimistic locking holds database locks, which starves connection pools under concurrent load. OCC handles collisions cleanly by returning 0 affected rows on version mismatch. To prevent the massive "Thundering Herd" thread-locking scenario during retries, we explicitly implemented an **Exponential Backoff with Jitter** retry algorithm: `delay = min(cap, base × 2^attempt) + random_jitter`, randomly staggering the retry attempts of the 100 winners to ensure smooth database commits.
* **Trade-offs:** Requires application-level retry logic. Retry storms are mitigated by jitter. Slightly more complex code but zero database lock contention.

## ADR 3: Kafka vs. RabbitMQ for Event Streaming
* **Context:** We need a reliable message broker for our Transactional Outbox pattern to orchestrate order creation asynchronously.
* **Decision:** We chose **Apache Kafka**.
* **Alternatives Considered:** RabbitMQ, Amazon SQS, direct synchronous REST calls.
* **Reasoning:** Kafka's append-only log architecture provides massive throughput and inherent message replayability. This pairs perfectly with the Outbox pattern, guaranteeing at-least-once delivery even during catastrophic order service failures. RabbitMQ's transient queuing model is less suited for guaranteed event sourcing at high scale. Direct REST calls would couple the Payment Service to the Order Service, creating a cascading failure risk.
* **Trade-offs:** Kafka is operationally complex (Zookeeper/KRaft, partitioning, consumer groups). Introduces eventual consistency for order creation. Requires idempotent consumers.

## ADR 4: Transactional Outbox vs. Two-Phase Commit (2PC) vs. Saga Choreography
* **Context:** When a payment succeeds, we must guarantee that a `PaymentSucceededEvent` is published to Kafka so the Order Service can create the order. If the application crashes after charging the card but before publishing the event, the order is lost.
* **Decision:** We chose the **Transactional Outbox Pattern**.
* **Alternatives Considered:**
  * *Two-Phase Commit (2PC):* Locks resources across distributed systems (database + Kafka). Extremely slow and fragile.
  * *Saga Choreography:* Services communicate entirely via events with compensation. Complex to trace and debug.
  * *Direct Publishing:* Dangerous; if the app crashes after charging but before publishing, the order is permanently lost.
* **Reasoning:** The Outbox pattern saves the event payload into an `outbox_event` table within the exact same database transaction as the payment record. A separate relay process (polling or CDC) reads pending events and publishes them to Kafka. This guarantees at-least-once delivery with minimal latency overhead.
* **Trade-offs:** Adds minor latency (relay polling interval). Requires an outbox table and relay infrastructure. Introduces at-least-once delivery semantics, requiring idempotent consumers.
