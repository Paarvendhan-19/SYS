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
| `status` | VARCHAR | `RESERVED`, `CONFIRMED`, `RELEASED` |
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
4. If update returns 0 rows (version mismatch), `ROLLBACK` and retry. Otherwise, `COMMIT`.

**Transaction B: Releasing a Reservation (Timeout/Failure)**
1. `BEGIN`
2. `UPDATE INVENTORY_RESERVATION SET status = 'RELEASED' WHERE status = 'RESERVED'`.
3. `UPDATE INVENTORY` (avail = avail + 1, res = res - 1) `WHERE version = X`.
4. `COMMIT`.

---

## 4. How Guarantees are Enforced
* **Duplicate Prevention:** The `idempotency_key` on the reservation table has a `UNIQUE` constraint. If a customer clicks "Buy Now" twice, the database strictly rejects the second `INSERT`, ensuring they only get one reservation.
* **Abandoned Carts:** The `expires_at` field allows an asynchronous background cron job (or TTL event) to safely execute **Transaction B**, sweeping up expired reservations and returning stock to the pool.

---

## 5. Jury Defense Narrative: "The 100th Unit Problem"
*Question: "What happens if two requests reach the database at the exact same time for the very last unit?"*

**Defense:**
"When two requests reach the database simultaneously for the last unit, our Optimistic Concurrency Control (versioning) guarantees strict consistency. Both transactions will initially read the inventory with `version = N`. However, the database enforces that only the first transaction to commit will successfully update the row to `version = N+1`. The second transaction will encounter a version mismatch, its update will return zero affected rows, and it will be forced to retry. Upon retrying, it will see `available_quantity = 0` and safely reject the request, mathematically guaranteeing we never oversell."
