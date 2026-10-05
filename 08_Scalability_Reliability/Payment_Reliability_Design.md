# Phase 4: Scalability & Reliability Design

## 1. Payment Reliability & Failure Handling
* **Circuit Breaker Pattern:** To protect our internal connection pools from an unstable external payment gateway (Stripe/PayPal), we wrap outbound API calls in a Circuit Breaker. If the gateway times out or returns excessive 5xx errors, the breaker trips open, instantly fast-failing subsequent requests to keep our system responsive.
* **Transactional Outbox Pattern:** To guarantee that an order is created if a payment succeeds, the Payment Service saves the payment record and a `PaymentSucceededEvent` payload into a database Outbox table within the exact same database transaction. A separate relay process publishes this to Kafka, guaranteeing at-least-once delivery even if the Payment Service crashes immediately after charging the card.

## 2. Idempotency & The "Browser Refresh" Defense
* **Problem:** Network lag causes users to mash the "Pay Now" button, or refresh the browser, potentially generating a new idempotency key.
* **Solution:** While we use a client-provided `Idempotency-Key` in the HTTP header as the first line of defense, our ultimate guarantee is at the database level. We enforce a **strict UNIQUE constraint on `reservation_id`** linked to a successful payment state. This means it is mathematically impossible for a single reservation to be paid for twice, completely neutralizing the double-charge risk on browser refreshes.
