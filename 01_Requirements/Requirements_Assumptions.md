# Phase 1: Requirements & Assumptions

## 1. Functional Requirements
* **Product Discovery:** Users can browse flash-sale products.
* **Inventory Reservation:** The system securely locks inventory during checkout.
* **Payment Processing:** Integrates with Stripe/PayPal to authorize payments.
* **Order Lifecycle:** Confirms orders on payment success or releases stock on failure/timeout.

## 2. Non-Functional Requirements (NFRs)
* **Throughput (TPS Target):** The system must smoothly handle **10,000 Transactions Per Second (TPS)** during the initial burst.
* **Latency:** Inventory reservation must complete in < 100ms.
* **Consistency:** Strict transactional consistency required for the 100 inventory units.

## 3. Hardware Assumptions & Deployment Experience
Drawing from our team's experience deploying highly scalable analytics platforms on Zoho Catalyst, we assume the following hardware/cloud capabilities:
* **Stateless Compute:** API Gateway and microservices will run on auto-scaling Kubernetes node groups capable of scaling from 10 to 500 pods in seconds.
* **Traffic Shedding Tier:** A highly available Redis cluster with sufficient memory and network bandwidth to absorb the 10,000 TPS spike instantly.
* **Relational Database:** PostgreSQL clusters configured with high connection limits (PgBouncer) and fast SSDs, though our architecture restricts actual database writes to only the 100 successful requests.

## 4. Strict Security & Idempotency Mandates
* A unique constraint on `reservation_id` must be enforced at the database level to prevent double charges if a user refreshes their browser and bypasses frontend caching.
