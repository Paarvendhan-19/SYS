# Phase 7: Architecture Decision Records (ADRs)

## ADR 1: Redis vs. Memcached for Traffic Shedding
* **Context:** We need an in-memory cache to absorb 10,000 concurrent requests and shed 9,900 losers instantly.
* **Decision:** We chose **Redis**.
* **Reasoning:** Redis natively supports the atomic `DECR` command out of the box, guaranteeing thread-safe decrements. Furthermore, we mandate that every Redis reservation key includes a short TTL (Time to Live) and a background cron reconciliation job to automatically release "Ghost Units" if a microservice crashes before persisting to the DB. Memcached lacks the advanced data structures required for this.

## ADR 2: Optimistic Concurrency Control (OCC) vs. Pessimistic Locking
* **Context:** The final 100 successful requests hit the PostgreSQL database simultaneously to claim inventory.
* **Decision:** We chose **Optimistic Concurrency Control (OCC)**.
* **Reasoning:** Pessimistic locking (`SELECT FOR UPDATE`) holds database locks, which starves connection pools under high load. OCC handles collisions cleanly by throwing a version mismatch. To prevent the massive "Thundering Herd" thread-locking scenario during retries, we explicitly implemented an **Exponential Backoff with Jitter** retry algorithm, randomly staggering the retry attempts of the 100 winners to ensure smooth database commits.

## ADR 3: Kafka vs. RabbitMQ for Event Streaming
* **Context:** We need a reliable message broker for our Transactional Outbox pattern to orchestrate order creation asynchronously.
* **Decision:** We chose **Apache Kafka**.
* **Reasoning:** Kafka's append-only log architecture provides massive throughput and inherent message replayability. This pairs perfectly with the Outbox pattern, guaranteeing at-least-once delivery even during catastrophic order service failures. RabbitMQ's transient queuing model is less suited for guaranteed event sourcing at high scale.
