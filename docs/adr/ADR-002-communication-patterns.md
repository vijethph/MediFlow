# ADR-002: Synchronous vs Asynchronous Communication Patterns

## Status

Accepted

## Context

Our Healthcare Patient Management System requires inter-service communication. We need to decide when to use synchronous communication (REST APIs) versus asynchronous communication (message queues with RabbitMQ).

### Key Scenarios:

1. Appointment Service needs to verify patient exists before booking
2. Billing Service needs to create invoices after appointments
3. Notification system needs to send appointment reminders
4. Services need to respond to user requests in real-time

## Decision

We will use a **hybrid approach** combining both synchronous and asynchronous communication:

### Synchronous Communication (REST APIs)

**Use for**:

- User-facing queries requiring immediate response
- Data validation before operations
- Real-time data retrieval

**Examples**:

- Appointment Service → Patient Service: Verify patient exists
- Frontend → Any Service: Get patient details, list appointments
- Billing Service → Appointment Service: Get appointment details

### Asynchronous Communication (RabbitMQ)

**Use for**:

- Event notifications
- Background processing
- Non-blocking operations
- Decoupled workflows

**Examples**:

- Appointment created → Notify Billing Service to create invoice
- Appointment scheduled → Send notification to patient
- Payment received → Update appointment status
- Prescription created → Notify patient

## Consequences

### Positive:

✅ **User Experience**: Synchronous APIs provide immediate feedback for user-facing operations.

✅ **System Resilience**: Asynchronous messaging allows services to be temporarily unavailable without losing events.

✅ **Scalability**: Message queues can buffer high volumes of events during traffic spikes.

✅ **Decoupling**: Asynchronous communication reduces tight coupling between services.

✅ **Flexibility**: Can add new services that consume existing events without modifying publishers.

✅ **Fault Tolerance**: RabbitMQ provides message persistence and retry mechanisms.

### Negative:

❌ **Complexity**: Maintaining two communication patterns increases system complexity.

❌ **Eventual Consistency**: Asynchronous operations mean data is eventually consistent, not immediately.

❌ **Debugging Difficulty**: Tracing asynchronous flows is more challenging than synchronous calls.

❌ **Operational Overhead**: Must monitor and maintain RabbitMQ in addition to REST APIs.

❌ **Learning Curve**: Team needs to understand both synchronous and asynchronous patterns.

❌ **Testing Complexity**: Testing asynchronous flows requires additional infrastructure.

## Implementation Guidelines

### Synchronous REST API Guidelines:

```python
# Example: Appointment Service verifying patient
async def create_appointment(appointment: AppointmentCreate):
    # Synchronous call to Patient Service
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PATIENT_SERVICE_URL}/patients/{appointment.patient_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Patient not found")

    # Create appointment locally
    return await appointment_repository.create(appointment)
```

**Best Practices**:

- Use circuit breakers (Tenacity) for fault tolerance
- Implement timeouts (default 30s)
- Return clear error messages
- Use async HTTP clients (httpx)

### Asynchronous RabbitMQ Guidelines:

```python
# Example: Publishing appointment created event
def publish_appointment_event(appointment: Appointment):
    message = {
        "event_type": "appointment.created",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "appointment_id": appointment.id,
            "patient_id": appointment.patient_id,
            "appointment_date": appointment.date.isoformat()
        }
    }

    channel.basic_publish(
        exchange='healthcare.events',
        routing_key='appointment.created',
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Persistent message
            content_type='application/json'
        )
    )
```

**Best Practices**:

- Use durable queues for important events
- Implement idempotent consumers (handle duplicate messages)
- Add retry logic with exponential backoff (Tenacity)
- Use dead letter queues for failed messages
- Include correlation IDs for tracing

## Event Schema

### Standard Event Format:

```json
{
  "event_id": "uuid",
  "event_type": "service.action",
  "timestamp": "ISO-8601 datetime",
  "source_service": "service-name",
  "correlation_id": "uuid",
  "data": {
    "entity_id": "...",
    "entity_type": "...",
    "changes": {}
  }
}
```

### Event Types:

- `patient.created`
- `patient.updated`
- `appointment.created`
- `appointment.updated`
- `appointment.cancelled`
- `appointment.completed`
- `prescription.created`
- `invoice.created`
- `payment.received`

## Trade-Off Analysis

| Aspect              | Synchronous REST                    | Asynchronous RabbitMQ           |
| ------------------- | ----------------------------------- | ------------------------------- |
| **Latency**         | Lower (immediate response)          | Higher (eventual processing)    |
| **Coupling**        | Tighter (service must be available) | Looser (decoupled services)     |
| **Consistency**     | Strong consistency possible         | Eventual consistency            |
| **Fault Tolerance** | Fails immediately if service down   | Resilient with queue buffering  |
| **Complexity**      | Simpler to implement and debug      | More complex infrastructure     |
| **Use Case**        | User-facing operations              | Background tasks, notifications |
| **Scalability**     | Limited by service capacity         | Highly scalable with queues     |
| **Debugging**       | Easy to trace with request IDs      | Harder to trace across events   |

## When to Use Which Pattern

### Use Synchronous REST When:

- User is waiting for a response
- Need immediate validation
- Query operation with no side effects
- Strong consistency required
- Simple request-response flow

### Use Asynchronous RabbitMQ When:

- Operation can happen in background
- Multiple services need to react to same event
- Service can be temporarily unavailable
- High volume of events to process
- Eventual consistency is acceptable
- Need to decouple services

## Alternatives Considered

### Alternative 1: Pure Synchronous (REST Only)

**Rejected because**:

- Creates tight coupling between services
- Reduces fault tolerance
- Cannot handle high event volumes
- Blocking operations impact user experience

### Alternative 2: Pure Asynchronous (Event-Driven Only)

**Rejected because**:

- Poor user experience for real-time queries
- Difficult to implement validation flows
- Eventual consistency everywhere is too complex
- 3-week timeline insufficient for full event sourcing

### Alternative 3: gRPC for Synchronous Communication

**Deferred because**:

- FastAPI has excellent REST support built-in
- REST is easier for debugging and testing
- Can consider gRPC as future optimization
- Learning curve for team

## References

- [Event-Driven Microservices with Python](https://www.linkedin.com/pulse/event-driven-microservices-python-building-scalable-systems-deger-kttyc)
- [RabbitMQ with FastAPI Tutorial](https://python.plainenglish.io/building-event-driven-architectures-fastapi-message-queues-rabbitmq-kafka-redis-streams-2ba82926a120)
- [Microservices Communication Patterns](https://microservices.io/patterns/communication-style/messaging.html)

## Monitoring and Observability

- Track REST API response times and error rates via Prometheus
- Monitor RabbitMQ queue depths and message rates
- Implement correlation IDs for tracing across sync/async boundaries
- Set up alerts for high queue depths or message processing delays

---

**Decision Date**: 2024-11-29
**Participants**: All 4 team members
**Reviewer**: Course Instructor (to be reviewed)
