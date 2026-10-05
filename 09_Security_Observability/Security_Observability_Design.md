# Phase 9: Security & Observability Design

## 1. Security Strategy
* **Authentication:** All incoming requests to the API Gateway are authenticated using stateless JSON Web Tokens (JWT). The API Gateway validates signatures locally before forwarding traffic to microservices.
* **Rate Limiting & WAF:** We employ a Token Bucket algorithm at the API Gateway to throttle abusive IPs, restricting traffic to 5 requests per second per user. A Cloud WAF sits at the edge to absorb DDoS attempts.
* **Data Security:** The system never handles raw credit card data. The frontend tokenizes payment info directly with Stripe/PayPal, sending only the secure token to our backend (PCI-DSS compliance).

## 2. Observability & Monitoring
* **Distributed Tracing:** We inject a `trace_id` (W3C Trace Context) at the API Gateway, passing it through HTTP headers and Kafka message payloads. This allows us to trace a user's checkout journey across all synchronous and asynchronous boundaries.
* **Key Metrics & Automated Alerts:**
  * **Queue Backlog Alert:** If Kafka consumer lag on the Order Service topic exceeds a critical threshold (e.g., 500 unacknowledged messages), an automated alert fires to trigger pod autoscaling.
  * **Ghost Unit Alert:** A background cron job periodically reconciles the Redis `DECR` counters with the database's `available_quantity`. If discrepancies are found, an alert is triggered to investigate TTL or network partition failures.
