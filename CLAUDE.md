# Maktab - Islamic School Management System

A Django-based SaaS platform for managing madrasas and Islamic educational institutions. Multi-tenant, role-based, optimized for Indian institutions.

> **This is a living document.** Update this file whenever you make core changes — new models, modified fee logic, new portals, changed auth flows, added commands, etc. Keep it concise but accurate so future sessions have correct context.

## Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_dev        # creates org + admin user + sample data
python manage.py runserver
# Login at /login/ — admin / admin
```

## Tech Stack

- **Backend:** Django 4.2, SQLite (WAL mode), custom auth backend
- **Frontend:** HTML templates, Bootstrap 5, Tailwind CSS, vanilla JS
- **Dependencies:** Pillow (images), hijridate (Islamic calendar), openpyxl (Excel I/O)

## Architecture

Single Django app (`management/`) with multi-tenant isolation via `Organization` model. All queries are scoped to the user's organization.

### Project Layout

```
Finetouch/          # Django project config (settings, urls, wsgi)
management/         # The app — all business logic lives here
  models.py         # 19 models (~1200 lines)
  views.py          # 116 view functions (~5000 lines)
  forms.py          # All Django forms
  urls.py           # 156 routes
  backends.py       # Custom auth: PhoneOrUsernameBackend
  signals.py        # Auto-create/cleanup parent accounts on student save/delete
  decorators.py     # Role-based access decorators
  context_processors.py
  utils.py          # Phone normalization
  templates/management/   # 75 HTML templates
  management/commands/    # setup_dev, create_parent_accounts
```

### Models (19 total)

**Core:**
- `Organization` — tenant boundary. All other models FK to this.
- `User` (custom AbstractUser) — roles: admin, manager, staff, parent. FK to Organization, O2O to Staff.

**Academic:**
- `Course` — name, code, fees, fee_period (monthly/quarterly/yearly)
- `Batch` — links to Course, has schedule (days, start/end time), M2M teachers, M2M students
- `Student` — enrollment, batches, discount_type/discount_value, is_orphan, opening_balance
- `Attendance` — student attendance per batch per day (Present/Absent/Late/Excused)
- `BehaviorNote` — categorized notes on students

**Staff & HR:**
- `Staff` — profile, salary, department, working hours
- `StaffAttendance` — daily attendance with hours
- `PunchRecord` — clock in/out timestamps
- `LeaveType`, `LeaveBalance`, `LeaveRequest` — leave management with approval workflow

**Finance:**
- `FeePayment` — student payments with receipt tracking, approval workflow (Approved/Pending/Rejected)
- `Expense` — institutional expenses by category
- `Payroll`, `PayrollComponent`, `SalaryComponent` — staff compensation

**Other:**
- `Event` — calendar events (holiday, exam, meeting, fee_deadline)
- `AdmissionApplication` — public admission form with accept/reject workflow

### Fee System

Fees flow from Course -> Batch -> Student. A student's effective fee is the sum of fees from all enrolled batches, minus any discount.

**Discount mechanisms (checked in this order):**
1. `is_orphan = True` -> fee is 0 (complete waiver)
2. `discount_type = 'percentage'` + `discount_value` -> percentage off total
3. `discount_type = 'fixed'` + `discount_value` -> flat amount off total

**Key methods on Student:**
- `get_effective_fee()` — total fee after discounts (single source of truth)
- `get_total_paid()` — sum of Approved payments only
- `get_pending_fees()` — effective_fee + opening_balance - total_paid

**Excel import/export:** Supports a `Discount` column (fixed amount only, no percentage via Excel).

### Authentication & Authorization

**Custom auth backend** (`PhoneOrUsernameBackend`) supports three login flows:
- Staff: staff_id + phone (as password)
- Parent: phone + password (auto-created accounts)
- Admin/Manager: username + password

**Decorators** (in `decorators.py`):
- `@admin_required`, `@manager_or_admin_required`, `@parent_required`
- `@internal_user_required` (blocks parents from admin views)
- `@staff_role_required` (staff with linked profile)
- `@role_required(*roles)` (generic)

### Signals

Student save/delete triggers auto-management of parent User accounts:
- On student create/update: creates a parent User from the student's phone
- On student delete: deactivates parent User if no students remain with that phone

### Portals

- **Admin/Manager dashboard** (`/dashboard/`) — full CRUD for everything
- **Staff self-service** (`/my/`) — punch in/out, attendance, salary, leave requests
- **Parent portal** (`/parent/`) — children's details, fee history, UPI payment

### Management Commands

- `python manage.py setup_dev` — creates dev org, admin user, sample data (idempotent)
- `python manage.py setup_dev --no-sample-data` — org + admin only
- `python manage.py create_parent_accounts` — backfill parent accounts for existing students

## Conventions

- Auto-generated IDs use prefix + zero-padded number: `STU0001`, `STF0001`, `CRS0001`, `BTH0001`, `RCP0001`
- All unique constraints are scoped per organization
- Migrations are gitignored (local only)
- Database file (`db.sqlite3`) is gitignored
- Templates use `base_tailwind.html` as the dashboard layout, `base.html` for auth pages

## Testing

```bash
python manage.py test management
```

Tests cover the fee discount system: effective fee calculation, pending fees, payment status filtering, orphan waivers, and opening balances.
