# ADR-001: Database Per Service Pattern

## Status

Accepted

## Context

In our Healthcare Patient Management System, we need to decide how to manage data across our 4 microservices (Patient, Appointment, Prescription, and Billing). The key question is whether to use a shared database or have each service maintain its own database.

### Key Considerations:

- Independent service development and deployment
- Data consistency requirements
- Scalability needs
- Technology flexibility
- Operational complexity

## Decision

We will implement the **Database Per Service** pattern, where each microservice has its own dedicated database:

- **Patient Service**: PostgreSQL (relational data for demographics)
- **Appointment Service**: PostgreSQL (transactional integrity for scheduling)
- **Prescription Service**: MongoDB (flexible schema for clinical documents)
- **Billing Service**: PostgreSQL (financial transactions and reporting)

### Rationale:

1. **Service Independence**: Each service can be developed, deployed, and scaled independently without affecting others.

2. **Technology Flexibility**: We can choose the most appropriate database technology for each service's specific needs (e.g., MongoDB for Prescription Service's flexible document storage).

3. **Fault Isolation**: Database failures in one service don't cascade to other services.

4. **Team Autonomy**: Each team member can work on their service without database-level coordination.

5. **Scalability**: Services with higher load (e.g., Appointment Service) can scale their databases independently.

## Consequences

### Positive:

✅ **Independent Deployment**: Services can be deployed without coordinating database migrations across teams.

✅ **Technology Choice**: Each service uses the most appropriate database technology (PostgreSQL for structured data, MongoDB for flexible documents).

✅ **Fault Isolation**: A database failure in one service doesn't bring down the entire system.

✅ **Scalability**: Services can scale independently based on their specific load patterns.

✅ **Team Autonomy**: Each student can work independently without database conflicts.

✅ **Performance**: Optimized schemas for each service's specific query patterns.

### Negative:

❌ **Distributed Transactions**: Cannot use ACID transactions across services. Must implement eventual consistency patterns (Saga pattern).

❌ **Data Consistency**: Ensuring consistency across services is more complex. Example: When creating an appointment, we need to verify the patient exists in Patient Service.

❌ **Join Queries**: Cannot perform SQL joins across services. Must use API composition or CQRS pattern for complex queries.

❌ **Operational Overhead**: Managing multiple databases increases operational complexity (backups, monitoring, upgrades).

❌ **Data Duplication**: Some data may need to be replicated across services, leading to potential inconsistencies.

❌ **Testing Complexity**: Integration tests must set up multiple databases.

## Implementation Strategy

### Inter-Service Data Access:

1. **Synchronous Queries**: Services call each other's REST APIs to fetch data (e.g., Appointment Service validates patient via Patient Service API).

2. **Event-Driven Updates**: Services publish events via RabbitMQ when data changes, allowing other services to update their local copies if needed.

3. **Eventual Consistency**: Accept that data consistency across services may be eventual rather than immediate.

### Example Flow:

```
Appointment Service creates appointment:
1. Call Patient Service API to verify patient exists (synchronous)
2. Create appointment in local database
3. Publish "appointment.created" event to RabbitMQ (asynchronous)
4. Billing Service listens to event and creates invoice
```

## Alternatives Considered

### Alternative 1: Shared Database

**Rejected because**:

- Creates tight coupling between services
- Prevents independent deployment
- Single point of failure
- Reduces team autonomy
- Makes it difficult to scale services independently

### Alternative 2: CQRS with Event Sourcing

**Deferred because**:

- Too complex for a 3-week project timeline
- Steep learning curve for students
- Overkill for the current requirements
- Can be considered as a future enhancement

### Alternative 3: Database Per Team with Shared Schema

**Rejected because**:

- Doesn't provide true service independence
- Schema changes still require coordination
- Doesn't allow different database technologies per service

## References

- [Microservices Pattern: Database Per Service](https://microservices.io/patterns/data/database-per-service.html)
- [Building Python Microservices with FastAPI - Chapter on Data Management](https://github.com/PacktPublishing/Building-Python-Microservices-with-FastAPI)
- [Martin Fowler: Microservices and Data](https://martinfowler.com/articles/microservices.html#DecentralizedDataManagement)

## Notes

This decision aligns with our course requirements for demonstrating trade-off analysis and architectural decision-making in distributed systems. The challenges introduced (distributed transactions, eventual consistency) provide valuable learning opportunities for understanding microservices architecture.

---

**Decision Date**: 2024-11-29
**Participants**: All 4 team members
**Reviewer**: Course Instructor (to be reviewed)
