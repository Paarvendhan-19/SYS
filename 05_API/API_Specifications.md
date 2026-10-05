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
* **Success Response (201 Created):**
```json
{
  "reservation_id": "res-456",
  "status": "RESERVED",
  "expires_at": "2026-10-05T10:05:00Z"
}
```
* **Error Responses:**

| Status Code | Condition | Response Body |
|-------------|-----------|---------------|
| `400 Bad Request` | Invalid payload or missing fields | `{"error": "INVALID_REQUEST", "message": "product_id is required"}` |
| `409 Conflict` | Duplicate idempotency key | `{"error": "DUPLICATE_REQUEST", "message": "Reservation already exists", "reservation_id": "res-456"}` |
| `410 Gone` | Product sold out (Redis counter < 0) | `{"error": "OUT_OF_STOCK", "message": "Item is sold out"}` |
| `429 Too Many Requests` | Rate limit exceeded | `{"error": "RATE_LIMITED", "message": "Retry after 1 second"}` |
| `503 Service Unavailable` | Redis or DB unavailable | `{"error": "SERVICE_UNAVAILABLE", "message": "Please try again later"}` |

---

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
* **Success Response (200 OK):**
```json
{
  "payment_id": "pay-789",
  "status": "SUCCESS",
  "transaction_ref": "txn_stripe_xyz"
}
```
* **Error Responses:**

| Status Code | Condition | Response Body |
|-------------|-----------|---------------|
| `400 Bad Request` | Missing or invalid reservation_id | `{"error": "INVALID_REQUEST", "message": "reservation_id is required"}` |
| `402 Payment Required` | Card declined or insufficient funds | `{"error": "PAYMENT_FAILED", "message": "Card declined"}` |
| `404 Not Found` | Reservation does not exist | `{"error": "RESERVATION_NOT_FOUND", "message": "No reservation found"}` |
| `409 Conflict` | Reservation already paid (UNIQUE violation on reservation_id) | `{"error": "ALREADY_PAID", "message": "This reservation has already been paid"}` |
| `410 Gone` | Reservation expired (status = RELEASED) | `{"error": "RESERVATION_EXPIRED", "message": "Reservation has expired. Please reserve again"}` |
| `503 Service Unavailable` | Payment gateway circuit breaker OPEN | `{"error": "GATEWAY_UNAVAILABLE", "message": "Payment gateway temporarily unavailable"}` |
| `504 Gateway Timeout` | Payment gateway timed out | `{"error": "GATEWAY_TIMEOUT", "message": "Payment processing timed out. Do NOT retry — reconciliation in progress"}` |

---

### 3. Get Order Status
* **Endpoint:** `GET /api/v1/orders/{order_id}`
* **Headers:** `Authorization: Bearer <JWT>`
* **Success Response (200 OK):**
```json
{
  "order_id": "ord-112233",
  "status": "CONFIRMED",
  "reservation_id": "res-456",
  "total_amount": 99.99,
  "created_at": "2026-10-05T10:02:16Z"
}
```
* **Error Responses:**

| Status Code | Condition | Response Body |
|-------------|-----------|---------------|
| `404 Not Found` | Order does not exist | `{"error": "ORDER_NOT_FOUND", "message": "No order found with this ID"}` |

---

### 4. Get Product (Flash Sale)
* **Endpoint:** `GET /api/v1/products/{product_id}`
* **Headers:** `Authorization: Bearer <JWT>` (optional for browse)
* **Success Response (200 OK):**
```json
{
  "product_id": "prod-8f7b9c32",
  "name": "Limited Edition Flash Sale Item",
  "price": 99.99,
  "available": true,
  "flash_sale_active": true
}
```

---

## Asynchronous Event Schema (Kafka)

### PaymentSucceededEvent
* **Topic:** `sales.payments.events`
* **Partition Key:** `reservation_id`
* **Payload:**
```json
{
  "event_id": "evt-111",
  "event_type": "PAYMENT_SUCCEEDED",
  "payload": {
    "reservation_id": "res-456",
    "payment_id": "pay-789",
    "customer_id": "usr-776",
    "amount": 99.99,
    "transaction_ref": "txn_stripe_xyz"
  },
  "timestamp": "2026-10-05T10:01:00Z"
}
```
* **Consumer:** Order Service (idempotent upsert keyed on reservation_id)
* **Retry Policy:** 3 retries with exponential backoff. After 3 failures → Dead-Letter Queue (`sales.payments.events.dlq`)
