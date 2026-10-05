# Phase 4: Scalability & Reliability Design

## 1. Payment Reliability Matrix (Challenge C Response)

| Scenario | Architectural Response & State Change |
| :--- | :--- |
| **Payment succeeds** | Payment Service records success. Within a single DB transaction, it inserts the PAYMENT record (status=`SUCCESS`) and an OUTBOX_EVENT (`PaymentSucceededEvent`). The Outbox Relay publishes to Kafka. The Order Service consumes it, transitioning the order to `CONFIRMED`. |
| **Payment fails** | Payment Service records failure and inserts an OUTBOX_EVENT (`PaymentFailedEvent`). The Inventory Service consumes this event to release the reservation back to `AVAILABLE` (stock + 1). The Order Service transitions to `CANCELLED`. |
| **Payment times out** | The Payment Service transitions to a `RECONCILIATION_NEEDED` state. A background cron job safely polls the Payment Gateway's reconciliation API using our unique `transaction_ref` to check the definitive status *without* initiating a new payment. |
| **Duplicate payment request (same key)** | The client generates a UUID `idempotency_key` at checkout. The Payment Service stores this with a `UNIQUE` database constraint. Duplicate requests return the cached response of the first request instead of double-charging. |
| **Duplicate payment request (browser refresh / new key)** | Even if the user refreshes and generates a new `idempotency_key`, the `UNIQUE` constraint on `reservation_id` in the PAYMENT table guarantees that a single reservation can never be paid for twice. The second INSERT fails at the database level. |
| **Payment succeeds, but Order Service fails** | The `PaymentSucceededEvent` is safely persisted in the OUTBOX_EVENT table within the same transaction as the payment record. The Outbox Relay publishes it to Kafka. The Order Service, even if temporarily down for 30+ seconds, will eventually come back online, resume consuming from its last committed offset, and create the order (Eventual Consistency). |

---

## 2. Circuit Breaker Pattern

### States & Configuration
| State | Behavior | Transition Trigger |
|-------|----------|-------------------|
| **CLOSED** (Normal) | All requests pass through to the Payment Gateway | Failure rate exceeds 50% over a 10-second sliding window → trip to OPEN |
| **OPEN** (Tripped) | All requests immediately fail-fast with HTTP 503. No calls to the gateway. Inventory is released. | After a 30-second cooldown timer expires → transition to HALF_OPEN |
| **HALF_OPEN** (Probing) | Allow 3 probe requests through. If all succeed → CLOSED. If any fail → OPEN. | Success of all probe requests → CLOSED |

### Fallback Behavior
When the circuit is OPEN, the Payment Service immediately returns a `503 Service Unavailable` response to the Checkout Service, which then publishes a `PaymentFailedEvent` to release the reserved inventory back to the pool.

---

## 3. Transactional Outbox Pattern (Detailed)

### Problem Solved
> If the Payment Service charges the customer's card and then crashes before publishing the `PaymentSucceededEvent` to Kafka, the order is never created. The customer is charged but receives nothing.

### Solution
The payment record AND the event payload are saved to the database in the **exact same transaction**:
```sql
BEGIN;
  INSERT INTO payment (payment_id, reservation_id, status, transaction_ref)
    VALUES (?, ?, 'SUCCESS', ?);
  INSERT INTO outbox_event (event_id, event_type, aggregate_id, payload, status)
    VALUES (?, 'PAYMENT_SUCCEEDED', ?, '{"reservation_id": "..."}', 'PENDING');
COMMIT;
```

### Relay Mechanism
A separate **Outbox Relay** process (polling-based or CDC via Debezium):
1. Reads all `PENDING` rows from the `outbox_event` table.
2. Publishes each event to the appropriate Kafka topic.
3. Updates the row status to `PUBLISHED`.
4. If Kafka is unavailable, the relay retries on the next polling cycle (at-least-once delivery).

### Dead-Letter Queue (DLQ)
Events that fail to publish after 5 retry attempts are moved to a dedicated DLQ Kafka topic for manual investigation and reprocessing.

---

## 4. Reservation Expiry Guard

### Problem Solved
> What happens if the reservation TTL expires while payment is still processing?

### Solution
Before initiating a charge to the external gateway, the Payment Service executes a **status validation query**:
```sql
SELECT status FROM inventory_reservation WHERE reservation_id = ? AND status = 'PAYMENT_PENDING';
```
If the reservation has been released (status = `RELEASED`) by the background cron job, the payment is immediately rejected without charging the card.

---

## 5. Order Service Consumer Deduplication

### Problem Solved
> If Kafka delivers the `PaymentSucceededEvent` twice (at-least-once delivery), can it create duplicate orders?

### Solution
The Order Service consumer performs an **idempotent upsert** keyed on `reservation_id`:
```sql
INSERT INTO orders (order_id, reservation_id, customer_id, status)
VALUES (?, ?, ?, 'CONFIRMED')
ON CONFLICT (reservation_id) DO NOTHING;
```
If the order already exists for this reservation, the duplicate event is silently ignored. This guarantees exactly-once order creation despite at-least-once Kafka delivery.

---

## 6. Jury Defense Narrative: "The Double Click Problem"
*Question: "If a customer experiences network lag and clicks 'Pay Now' three times in quick succession, how exactly does the architecture ensure only one payment transaction is processed and only one order is created?"*

**Defense:**
"If a customer clicks 'Pay Now' three times, our architecture protects them at two levels. First, the client generates a UUID **Idempotency Key**. When the first request hits our Payment Service, it stores this key under a strict `UNIQUE` constraint, instantly rejecting duplicate clicks. Second, to address the 'Browser Refresh' scenario where a user might accidentally generate a brand new Idempotency Key, our database enforces a secondary strict `UNIQUE` constraint on `reservation_id` in the PAYMENT table. This guarantees that a single reservation can never be paid for twice, mathematically ensuring only one payment is processed and one order is created."
