# Phase 7: Trade-offs & Architecture Defense

## 1. The "Trade-off Requirement" Statement
*(Mandatory response to Section 10 of the hackathon brief)*

In designing the SALESTORM platform, we made explicit, calculated sacrifices to guarantee data integrity and system availability under extreme flash-sale pressure:
1. **We sacrifice Synchronous Simplicity for Asynchronous Resilience:** We abandon linear, easy-to-debug code paths in favor of an Event-Driven Architecture (Kafka) and the Transactional Outbox Pattern. This makes the system significantly harder to trace and debug, but strictly isolates failures so an Order Service outage cannot bring down the Payment Service.
2. **We sacrifice Database Simplicity for Horizontal Scalability:** Instead of relying entirely on PostgreSQL, we inject a distributed cache (Redis) as an atomic traffic shedder. This requires our engineering team to manage two data tiers, but it is the only way to prevent our relational database from collapsing under 10,000 concurrent writes.
3. **We sacrifice Availability for Strict Consistency (CAP Theorem):** In the event of a network partition between our microservices and our inventory database, we will explicitly reject customer requests rather than risk overselling the 100 units. Consistency is our absolute priority.

---

## 2. Jury Defense Narrative: "The Ultimate Bottleneck"
*Question: "Which component is the likely bottleneck when traffic increases by 50x (to 500,000 requests/sec), and exactly how will it scale?"*

**Defense:**
"When traffic spikes by 50x to 500,000 requests per second, our primary relational database will become the ultimate bottleneck due to strict connection pool limits and maximum write-throughput capacities. To handle this extreme scale, our architecture will evolve in two ways: first, we will heavily shard our PostgreSQL database by `product_id` to distribute the write load across multiple physical clusters. Second, we will lean entirely on a queue-based ingress strategy where the API Gateway immediately drops all valid requests into a massive Kafka buffer, completely decoupling the traffic burst from our data tier and allowing our services to process the queue sequentially at their maximum safe capacity."
