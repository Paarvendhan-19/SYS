# Phase 6: Event & Message Design

*Our architecture heavily leverages Event-Driven Architecture (EDA) via Kafka to decouple services and ensure extreme availability.*

## 1. Domain Event Definitions

### A. `PaymentSucceededEvent`
* **Owner / Publisher:** Payment Service (via Transactional Outbox)
* **JSON Payload Schema:**
```json
{
  "event_id": "evt_991a",
  "event_type": "PAYMENT_SUCCEEDED",
  "timestamp": "2026-10-05T10:02:14Z",
  "data": {
    "transaction_id": "txn_8841a",
    "reservation_id": "res_99f2b1",
    "customer_id": "usr_776",
    "amount_paid": 49.99
  }
}
```
* **Consumer Responsibilities:**
  * **Order Service:** Consumes this event, validates the payload, and transitions the pending order to `CONFIRMED`.

---

### B. `PaymentFailedEvent`
* **Owner / Publisher:** Payment Service
* **JSON Payload Schema:**
```json
{
  "event_id": "evt_991b",
  "event_type": "PAYMENT_FAILED",
  "timestamp": "2026-10-05T10:03:00Z",
  "data": {
    "reservation_id": "res_99f2b1",
    "reason": "CARD_DECLINED_INSUFFICIENT_FUNDS"
  }
}
```
* **Consumer Responsibilities:**
  * **Inventory Service:** Consumes this event to execute compensation logic: Updates the reservation status to `RELEASED`, and increments `available_quantity` by 1, returning the stock to the flash sale pool.
  * **Order Service:** Consumes this event to transition the order state to `CANCELLED`.

---

### C. `OrderConfirmedEvent`
* **Owner / Publisher:** Order Service
* **JSON Payload Schema:**
```json
{
  "event_id": "evt_991c",
  "event_type": "ORDER_CONFIRMED",
  "timestamp": "2026-10-05T10:02:16Z",
  "data": {
    "order_id": "ord_112233",
    "customer_id": "usr_776",
    "shipping_address_id": "addr_99",
    "items": [
      { "product_id": "prod_8f7b9c32", "quantity": 1 }
    ]
  }
}
```
* **Consumer Responsibilities:**
  * **Notification Service:** Listens to this event and dispatches the "Order Successful!" email and SMS to the user asynchronously.
  * **Fulfillment Service:** Listens to this event to generate the warehouse picking slip and prepare the physical package for shipment.

---

## 2. Jury Defense Narrative: "The Asynchronous Trade-off"
*Question: "Why did you choose to make the Order Creation and Notification steps asynchronous rather than processing them in the same synchronous thread as the initial purchase request?"*

**Defense:**
"By making Order Creation and Notifications asynchronous, we aggressively minimize the synchronous 'critical path' of the checkout flow. This ensures that the user receives their immediate payment confirmation in milliseconds rather than waiting for an external email API or a slower order database insert to complete while holding a connection open. While this introduces Eventual Consistency to our system, the trade-off is absolutely necessary to prevent thread starvation, avoid cascading timeouts, and maintain high availability during our 10,000 requests-per-second flash sale."
