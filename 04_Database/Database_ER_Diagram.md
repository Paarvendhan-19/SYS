```mermaid
erDiagram
    PRODUCT ||--o{ INVENTORY : "has"
    CUSTOMER ||--o{ ORDER : "places"
    ORDER ||--o{ ORDER_ITEM : "contains"
    ORDER ||--o{ PAYMENT : "requires"
    INVENTORY_RESERVATION ||--|{ PAYMENT : "linked to"
    INVENTORY ||--o{ INVENTORY_RESERVATION : "locks"
    
    INVENTORY {
        uuid inventory_id PK
        uuid product_id FK
        int available_quantity "CHECK >= 0"
        int reserved_quantity
        int sold_quantity
        int version "OCC constraint"
        timestamp updated_at
    }
    
    INVENTORY_RESERVATION {
        uuid reservation_id PK
        uuid inventory_id FK
        uuid customer_id FK
        string idempotency_key UK "Unique duplicate prevention"
        string status "RESERVED, CONFIRMED, SOLD, RELEASED"
        timestamp expires_at
        timestamp created_at
    }
    
    ORDER {
        uuid order_id PK
        uuid customer_id FK
        uuid reservation_id FK_UK "UNIQUE for idempotent upsert"
        string status "CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED"
        decimal total_amount
        timestamp created_at
    }
    
    ORDER_ITEM {
        uuid order_item_id PK
        uuid order_id FK
        uuid product_id FK
        int quantity
        decimal unit_price
    }
    
    PAYMENT {
        uuid payment_id PK
        uuid order_id FK
        uuid reservation_id FK_UK "UNIQUE - prevents double charge"
        string transaction_ref UK "External gateway reference"
        string idempotency_key UK "Client-generated dedup key"
        string status "PENDING, SUCCESS, FAILED, RECONCILIATION_NEEDED"
        timestamp processed_at
    }

    OUTBOX_EVENT {
        uuid event_id PK
        string event_type "PAYMENT_SUCCEEDED, PAYMENT_FAILED, ORDER_CONFIRMED"
        uuid aggregate_id "reservation_id or order_id"
        jsonb payload "Full Kafka event payload"
        string status "PENDING, PUBLISHED"
        timestamp created_at
    }
```
