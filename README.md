# SALESTORM System Design Hackathon - Final Submission

## Executive Summary
This repository contains our team's (Vetrivel, Nithiya, and Saaiprasath) highly defensible architectural blueprint for the SALESTORM E-Commerce Flash Sale platform. Drawing on our rapid deployment experience building scalable solutions on Zoho Catalyst, we designed a system capable of handling **10,000 concurrent checkout requests for exactly 100 limited-stock units without overselling or crashing.**

Our architecture heavily leverages a **Redis DECR atomic counter** (with strict TTLs) as a primary traffic shedder, **Optimistic Concurrency Control (OCC) with Exponential Backoff and Jitter** at the database tier to prevent Thundering Herds, and the **Transactional Outbox Pattern** to guarantee message delivery to Kafka.

---

## Directory Index

* **`01_Requirements/`**: Hardware assumptions and TPS targets.
* **`02_HLD/`**: High-Level Context, Container, Component, and Deployment diagrams.
* **`03_LLD/`**: Unified Class diagrams, Sequence diagrams, and Order/Reservation state machines.
* **`04_Database/`**: Database schema constraints and transaction boundaries.
* **`05_API/`**: REST/gRPC API specifications and event payload schemas.
* **`06_SOLID/`**: Detailed SOLID principles mapping (DIP, OCP, etc.).
* **`07_Design_Patterns/`**: Implementation of Strategy, Adapter, Repository, and Observer patterns.
* **`08_Scalability_Reliability/`**: Transactional Outbox, Circuit Breaker, and Idempotency logic.
* **`09_Security_Observability/`**: JWT auth, rate limiting, and distributed tracing.
* **`10_ADR/`**: Architecture Decision Records (Redis vs. Memcached, OCC vs. Pessimistic, Kafka vs. RabbitMQ).
* **`11_AI_Assisted_Validation/`**: Multithreaded Python simulation script (`concurrent.futures`).
* **`12_Presentation/`**: 5-minute Final Pitch Script for Vetrivel, Nithiya, and Saaiprasath.

---

## How to Validate

We built a multithreaded Python script to mathematically prove our concurrency logic handles 10,000 threads perfectly. Run it via:
```bash
python3 11_AI_Assisted_Validation/concurrency_simulation.py
```
