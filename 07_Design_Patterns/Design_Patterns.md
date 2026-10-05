# Phase 5: Design Patterns Application

### 1. Strategy Pattern
* **Context:** Selecting between different payment providers (Stripe vs PayPal).
* **Application:** We encapsulate the payment logic into interchangeable strategy classes implementing `IPaymentProvider`. The system dynamically selects the strategy at runtime based on the user's selected payment method.

### 2. Adapter Pattern
* **Context:** External Payment Gateway integration.
* **Application:** Stripe and PayPal have different SDK signatures. We use the Adapter pattern (`StripeAdapter`) to translate our internal domain request into the specific JSON/API format required by the external gateway, insulating our core logic from third-party API changes.

### 3. Repository Pattern
* **Context:** Database concurrency and persistence.
* **Application:** The `IInventoryRepository` abstracts away the complex Optimistic Concurrency Control (OCC) SQL statements. The business logic only knows if `reserveInventory()` returned true or false, completely hiding the underlying PostgreSQL version-checking mechanism.

### 4. Observer Pattern
* **Context:** Asynchronous downstream processing (Event-Driven Architecture).
* **Application:** We utilize Kafka as our message broker. When the `OrderService` publishes an `OrderConfirmedEvent`, the `NotificationService` and `FulfillmentService` act as observers, consuming the event asynchronously to send emails and print shipping labels without blocking the user's checkout response.
