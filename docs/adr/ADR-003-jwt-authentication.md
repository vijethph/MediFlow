# ADR-003: JWT Authentication Strategy

## Status

Accepted

## Context

Our Healthcare Patient Management System requires secure authentication and authorization across multiple microservices. We need a mechanism that:

- Securely identifies users across services
- Supports different user roles (patients, doctors, admins)
- Minimizes inter-service authentication calls
- Complies with HIPAA security requirements
- Is stateless and scalable

## Decision

We will use **JSON Web Tokens (JWT)** for authentication and authorization with the following architecture:

### Authentication Flow:

1. **Centralized Authentication**: Patient Service acts as the authentication service
2. **JWT Generation**: Upon successful login, generate JWT with user claims
3. **Token Distribution**: Client includes JWT in Authorization header for all requests
4. **Gateway Validation**: Kong API Gateway validates JWT for all incoming requests
5. **Service Trust**: Internal services trust tokens validated by the gateway

### Token Structure:

```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "patient|doctor|admin",
  "patient_id": "P123456",
  "exp": 1234567890,
  "iat": 1234567890,
  "iss": "healthcare-system"
}
```

### Implementation:

- **Algorithm**: HS256 (HMAC with SHA-256)
- **Expiration**: 24 hours for regular tokens
- **Refresh Tokens**: 7 days (stored securely, can be revoked)
- **Secret Management**: Shared secret stored in environment variables

## Consequences

### Positive:

✅ **Stateless**: No need for session storage, enabling horizontal scaling.

✅ **Single Sign-On**: Users authenticate once and can access all services.

✅ **Decentralized Authorization**: Each service can independently verify tokens and make authorization decisions.

✅ **Performance**: No need to call authentication service for every request.

✅ **Cross-Service Security**: Services can trust tokens validated at the API Gateway.

✅ **Role-Based Access Control**: JWT claims contain user roles for authorization.

✅ **Audit Trail**: Token claims provide user context for logging.

### Negative:

❌ **Token Revocation Complexity**: Cannot immediately revoke tokens; must wait for expiration.

❌ **Token Size**: JWTs are larger than session IDs, increasing bandwidth usage.

❌ **Secret Management**: Shared secret must be securely distributed to all services.

❌ **Token Theft Risk**: If token is stolen, attacker has access until expiration.

❌ **Clock Synchronization**: Services need synchronized clocks for expiration validation.

❌ **Cannot Update Claims**: Once issued, token claims cannot be updated; user must re-authenticate.

## Implementation Details

### Token Generation (Patient Service):

```python
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

def create_access_token(user_id: str, email: str, role: str) -> str:
    """Generate JWT access token."""
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expiration,
        "iat": datetime.utcnow(),
        "iss": "healthcare-system"
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def verify_token(token: str) -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
```

### Token Validation Middleware:

```python
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token in request."""
    token = credentials.credentials
    payload = verify_token(token)
    return payload

# Usage in endpoints
@router.get("/patients/{patient_id}", dependencies=[Depends(verify_jwt)])
async def get_patient(patient_id: str):
    ...
```

### Role-Based Authorization:

```python
from enum import Enum

class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"

def require_role(required_role: UserRole):
    """Decorator to require specific role."""
    def role_checker(current_user: dict = Depends(verify_jwt)):
        if current_user.get("role") != required_role.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker

# Usage
@router.delete("/patients/{patient_id}")
async def delete_patient(
    patient_id: str,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    ...
```

## Security Considerations

### HIPAA Compliance:

- **Encryption in Transit**: All JWT tokens transmitted over HTTPS/TLS
- **Access Control**: Role-based authorization for PHI access
- **Audit Logging**: Log all token validations and authorization decisions
- **Token Expiration**: Short-lived tokens reduce risk of theft
- **Refresh Tokens**: Longer-lived refresh tokens stored securely (optional enhancement)

### Best Practices:

1. **HTTPS Only**: Never transmit tokens over unencrypted connections
2. **Strong Secrets**: Use cryptographically secure random secrets (>256 bits)
3. **Token Rotation**: Implement refresh token rotation
4. **XSS Protection**: Store tokens securely on client (httpOnly cookies or secure storage)
5. **Rate Limiting**: Prevent brute force attacks on authentication endpoint
6. **Logging**: Audit all authentication attempts and authorization decisions

## Token Revocation Strategy

Since JWTs are stateless, we implement a lightweight revocation strategy:

### Option 1: Short Expiration (Chosen for MVP)

- Keep token expiration short (24 hours)
- Force re-authentication for sensitive operations
- Accept slight delay in access revocation

### Option 2: Token Blacklist (Future Enhancement)

- Maintain Redis cache of revoked tokens
- Check blacklist before accepting token
- Adds slight latency but enables immediate revocation

### Option 3: Refresh Token Rotation (Future Enhancement)

- Issue short-lived access tokens (15 min)
- Use refresh tokens to obtain new access tokens
- Revoke refresh tokens in database

## Kong API Gateway Configuration

```bash
# Configure JWT plugin in Kong
curl -X POST http://localhost:8001/services/patient-service/plugins \
  --data "name=jwt" \
  --data "config.secret_is_base64=false" \
  --data "config.key_claim_name=iss" \
  --data "config.claims_to_verify=exp"
```

## Trade-Off Analysis

| Aspect                  | JWT                      | Session-Based          | OAuth2    |
| ----------------------- | ------------------------ | ---------------------- | --------- |
| **Scalability**         | High (stateless)         | Low (server state)     | High      |
| **Complexity**          | Medium                   | Low                    | High      |
| **Revocation**          | Difficult                | Easy                   | Easy      |
| **Performance**         | Fast (no DB lookup)      | Slower (session store) | Slower    |
| **Security**            | Good with best practices | Good                   | Excellent |
| **Implementation Time** | 2-3 days                 | 1-2 days               | 5-7 days  |
| **Microservices Fit**   | Excellent                | Poor                   | Excellent |

## Alternatives Considered

### Alternative 1: Session-Based Authentication

**Rejected because**:

- Requires shared session storage (Redis) across services
- Creates stateful architecture
- Doesn't scale well with microservices
- Adds latency for session lookups

### Alternative 2: OAuth2 with External Provider

**Deferred because**:

- Too complex for 3-week timeline
- Requires external service integration
- Overkill for current requirements
- Can be added as future enhancement

### Alternative 3: API Keys

**Rejected because**:

- No user context or roles
- Difficult to manage and rotate
- No standard expiration mechanism
- Poor fit for patient-facing application

## Testing Strategy

```python
# Example test
def test_jwt_authentication():
    # Create valid token
    token = create_access_token("user123", "test@example.com", "patient")

    # Make authenticated request
    response = client.get(
        "/api/v1/patients/P123",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

def test_expired_token():
    # Create expired token
    token = create_expired_token()

    # Should fail
    response = client.get(
        "/api/v1/patients/P123",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
```

## References

- [FastAPI JWT Authentication Tutorial](https://testdriven.io/blog/fastapi-jwt-auth/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [OWASP JWT Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [HIPAA Security Rule - Access Controls](https://www.hhs.gov/hipaa/for-professionals/security/index.html)

## Monitoring

- Track authentication success/failure rates
- Monitor token validation errors
- Alert on unusual authentication patterns
- Log authorization decisions for audit trail

---

**Decision Date**: 2024-11-29
**Participants**: All 4 team members
**Reviewer**: Course Instructor (to be reviewed)
