# Phase 6: API Specifications

## REST/gRPC API Contracts

### 1. Create Reservation
* **Endpoint:** `POST /api/v1/reservations`
* **Headers:** `Authorization: Bearer <JWT>`, `Idempotency-Key: <UUID>`
* **Request Payload:**
```json
{
  "product_id": "uuid-123",
  "quantity": 1
}
```
* **Response (201 Created):**
```json
{
  "reservation_id": "res-456",
  "status": "RESERVED",
  "expires_at": "2026-10-05T10:05:00Z"
}
```

### 2. Execute Payment
* **Endpoint:** `POST /api/v1/payments`
* **Headers:** `Authorization: Bearer <JWT>`, `Idempotency-Key: <UUID>`
* **Request Payload:**
```json
{
  "reservation_id": "res-456",
  "payment_token": "tok_stripe_abc",
  "gateway": "STRIPE"
}
```
* **Response (200 OK):**
```json
{
  "payment_id": "pay-789",
  "status": "SUCCESS"
}
```

### 3. Asynchronous Event Schema (Kafka)
* **Topic:** `sales.orders.events`
* **Payload (`PaymentSucceededEvent`):**
```json
{
  "event_id": "evt-111",
  "event_type": "PAYMENT_SUCCEEDED",
  "payload": {
    "reservation_id": "res-456",
    "amount": 99.99
  },
  "timestamp": "2026-10-05T10:01:00Z"
}
```
