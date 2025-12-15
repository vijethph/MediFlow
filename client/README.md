# Healthcare Patient Management System - Client Application

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Backend Changes](#backend-changes)
4. [Frontend Implementation](#frontend-implementation)
5. [API Integration](#api-integration)
6. [Features](#features)
7. [Setup & Installation](#setup--installation)
8. [Configuration](#configuration)
9. [Development Guide](#development-guide)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This is a **production-ready healthcare patient management system** built with:

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS v4, React Query
- **Backend**: FastAPI microservices (Patient, Appointment, Prescription, Billing)
- **API Gateway**: Kong Gateway for centralized routing
- **Authentication**: JWT-based authentication with password hashing
- **Standards**: FHIR R4 compatible schemas

The system provides a complete patient portal where users can:
- Register and login with secure password authentication
- Manage appointments (book, reschedule, cancel)
- View and create prescriptions
- Manage billing and invoices
- Update profile information

---

## Architecture

### System Architecture

```
┌─────────────────┐
│   Frontend      │  Next.js 14 (Port 3001)
│   (This Client) │  TypeScript + Tailwind CSS
└────────┬────────┘
         │
         │ HTTP/REST
         │
┌────────▼────────┐
│  Kong Gateway   │  Port 8000
│  (API Gateway)  │  JWT Authentication
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────────┐
    │         │          │              │
┌───▼───┐ ┌──▼───┐ ┌─────▼────┐ ┌──────▼─────┐
│Patient│ │Appt  │ │Prescription│ │  Billing   │
│Service│ │Service│ │  Service   │ │  Service   │
│ :8001 │ │ :8002│ │   :8003    │ │   :8004    │
└───────┘ └──────┘ └───────────┘ └────────────┘
```

### Frontend Architecture

```
client/
├── app/                    # Next.js App Router pages
│   ├── dashboard/         # Dashboard with stats
│   ├── appointments/      # Appointment management
│   ├── prescriptions/     # Prescription management
│   ├── billing/           # Invoice and payment management
│   ├── profile/           # User profile and settings
│   ├── login/             # Authentication
│   └── register/          # User registration
├── components/            # React components
│   ├── layout/           # Header, Sidebar, AuthLayout
│   ├── providers/        # Context providers (Query, Auth, Notifications)
│   └── ui/               # Reusable UI components
├── lib/                   # Core libraries
│   ├── api/              # API client functions
│   ├── hooks/            # React Query hooks
│   └── validations/      # Zod validation schemas
└── public/               # Static assets
```

---

## Backend Changes

### Summary

**Philosophy**: Minimize backend changes, maximize frontend transformations for flexibility and maintainability.

### 1. Patient Service - Password Authentication

#### Files Modified:

**`patient_service/app/models.py`**
- Added `password_hash` column (nullable for backward compatibility)
```python
password_hash = Column(String(255), nullable=True)
```

**`patient_service/app/auth/password.py`** (NEW FILE)
- Password hashing utilities using bcrypt via `passlib`
- Functions: `hash_password()`, `verify_password()`

**`patient_service/app/crud.py`**
- Modified `create_patient()`: Hashes password before storing
- Added `change_patient_password()`: Verifies current password, hashes new password

**`patient_service/app/schemas.py`**
- Added `password` field to `PatientBase` (optional)
- Added `ChangePassword` schema for password change endpoint
- Made `password` optional in `PatientLogin` for backward compatibility

**`patient_service/app/routers/patients.py`**
- Modified `login_patient()`: Verifies password using `verify_password()`
- Added `POST /api/v1/patients/change-password` endpoint

#### Key Changes:

1. **Password Hashing**: All passwords are hashed using bcrypt before storage
2. **Password Verification**: Login verifies password against stored hash
3. **Password Change**: New endpoint allows authenticated users to change passwords
4. **Backward Compatibility**: Existing users without passwords can still login

#### Database Migration Required:

```sql
ALTER TABLE patients ADD COLUMN password_hash VARCHAR(255);
```

Or using Alembic:
```bash
cd patient_service
alembic revision --autogenerate -m "add_password_hash_to_patients"
alembic upgrade head
```

### 2. Appointment Service - Query Parameter Support

#### Files Modified:

**`appointment_service/app/routers/appointments.py`**
- Modified `list_appointments()` endpoint to accept optional `patient_id` query parameter
- If `patient_id` provided, filters appointments by patient
- Maintains backward compatibility with general listing

```python
@router.get("/", response_model=List[Appointment])
async def list_appointments(
    ...
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    ...
):
    if patient_id:
        appointments = await get_appointments_by_patient(...)
    else:
        appointments = await get_appointments(...)
```

### 3. No Other Backend Changes

All other schema transformations and data mapping are handled in the **frontend** to maintain backend stability and flexibility.

---

## Frontend Implementation

### Technology Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **State Management**: React Query (@tanstack/react-query)
- **HTTP Client**: Axios
- **Form Validation**: Zod + React Hook Form
- **Icons**: Lucide React
- **Design System**: Custom design tokens (Blue theme)

### Key Features Implemented

#### 1. Authentication System

**Files**: `lib/api/auth.ts`, `app/login/page.tsx`, `app/register/page.tsx`

- JWT token management (localStorage)
- Automatic token expiration checking
- Password-based login and registration
- Session expiration handling
- Protected routes with `AuthGuard`

**Features**:
- Password strength validation (min 8 chars, uppercase, lowercase, number, special char)
- Password confirmation matching
- Automatic redirect on login/logout
- Token refresh placeholder (for future implementation)

#### 2. Appointment Management

**Files**: `app/appointments/page.tsx`, `app/appointments/book/page.tsx`, `app/appointments/[id]/reschedule/page.tsx`

**Features**:
- List appointments with filtering and pagination
- Book new appointments (30 or 60 minute slots)
- Reschedule existing appointments
- Cancel appointments
- Status filtering (pending, booked, cancelled, etc.)
- Date range filtering
- Real-time appointment count on dashboard

**Schema Transformations** (in `lib/api/appointments.ts`):
- Frontend `start`/`end` → Backend `appointment_date`/`duration_minutes`
- Frontend `practitioner_name` → Backend `doctor_name`
- Backend `appointment_id` → Frontend `id`
- Handles FHIR R4 format (start/end) vs traditional format (appointment_date)

#### 3. Prescription Management

**Files**: `app/prescriptions/page.tsx`, `app/prescriptions/create/page.tsx`

**Features**:
- List prescriptions with pagination
- Create new prescriptions with multiple medications
- Dynamic medication fields (add/remove)
- Medication frequency mapping to backend enum
- Prescription refill requests
- Status filtering

**Schema Transformations** (in `lib/api/prescriptions.ts`):
- Maps frontend frequency strings to backend `MedicationFrequency` enum
- Handles MongoDB `_id` field transformation
- Transforms response format for UI display

#### 4. Billing & Invoices

**Files**: `app/billing/page.tsx`, `app/billing/invoice/create/page.tsx`, `app/billing/[id]/page.tsx`

**Features**:
- List invoices with pagination
- Generate new invoices with line items
- Dynamic line item fields
- Payment processing
- Outstanding balance calculation
- Invoice status tracking

**Schema Transformations** (in `lib/api/billing.ts`):
- Frontend number → Backend `Money` object (`{value, currency}`)
- Line items transformation with sequence, code, unit_price
- Payment amount transformation
- EUR currency support

#### 5. User Profile

**Files**: `app/profile/page.tsx`

**Features**:
- View and edit profile information
- Change password (with current password verification)
- Update allergies
- Notification preferences
- Section-based navigation

#### 6. Dashboard

**Files**: `app/dashboard/page.tsx`

**Features**:
- Upcoming appointments count (with date filtering)
- Active prescriptions count
- Outstanding balance
- Next appointment display
- Pending actions list
- Recent activity feed

**Fix Applied**: Dashboard now correctly counts appointments with status "proposed", "pending", or "booked" that are in the future.

#### 7. Form Validation

**Files**: `lib/validations/*.ts`

All forms use Zod schemas for validation:
- `auth.ts`: Login, registration, password change
- `appointments.ts`: Appointment booking with date validation
- `prescriptions.ts`: Prescription creation with medication validation
- `billing.ts`: Invoice and payment validation
- `profile.ts`: Profile update validation

#### 8. Notification System

**Files**: `components/ui/Notification.tsx`, `lib/hooks/useNotifications.ts`, `components/providers/NotificationProvider.tsx`

**Features**:
- Real-time toast notifications
- Success, error, info, warning types
- Auto-dismiss with configurable duration
- Global notification context

#### 9. UI Components

**Files**: `components/ui/*.tsx`

Reusable components:
- `Button`: Primary, secondary, outline, ghost variants
- `Card`: Container component
- `Input`: Form input with error display
- `Modal`: Pop-up dialogs
- `Pagination`: List pagination
- `StatusBadge`: Status indicators
- `FileUpload`: File upload with validation
- `LoadingSpinner`: Loading states
- `ErrorMessage`: Error display

#### 10. API Client

**Files**: `lib/api/client.ts`

**Features**:
- Centralized Axios instance
- JWT token injection in headers
- Automatic 401 handling (redirects to login)
- Token expiration detection
- Error handling and transformation
- 307 redirect handling
- 502/503 service unavailable handling

---

## API Integration

### API Endpoints Used

#### Authentication
- `POST /api/v1/patients/register` - User registration
- `POST /api/v1/patients/login` - User login
- `POST /api/v1/patients/change-password` - Change password

#### Patient Data
- `GET /api/v1/patients/{patient_id}` - Get patient details
- `PUT /api/v1/patients/{patient_id}` - Update patient

#### Appointments
- `GET /api/v1/appointments/` - List appointments (with `patient_id` query param)
- `GET /api/v1/appointments/{appointment_id}` - Get appointment
- `POST /api/v1/appointments` - Create appointment
- `PUT /api/v1/appointments/{appointment_id}` - Update appointment
- `POST /api/v1/appointments/{appointment_id}/cancel` - Cancel appointment

#### Prescriptions
- `GET /api/v1/prescriptions` - List prescriptions (with `patient_id` query param)
- `GET /api/v1/prescriptions/{prescription_id}` - Get prescription
- `POST /api/v1/prescriptions` - Create prescription
- `PUT /api/v1/prescriptions/{prescription_id}` - Update prescription

#### Billing
- `GET /api/v1/invoices` - List invoices (with `patient_id` query param)
- `GET /api/v1/invoices/{invoice_id}` - Get invoice
- `POST /api/v1/invoices` - Create invoice
- `POST /api/v1/payments` - Create payment
- `GET /api/v1/payments/{payment_id}` - Get payment

### Data Transformations

All transformations are handled in the frontend API layer (`lib/api/*.ts`) to maintain backend compatibility:

1. **Appointments**: `start`/`end` ↔ `appointment_date`/`duration_minutes`
2. **Prescriptions**: Frequency string ↔ Enum mapping
3. **Billing**: Number ↔ Money object transformation
4. **Responses**: Backend IDs (`appointment_id`, `_id`) → Frontend `id`

---

## Features

### ✅ Implemented Features

1. **User Authentication**
   - Secure password-based login
   - User registration with validation
   - Password change functionality
   - JWT token management
   - Session expiration handling

2. **Appointment Management**
   - Book appointments (30/60 min slots)
   - Reschedule appointments
   - Cancel appointments
   - View appointment history
   - Filter by status and date
   - Pagination support

3. **Prescription Management**
   - View prescriptions
   - Create prescriptions with multiple medications
   - Request prescription refills
   - Filter by status
   - Pagination support

4. **Billing Management**
   - View invoices
   - Generate invoices with line items
   - Process payments
   - Track outstanding balance
   - Filter by status
   - Pagination support

5. **User Profile**
   - View and edit profile
   - Change password
   - Update allergies
   - Notification preferences

6. **Dashboard**
   - Upcoming appointments count
   - Active prescriptions count
   - Outstanding balance
   - Next appointment display
   - Pending actions
   - Recent activity

7. **UI/UX Features**
   - Responsive design (mobile-first)
   - Real-time notifications
   - Form validation with error messages
   - Loading states
   - Error handling
   - Accessibility (WCAG 2.1 AA)
   - Blue theme with design tokens

---

## Setup & Installation

### Prerequisites

- Node.js 18+ and npm
- Backend services running (via Docker Compose)
- Kong API Gateway running on port 8000

### Installation Steps

1. **Install Dependencies**
```bash
cd client
npm install
```

2. **Environment Configuration**
Create `.env.local` file:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. **Start Development Server**
```bash
npm run dev
```

The application will run on `http://localhost:3001`

4. **Build for Production**
```bash
npm run build
npm start
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API Gateway URL | `http://localhost:8000` |

### Design Tokens

Custom CSS variables in `app/globals.css`:
- Primary color: `#2563EB` (Blue)
- Primary light: `#DBEAFE`
- Primary dark: `#1E40AF`
- Success, warning, danger colors
- Typography scales
- Spacing system

---

## Development Guide

### Project Structure

```
client/
├── app/                      # Next.js pages (App Router)
│   ├── (auth)/              # Auth routes (login, register)
│   ├── (dashboard)/         # Protected routes
│   │   ├── dashboard/
│   │   ├── appointments/
│   │   ├── prescriptions/
│   │   ├── billing/
│   │   └── profile/
│   └── layout.tsx           # Root layout
├── components/              # React components
│   ├── layout/             # Layout components
│   ├── providers/          # Context providers
│   └── ui/                 # UI components
├── lib/                    # Core libraries
│   ├── api/               # API clients
│   ├── hooks/             # Custom hooks
│   └── validations/        # Zod schemas
└── public/                # Static assets
```

### Adding a New Feature

1. **Create API function** in `lib/api/`
2. **Create React Query hook** in `lib/hooks/`
3. **Create validation schema** in `lib/validations/`
4. **Create page** in `app/`
5. **Add route** to sidebar navigation

### Code Style

- TypeScript strict mode
- ESLint for linting
- Prettier for formatting (recommended)
- Functional components with hooks
- Custom hooks for reusable logic

---

## Troubleshooting

### Common Issues

#### 1. "Cannot connect to API server"
- **Solution**: Ensure backend services and Kong Gateway are running
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Verify Kong Gateway is accessible at `http://localhost:8000`

#### 2. "Invalid token or expired token"
- **Solution**: Log out and log back in
- Check JWT token expiration
- Verify `JWT_SECRET` matches across all services

#### 3. "Failed to load appointments"
- **Solution**: Check appointment service is running
- Verify `patient_id` is being sent in query parameters
- Check appointment service logs

#### 4. Build Errors
- **Solution**: Clear `.next` folder and rebuild
- Run `npm install` to ensure dependencies are up to date
- Check TypeScript errors in terminal

#### 5. Hydration Errors
- **Solution**: Ensure all date formatting uses stable formats
- Avoid `Math.random()` in render, use `React.useId()` instead
- Move `localStorage` access to `useEffect`

---

## API Documentation

### Authentication Flow

1. User submits login form with email and password
2. Frontend sends `POST /api/v1/patients/login` with credentials
3. Backend verifies password and returns JWT token
4. Frontend stores token in `localStorage`
5. All subsequent requests include token in `Authorization` header
6. On 401 response, frontend redirects to login

### Data Flow

1. **User Action** → React component
2. **Form Validation** → Zod schema
3. **API Call** → React Query hook
4. **Data Transformation** → API client function
5. **HTTP Request** → Axios with JWT token
6. **Backend Processing** → Microservice
7. **Response Transformation** → API client function
8. **State Update** → React Query cache
9. **UI Update** → React component re-render

---

## Security Considerations

1. **Password Hashing**: All passwords are hashed in backend using bcrypt
2. **JWT Tokens**: Stored in `localStorage` (consider httpOnly cookies for production)
3. **Token Expiration**: Tokens expire after configured time (default: 60 minutes)
4. **HTTPS**: Use HTTPS in production
5. **CORS**: Configured in Kong Gateway
6. **Input Validation**: All inputs validated with Zod schemas
7. **XSS Protection**: React automatically escapes user input

---

## Performance Optimizations

1. **React Query**: Automatic caching and background refetching
2. **Code Splitting**: Next.js automatic code splitting
3. **Image Optimization**: Next.js Image component
4. **Lazy Loading**: Components loaded on demand
5. **Pagination**: Large lists paginated to reduce load

---

## Testing

### Manual Testing Checklist

- [ ] User registration with password
- [ ] User login with password
- [ ] Password change functionality
- [ ] Book new appointment
- [ ] Reschedule appointment
- [ ] Cancel appointment
- [ ] Create prescription
- [ ] Generate invoice
- [ ] Process payment
- [ ] Update profile
- [ ] Dashboard stats accuracy

---

## Future Enhancements

1. **Token Refresh**: Implement refresh token mechanism
2. **Offline Support**: Add service worker for offline functionality
3. **Real-time Updates**: WebSocket integration for live updates
4. **File Uploads**: Complete file upload implementation
5. **Advanced Search**: Full-text search across all resources
6. **Export Data**: PDF/CSV export functionality
7. **Multi-language**: i18n support
8. **Dark Mode**: Theme switching

---

## Support & Contact

For issues or questions:
1. Check this README
2. Review backend service logs
3. Check Kong Gateway logs
4. Review browser console for errors

---

## License

Private - Healthcare Patient Management System

---

## Changelog

### Version 1.0.0 (Current)

**Backend Changes**:
- ✅ Added password hashing to Patient Service
- ✅ Added password change endpoint
- ✅ Added patient_id query parameter to appointment list endpoint

**Frontend Changes**:
- ✅ Complete authentication system with password support
- ✅ Appointment management (book, reschedule, cancel)
- ✅ Prescription management (create, view, refill)
- ✅ Billing management (invoices, payments)
- ✅ User profile management
- ✅ Dashboard with real-time stats
- ✅ Form validation with Zod
- ✅ Real-time notifications
- ✅ Pagination for all lists
- ✅ Search and filtering
- ✅ Responsive design
- ✅ Accessibility (WCAG 2.1 AA)
- ✅ Blue theme implementation
- ✅ Fixed dashboard appointment count (includes "proposed" status)
- ✅ Fixed all endpoint schema transformations

---

**Last Updated**: December 2025
