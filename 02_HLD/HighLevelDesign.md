# Phase 2: High-Level Design (HLD)

## 1. System Context Diagram
*This diagram illustrates the highest-level view of the SALESTORM platform and its external dependencies.*

```mermaid
C4Context
title System Context Diagram - SALESTORM Platform

Person(customer, "Customer", "A user attempting to purchase a flash sale item.")
System(salestorm, "SALESTORM E-Commerce Platform", "Handles flash sale, inventory, checkout, and orders.")
System_Ext(payment_gw, "Payment Gateway", "External system for processing credit card payments.")
System_Ext(notification_svc, "Notification & Delivery System", "External partners for SMS/Email and shipping.")

Rel(customer, salestorm, "Discovers products, adds to cart, checks out", "HTTPS")
Rel(salestorm, payment_gw, "Processes payments", "HTTPS/TLS")
Rel(salestorm, payment_gw, "Handles Refunds/Expirations", "HTTPS/TLS")
Rel(salestorm, notification_svc, "Sends order updates and ships products", "HTTPS")
```

## 2. Container & Service Architecture Diagram
*This maps out the flow from the edge (CDN/WAF) down to the microservices, databases, and message queues.*

```mermaid
C4Container
title Container Architecture - Flash Sale Flow

Person(customer, "Customer", "Flash Sale Participant")
System_Boundary(c1, "SALESTORM Architecture") {
    Container(cdn, "CDN / WAF", "Cloudflare / AWS CloudFront", "Caches static content, mitigates DDoS")
    Container(lb, "Load Balancer", "ALB", "Distributes incoming traffic")
    Container(api_gw, "API Gateway", "Kong / AWS API Gateway", "Routing, Rate Limiting, Auth")

    Container(product_svc, "Product Service", "Go/Java", "Serves product catalog")
    ContainerDb(product_db, "Product DB", "PostgreSQL", "Read-replica optimized")

    Container(cart_svc, "Cart Service", "Go/Java", "Manages user carts")
    ContainerDb(cart_cache, "Cart Cache", "Redis", "Low latency cart storage")

    Container(inventory_svc, "Inventory/Reservation Service", "Go/Java", "Manages stock & locks")
    ContainerDb(inventory_redis, "Reservation Cache (Atomic)", "Redis Cluster", "Handles 10k req/sec DECR")
    ContainerDb(inventory_db, "Inventory DB", "PostgreSQL", "Persistent inventory state")

    Container(checkout_svc, "Checkout Service", "Go/Java", "Orchestrates checkout flow")
    
    Container(payment_svc, "Payment Service", "Go/Java", "Integrates with external gateway")
    
    Container(order_svc, "Order Service", "Go/Java", "Manages order lifecycle")
    ContainerDb(order_db, "Order DB", "PostgreSQL", "Source of truth for orders")
    
    Container(msg_broker, "Message Broker", "Kafka / RabbitMQ", "Async Event Bus")
}

System_Ext(payment_gw, "Payment Gateway", "Stripe / PayPal")

Rel(customer, cdn, "Visits", "HTTPS")
Rel(cdn, lb, "Forwards dynamic requests", "HTTPS")
Rel(lb, api_gw, "Routes", "HTTPS")

Rel(api_gw, product_svc, "Reads Catalog")
Rel(product_svc, product_db, "Reads")

Rel(api_gw, cart_svc, "Manages Cart")
Rel(cart_svc, cart_cache, "Reads/Writes")

Rel(api_gw, checkout_svc, "Initiates Checkout")
Rel(checkout_svc, inventory_svc, "1. Request Reservation (Sync)")
Rel(inventory_svc, inventory_redis, "2. Atomic DECR (Sync)")
Rel(inventory_svc, inventory_db, "3. Persist Reservation (Sync)")

Rel(checkout_svc, payment_svc, "4. Process Payment (Sync)")
Rel(payment_svc, payment_gw, "5. API Call (Sync)")

Rel(payment_svc, msg_broker, "6. Publish PaymentSuccess Event (Async)")
Rel(msg_broker, order_svc, "7. Consume Event")
Rel(order_svc, order_db, "8. Create Order")
Rel(order_svc, msg_broker, "9. Publish OrderCreated Event")
```

## 3. Component Diagram: Inventory & Order Services
*A zoomed-in look at the critical internal workings of our Inventory and Order modules.*

```mermaid
C4Component
title Component Diagram - Inventory & Order Services

Container_Boundary(inv_bound, "Inventory / Reservation Service") {
    Component(inv_ctrl, "Reservation Controller", "REST/gRPC", "Entry point for reservation requests")
    Component(inv_validator, "Request & Idempotency Validator", "Middleware", "Filters duplicates")
    Component(redis_client, "Atomic Counter Client", "Redis Client", "Executes DECR for stock contention")
    Component(inv_repo, "Inventory Repository", "Data Access", "Persists reservation state to DB")
    
    Rel(inv_ctrl, inv_validator, "Validates")
    Rel(inv_validator, redis_client, "Attempts decrement")
    Rel(redis_client, inv_repo, "If success, persist reservation")
}

Container_Boundary(ord_bound, "Order Service") {
    Component(order_consumer, "Payment Event Consumer", "Kafka Listener", "Listens for successful payments")
    Component(order_mgr, "Order State Manager", "Business Logic", "Validates and transitions order states")
    Component(order_repo, "Order Repository", "Data Access", "Persists order")
    
    Rel(order_consumer, order_mgr, "Passes payment payload")
    Rel(order_mgr, order_repo, "Creates confirmed order")
}
```

## 4. Deployment Diagram
*Physical deployment strategy targeting the 10,000 req/sec spike.*

```mermaid
graph TD
    subgraph "Cloud Region (Multi-AZ)"
        CDN["CDN & WAF (Cloudflare/CloudFront) <br/> <i>Absorbs static load & prevents DDoS</i>"]
        ALB["Application Load Balancer"]
        
        subgraph "Auto-Scaling Kubernetes (EKS/AKS)"
            API_GW["API Gateway (Rate Limiting)"]
            
            subgraph "Stateless Microservices (Horizontal Scaling)"
                PROD_SVC["Product Service (Pods)"]
                CART_SVC["Cart Service (Pods)"]
                CHK_SVC["Checkout Service (Pods)"]
                PAY_SVC["Payment Service (Pods)"]
            end
            
            subgraph "Critical Stateful/Worker Services"
                INV_SVC["Inventory Service (Optimized for Throughput)"]
                ORD_SVC["Order Service (Async Workers)"]
            end
        end
        
        subgraph "Managed Data Tier"
            REDIS_CLUSTER["Redis ElastiCache Cluster (Primary + Replicas) <br/> <i>Handles DECR Contention</i>"]
            KAFKA_CLUSTER["Kafka / MSK Cluster <br/> <i>Event Streaming & Decoupling</i>"]
            RDS_CLUSTER["Aurora PostgreSQL (Primary + Read Replicas) <br/> <i>Persistent Truth</i>"]
        end
    end
    
    Internet(("10,000 Users/sec")) --> CDN
    CDN --> ALB
    ALB --> API_GW
    API_GW --> PROD_SVC
    API_GW --> CART_SVC
    API_GW --> CHK_SVC
    
    CHK_SVC --> INV_SVC
    CHK_SVC --> PAY_SVC
    
    INV_SVC -.->|Atomic DECR| REDIS_CLUSTER
    INV_SVC -.->|Persist| RDS_CLUSTER
    
    PAY_SVC -.->|Publish Event| KAFKA_CLUSTER
    ORD_SVC -.->|Consume Event| KAFKA_CLUSTER
    ORD_SVC -.->|Write Order| RDS_CLUSTER
```

---

## 5. Architectural Defense (Mandatory Jury Requirements)

### A. Communication Flow
* **Synchronous Flow (The Critical Path):** 
  * `Client → API Gateway → Checkout Service`: The user must wait for the checkout response.
  * `Checkout Service → Inventory Service`: Securing the item using the Redis `DECR` command **must** be strictly synchronous. If the counter drops below zero, we must instantly fail the request synchronously and alert the user they missed out.
  * `Checkout Service → Payment Gateway`: We must wait for authorization/capture synchronously before proceeding, as we cannot guarantee stock without guaranteed funds.
* **Asynchronous Flow (The Background Path):**
  * `Payment Service → Message Queue (Kafka) → Order Service`: Once payment is confirmed, creating the final Order record is decoupled asynchronously. This speeds up the user's response time and guarantees eventual consistency even if the Order Service is temporarily down.
  * `Order Service → Notification Service`: Sending the "Order Confirmed" email happens entirely asynchronously in the background.

### B. Bottleneck Analysis & Component Justification
1. **Bottleneck: Database Row Locking (Inventory Contention)**
   * *Why the component exists:* The **Redis Atomic Counter** cluster exists specifically to act as an in-memory buffer. 10,000 users will hit Redis simultaneously, but `DECR` will fast-fail 9,900 of them instantly. Because of this component, our PostgreSQL database is completely shielded from connection exhaustion and only has to process the 100 winning transactions.
2. **Bottleneck: Payment Gateway Rate Limits & Latency**
   * *Why the component exists:* External APIs are slow and prone to timeouts during high traffic. The **Message Broker (Kafka)** and **Payment Service Circuit Breakers** exist so that if the Payment Gateway becomes a bottleneck, we do not hold open hundreds of database transactions. We can safely timeout, release the inventory, and allow another user to buy.
3. **Bottleneck: Ingress Connection Limits**
   * *Why the component exists:* 10,000 req/sec will easily crash a single server. The **API Gateway & Load Balancer** combination provides aggressive rate limiting and routing, while **Stateless Auto-Scaling Groups (Kubernetes Pods)** allow us to spin up hundreds of Checkout Service instances on demand to handle the massive ingress connection spike before it ever reaches the data tier.
