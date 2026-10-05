# Phase 3: Database Schema & Transaction Boundaries

## 1. Inventory & Reservation Schema

### `INVENTORY` Table
| Column | Type | Description |
|--------|------|-------------|
| `inventory_id` | UUID (PK) | Unique identifier |
| `product_id` | UUID (FK) | Reference to the product |
| `available_quantity`| INT | Units available to reserve |
| `reserved_quantity` | INT | Units currently locked in carts |
| `sold_quantity` | INT | Units successfully paid for |
| `version` | INT | OCC version control counter |
| `updated_at` | TIMESTAMP | Last modification time |

### `INVENTORY_RESERVATION` Table
| Column | Type | Description |
|--------|------|-------------|
| `reservation_id` | UUID (PK) | Unique reservation identifier |
| `inventory_id` | UUID (FK) | Reference to inventory |
| `customer_id` | UUID | User making the reservation |
| `status` | VARCHAR | `RESERVED`, `PAYMENT_PENDING`, `CONFIRMED`, `SOLD`, `RELEASED` |
| `expires_at` | TIMESTAMP | Time when reservation expires |
| `idempotency_key` | VARCHAR (UNIQUE) | Prevents duplicate requests |

---

## 2. Quantity Shifts Across the Lifecycle
Assuming initial state of 100 units:
1. **AVAILABLE (Start):** `available_quantity` = 100, `reserved_quantity` = 0, `sold_quantity` = 0
2. **RESERVED:** `available_quantity` = 99, `reserved_quantity` = 1, `sold_quantity` = 0
3. **CONFIRMED (Paid):** `available_quantity` = 99, `reserved_quantity` = 0, `sold_quantity` = 1
4. **RELEASED (Failed/Timeout):** `available_quantity` = 100, `reserved_quantity` = 0, `sold_quantity` = 0

---

## 3. Database Transaction Boundaries
To ensure atomicity, these operations must occur within a single database transaction (`BEGIN` ... `COMMIT`):

**Transaction A: Creating a Reservation**
1. `BEGIN`
2. `INSERT INTO INVENTORY_RESERVATION` (using the `idempotency_key` to fail fast on duplicates).
3. `UPDATE INVENTORY` (avail = avail - 1, res = res + 1) `WHERE version = X AND available_quantity > 0`.
4. If update returns 0 rows (version mismatch), `ROLLBACK` and retry with **Exponential Backoff + Jitter**. Otherwise, `COMMIT`.

**Transaction C: Confirming a Reservation (Payment Success)**
1. `BEGIN`
2. `UPDATE INVENTORY_RESERVATION SET status = 'CONFIRMED' WHERE reservation_id = ? AND status = 'PAYMENT_PENDING'`.
3. If 0 rows updated (reservation expired/released), `ROLLBACK` and reject the payment.
4. `COMMIT`.

**Transaction B: Releasing a Reservation (Timeout/Failure)**
1. `BEGIN`
2. `UPDATE INVENTORY_RESERVATION SET status = 'RELEASED' WHERE status = 'RESERVED'`.
3. `UPDATE INVENTORY` (avail = avail + 1, res = res - 1) `WHERE version = X`.
4. `COMMIT`.

---

## 4. Payment Table (Cross-reference)

### `PAYMENT` Table
| Column | Type | Description |
|--------|------|-------------|
| `payment_id` | UUID (PK) | Unique payment identifier |
| `order_id` | UUID (FK) | Reference to the order |
| `reservation_id` | UUID (FK, **UNIQUE**) | **Prevents a single reservation from being paid twice** |
| `transaction_ref` | VARCHAR (UNIQUE) | External gateway reference / idempotency key |
| `status` | VARCHAR | `PENDING`, `SUCCESS`, `FAILED` |
| `processed_at` | TIMESTAMP | Time payment was processed |

> **Critical Constraint:** The `UNIQUE` constraint on `reservation_id` is the ultimate defense against the "Browser Refresh" double-payment scenario. Even if a user generates a new idempotency key, a second successful payment for the same reservation is mathematically impossible.

---

## 5. Outbox Table (Transactional Outbox Pattern)

### `OUTBOX_EVENT` Table
| Column | Type | Description |
|--------|------|-------------|
| `event_id` | UUID (PK) | Unique event identifier |
| `event_type` | VARCHAR | `PAYMENT_SUCCEEDED`, `PAYMENT_FAILED`, `ORDER_CONFIRMED` |
| `aggregate_id` | UUID | The reservation_id or order_id this event relates to |
| `payload` | JSONB | Full event payload for Kafka publishing |
| `status` | VARCHAR | `PENDING`, `PUBLISHED` |
| `created_at` | TIMESTAMP | Event creation time |

> **Transaction Boundary:** The payment record and the outbox event row are inserted within the **exact same database transaction** (`BEGIN` ... `COMMIT`). A separate Outbox Relay process (CDC or polling) reads `PENDING` rows, publishes them to Kafka, and marks them `PUBLISHED`.

---

## 6. Database Constraints Summary

| Constraint | Table | Purpose |
|------------|-------|---------|
| `CHECK (available_quantity >= 0)` | INVENTORY | Prevents negative stock at the DB level |
| `UNIQUE (idempotency_key)` | INVENTORY_RESERVATION | Prevents duplicate reservation requests |
| `UNIQUE (reservation_id)` | PAYMENT | Prevents double-charging a single reservation |
| `UNIQUE (transaction_ref)` | PAYMENT | Prevents duplicate gateway charges |
| `version` column + OCC WHERE clause | INVENTORY | Prevents concurrent overwrites |

---

## 7. How Guarantees are Enforced
* **Duplicate Prevention:** The `idempotency_key` on the reservation table has a `UNIQUE` constraint. If a customer clicks "Buy Now" twice, the database strictly rejects the second `INSERT`, ensuring they only get one reservation.
* **Double-Payment Prevention:** The `UNIQUE` constraint on `reservation_id` in the PAYMENT table ensures that even if a user refreshes the browser and generates a new idempotency key, a reservation can never be charged twice.
* **Abandoned Carts:** The `expires_at` field allows an asynchronous background cron job (or TTL event) to safely execute **Transaction B**, sweeping up expired reservations and returning stock to the pool.
* **Reservation Expiry Guard:** Before charging, the Payment Service validates that the reservation status is still `PAYMENT_PENDING` (not `RELEASED`). If the reservation has expired, the payment is rejected.

---

## 8. Jury Defense Narrative: "The 100th Unit Problem"
*Question: "What happens if two requests reach the database at the exact same time for the very last unit?"*

**Defense:**
"When two requests reach the database simultaneously for the last unit, our Optimistic Concurrency Control (versioning) guarantees strict consistency. Both transactions will initially read the inventory with `version = N`. However, the database enforces that only the first transaction to commit will successfully update the row to `version = N+1`. The second transaction will encounter a version mismatch, its update will return zero affected rows, and it will be forced to retry using Exponential Backoff with Jitter. Upon retrying, it will see `available_quantity = 0` and safely reject the request, mathematically guaranteeing we never oversell. Furthermore, the `CHECK (available_quantity >= 0)` constraint provides a hard database-level safety net."
