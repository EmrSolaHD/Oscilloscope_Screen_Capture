# Comprehensive Full-Stack Plan for Design-Job/Task Management Portal (Django)

This document unifies all earlier discussions into a **complete, end-to-end architectural plan** for a custom design-job/task portal.  It details the technology stack, project structure, data model, multi-step form logic, design-team specific fields, attachments, approval workflows, directory lookup for approvers, role-based access controls and deployment guidelines.  The system uses **Django** and **Django REST Framework (DRF)** for the backend, and a **React front-end** with a modern glass-morphism UI.  All features discussed in the conversation have been consolidated here.

## 1. Business Goals & Rationale

1. **Streamlined request submission** – Provide employees with a friendly web portal to create design requests (jobs/tasks) for different engineering disciplines (PCB, Drawing, Hardware, Firmware).  Forms must be **multi-step**, only show relevant fields and include mandatory checks.
2. **Dynamic custom fields** – Each design team requires unique supplemental fields (e.g., board size for PCB, MCU type for Firmware).  These should be stored as JSON, allowing modifications without database schema changes.
3. **Managed approvals** – Every design job/task can require approval.  Approvers should be chosen from Azure AD via a **People Picker**.  The system must have **default approver lists** and **default approval routes** per team/request type, but allow administrators/group leaders to override them.
4. **Attachments & metadata** – Requests need attachments for design files and supporting documents.  All attachments should be uploaded to a file store (SharePoint/OneDrive/Azure Blob) and tracked in the database.
5. **Role-based access control (RBAC)** – Distinguish between Admin, Group Leader and User.  Only certain roles can search the entire directory or change approval lists; normal users see pre-selected defaults.
6. **Audit and traceability** – Track all changes, from job status and approval decisions to modifications of approval routes/defaults.  Provide dashboards and history timelines.

## 2. Technology Stack & Tools

- **Backend**: Python 3.10+ with Django 4.x and Django REST Framework.  PostgreSQL for relational storage; JSONField to store dynamic metadata.  Use `django-auth-adfs` or `django-allauth` with MSAL for Azure AD SSO.  Celery + Redis for async tasks (optional for notifications).  Use `msgraph-core` for Graph API calls.
- **Frontend**: React (with Next.js or Vite) for a single-page application.  Use CSS modules or Tailwind for the glass-morphism aesthetic (frosted panels, gradients, dark/light mode).  Use context or Redux for state management.
- **File Storage**: Azure SharePoint/OneDrive via Microsoft Graph for attachments; fallback to local storage or Azure Blob in development.  Use Graph’s `driveItem` endpoints for upload and metadata retrieval.
- **SSO & Directory**: Azure AD (or Okta) integration.  Use Graph API to search users (`User.ReadBasic.All` or `People.Read`).  Use `django-auth-adfs` for authentication; store the AD object ID for each user.
- **Deployment**: Use Waitress or Gunicorn to serve Django, Nginx/Apache as reverse proxy.  The React app can be hosted statically (Netlify/Vercel) or via Nginx.  Use Docker Compose or ARM templates for infrastructure as code.  Set up CI/CD (GitHub Actions) for automated testing and deployment.

## 3. Project Structure

```
root/
├── manage.py
├── requirements.txt
├── .env.example
├── design_portal/        # Django project package
│   ├── __init__.py
│   ├── settings/
│   │   ├── base.py       # common settings
│   │   ├── dev.py        # dev overrides
│   │   └── prod.py       # production overrides
│   ├── urls.py           # root URLConf
│   └── asgi.py / wsgi.py
├── apps/                 # Django apps
│   ├── accounts/
│   │   ├── models.py
│   │   ├── admin.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── design_teams/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── jobs/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── approvals.py
│   ├── tasks/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── approvals/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── notifications/
│   │   ├── utils.py
│   │   ├── tasks.py
│   │   └── signals.py
│   └── ...
├── static/
├── media/
├── frontend/             # React project
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── context/
│   │   ├── services/
│   │   └── index.jsx
│   └── ...
└── docs/
    └── master_plan.md    # this document
```

### Explanation
- `design_portal/settings/base.py` defines common settings (installed apps, authentication backends, REST framework, Graph credentials).  `dev.py` overrides with debug settings; `prod.py` sets allowed hosts, static roots.
- `accounts` app handles user profiles, roles and group membership.  Integrate SSO via Azure AD.  Extend `AbstractUser` with fields such as `aad_object_id` and `role` (Admin/GroupLeader/User).
- `design_teams` app stores the names and JSON definitions for team-specific fields and default routes.  Example teams: PCB, Drawing, Hardware, Firmware.
- `jobs` and `tasks` apps hold the core models for requests and tasks, including dynamic metadata and relationships to design teams, approval routes and line-items.  They handle API endpoints for creating, updating and listing jobs/tasks.  `approvals.py` may handle approval logic.
- `approvals` app contains models for `ApprovalRoute`, `DefaultApprover` and `ApprovalInstance` (individual pending approvals).  Provide endpoints for admins to manage default routes and approvers.
- `notifications` app provides utilities for sending emails via Graph API and Celery tasks.  It also defines signals to trigger notifications when a job is submitted, approved or rejected.
- `frontend` is a separate React project.  It will access the Django API via Axios or fetch and handle authentication tokens.  The folder structure follows common React patterns.

## 4. Data Model (Django ORM)

### 4.1 Identity & Permissions

```python
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Extend Django user with AD object and role."""
    aad_object_id = models.CharField(max_length=64, unique=True)
    role = models.CharField(
        max_length=20,
        choices=[('ADMIN', 'Admin'), ('GROUP_LEADER', 'Group Leader'), ('USER', 'User')],
        default='USER',
    )
    # any additional fields (department, etc.) can be added here

class Group(models.Model):
    """Represents company departments or design teams."""
    name = models.CharField(max_length=100)
    aad_group_id = models.CharField(max_length=64, blank=True, null=True)

class UserGroupMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
```

### 4.2 Design Teams & Configurations

```python
class DesignTeam(models.Model):
    name = models.CharField(max_length=50)
    form_definition = models.JSONField()  # team-specific fields definition for dynamic form
    default_route = models.ForeignKey('ApprovalRoute', null=True, blank=True,
                                      on_delete=models.SET_NULL)
```

### 4.3 Jobs & Tasks

```python
import uuid

class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    request_type = models.CharField(max_length=30)
    priority = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    group = models.ForeignKey(Group, on_delete=models.PROTECT)
    design_team = models.ForeignKey(DesignTeam, on_delete=models.PROTECT)
    approval_route = models.ForeignKey('ApprovalRoute', null=True, blank=True,
                                       on_delete=models.SET_NULL)
    metadata = models.JSONField(default=dict)  # includes custom fields, approver IDs etc.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent_job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    due_date = models.DateField(null=True, blank=True)
    assignee = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    group = models.ForeignKey(Group, on_delete=models.PROTECT)
    design_team = models.ForeignKey(DesignTeam, on_delete=models.PROTECT)
    approval_route = models.ForeignKey('ApprovalRoute', null=True, blank=True,
                                       on_delete=models.SET_NULL)
    metadata = models.JSONField(default=dict)  # stores custom fields, approvers/watchers
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 4.4 Line Items & Attachments

```python
class JobLineItem(models.Model):
    job = models.ForeignKey(Job, related_name='line_items', on_delete=models.CASCADE)
    order_index = models.PositiveIntegerField()
    data = models.JSONField()  # store row values as JSON
    created_at = models.DateTimeField(auto_now_add=True)

class TaskLineItem(models.Model):
    task = models.ForeignKey(Task, related_name='line_items', on_delete=models.CASCADE)
    order_index = models.PositiveIntegerField()
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

class Attachment(models.Model):
    parent_job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.CASCADE)
    parent_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)  # path or SharePoint drive ID
    mime_type = models.CharField(max_length=100)
    size = models.BigIntegerField()
    version = models.IntegerField(default=1)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### 4.5 Approval & Configuration Tables

```python
class ApprovalRoute(models.Model):
    name = models.CharField(max_length=100)
    route = models.JSONField()  # list of steps with roles or user IDs

class DefaultApprover(models.Model):
    design_team = models.ForeignKey(DesignTeam, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=50)
    approver_ids = models.JSONField()  # list of AD object IDs

class FormDefinition(models.Model):
    request_type = models.CharField(max_length=50)
    definition = models.JSONField()  # base multi-step form structure
    permissions = models.JSONField(default=dict)  # which roles can view/edit each field

class ApprovalInstance(models.Model):
    """Tracks the progress of a job/task along its approval route."""
    parent_job = models.ForeignKey(Job, null=True, on_delete=models.CASCADE)
    parent_task = models.ForeignKey(Task, null=True, on_delete=models.CASCADE)
    route = models.ForeignKey(ApprovalRoute, on_delete=models.PROTECT)
    current_stage = models.PositiveIntegerField(default=0)  # index in route.route list
    status = models.CharField(max_length=20, default='PENDING')  # PENDING/APPROVED/REJECTED
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## 5. Multi-Step Form Logic

1. **Fetching form definitions** – On page load for a new job/task, the React app calls `GET /api/form-definitions/?request_type=JOB`.  The backend responds with a JSON object describing steps, each with fields and validation rules.  Distribution of these fields is stored in `FormDefinition.definition` and merged with the selected design team’s `DesignTeam.form_definition`.
2. **Navigation & state** – The multi-step form (FormWizard) stores the current step and data in React state.  Each step has a “Next” and “Back” button.  The “Next” button is disabled until required fields on that step are valid.
3. **Conditional display** – Field definitions may include `conditionalDisplay` expressions.  For example, show “MCU Type” only if design team is Firmware.  The FormWizard interprets these conditions using current state.
4. **Mandatory fields** – Use the HTML `required` attribute in input controls for client-side validation.  On submission, the backend re-checks required fields using Django validators.  If missing, return a 400 response.
5. **Editable tables** – For each line item step, include a table that uses `JobLineItem` or `TaskLineItem`.  Users can add rows and fill in columns defined by the step’s table schema (stored in the form definition).  Each row is validated before proceeding.
6. **Attachments & People Picker** – The attachments step allows multiple file uploads.  It also includes the People Picker for selecting approvers and watchers.  For standard users, the People Picker shows default approvers loaded from `DefaultApprover` for the selected team/request type.  Admins and group leaders get a search box that queries `GET /api/users/search?q=...`.
7. **Review & Submit** – The final step summarizes all collected data.  The “Submit” button sends the payload to `POST /api/jobs/` or `/api/tasks/`.  The backend creates a new job/task with a **system-generated ID (UUID)**, populates `metadata` with custom fields, and kicks off the approval process.

## 6. Directory Lookup & People Picker

1. **Backend endpoints**:
   - `GET /api/users/search?q=...` – Searches Azure AD via Graph for users whose name or email starts with the query.  Only accessible to Admin or Group Leader roles.  The view obtains a Graph token (via client credentials or delegated token) and calls `/v1.0/users?$filter=startswith(displayName,'q') or startswith(mail,'q')`.  It returns basic data (name, email, AD object ID).
   - `GET /api/default-approvers/?design_team_id=X&request_type=Y` – Returns default approver AD IDs for a given team and request type.  Accessible to all authenticated users.  The view uses `DefaultApprover` table and returns names/emails via Graph lookup.
2. **People Picker component**:
   - For regular users: loads the default approvers list and disables free-typing.  Users can select/deselect from the default list.  The selected AD object IDs are added to `metadata.approver_ids`.
   - For admins and group leaders: the People Picker includes a search box.  On each keystroke (with debounce), it calls `GET /api/users/search?q=...`.  Results show names and job titles.  Selected users appear as tags/pills.
3. **Validation & RBAC**: When the job is submitted, the backend checks whether the user’s role matches the approvers they selected.  If a standard user attempted to add an approver not in the default list, return 403 Forbidden.

## 7. Approval Workflow

1. **Default route & stage creation** – When a job is submitted, the backend determines which approval route applies.  Use the job’s `design_team` → `DesignTeam.default_route`.  Alternatively, if `approval_route` is explicit in the payload (from an admin), use that.
2. **Instantiate ApprovalInstance** – Create an `ApprovalInstance` record linking to the job/task and the selected route.  Set `current_stage=0` (pending the first step).
3. **Notify first approver** – Use the notifications app to send an email/Teams message to the first stage’s approver(s).  The message includes a link to the job and instructions to approve or reject.
4. **Approval actions** – Approvers log in and see a list of assignments (`/approvals/`).  They may view job details, attachments, comments and history.  When they click “Approve” or “Reject”, the system records the decision, advances `current_stage`, and notifies the next approver or the requester if final.
5. **Default vs custom routes** – In the creation form, show a checkbox labelled “Use default approval route”.  If checked, the route is determined automatically; if unchecked (admins only), the user may choose or construct a custom route by ordering selected approvers.  The selected route is saved in `approval_route` and used instead of `DesignTeam.default_route`.
6. **Audit log** – All approval actions are logged (approver, decision, timestamp, comments).  These logs are displayed alongside the job in a history section and can be exported.

## 8. Pages & UI Specifications

| Page/Route | Purpose | Key Features |
|-----------|---------|-------------|
| `/dashboard/` | Overview showing active jobs/tasks, metrics (by status, priority, design team) | Widgets and charts; filter by group, design team, date range.  Provide notifications feed. |
| `/jobs/new/` | Multi-step form for new job requests | Steps: (1) Basic details & design team; (2) Stakeholders & Approvals (People Picker, route selection); (3) Custom team fields; (4) Attachments & watchers; (5) Line items table; (6) Review and Submit.  Use FormWizard with progress indicator. |
| `/tasks/new/` | Multi-step form for new tasks | Similar to jobs but may omit design-team selection if tied to a parent job. |
| `/jobs/{id}/` | View/edit a job | Display all fields, attachments, line items, current approval stage and history.  Allow editing of non-restricted fields.  Show People Picker for watchers (read-only if not authorized). |
| `/tasks/{id}/` | View/edit a task | Same pattern as job detail.  Include subtask creation. |
| `/approvals/` | Approver’s queue | List jobs/tasks awaiting the current user’s approval.  Filter by urgency, design team.  Each entry shows current stage, due date. |
| `/admin/` | Administrative console | Manage users/roles, design teams, approval routes and default approvers.  Provide UI to define multi-step form definitions and team-specific fields. |
| `/management/` | Group leader triage | Show jobs/tasks awaiting assignment or needing triage.  Assign tasks, set priorities, and balance workload. |
| `/settings/` | User preferences | Allow users to set default filters (e.g. default design team, view preferences). |

### Key UI components

- **Layout** – Header with title and user account; collapsible side navigation; dark/light mode toggle.  Footer with copyright and version.
- **FormWizard** – Manages step logic and state; integrates field validation and conditional display; shows progress bar.
- **FieldRenderer** – Renders dynamic fields based on field definitions (text, number, select, date, checkboxes, file upload, editable table).  Applies `required`, `pattern`, `min/max` constraints.
- **EditableTable** – Allows row-level CRUD operations; column definitions come from the form definition.  Stores rows in state and posts them to the backend on submission.
- **PeoplePicker** – As described above; uses Graph search for Admin/Group Leader roles; uses default lists for Users.
- **AttachmentUploader** – Drag-and-drop file upload with preview; calls backend to get upload URLs; updates attachments list in state.
- **Chart Widgets** – On dashboard: bar chart/pie chart summarizing jobs by status or tasks by team; support for time-series.  Use Chart.js or ECharts.

## 9. Starting the Project

### 9.1 Backend Setup

1. **Create project & virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install django djangorestframework psycopg2-binary django-auth-adfs
   django-admin startproject design_portal
   cd design_portal
   python manage.py startapp accounts
   python manage.py startapp design_teams
   python manage.py startapp jobs
   python manage.py startapp tasks
   python manage.py startapp approvals
   python manage.py startapp notifications
   ```
2. **Configure settings**: In `design_portal/settings/base.py`, set up database connection (PostgreSQL), installed apps (accounts, design_teams, jobs, tasks, approvals, notifications, rest_framework, auth_adfs).  Configure ADFS/Graph integration keys via environment variables loaded from `.env`.
3. **Define models**: Copy the model snippets (User, Group, Job, Task, etc.) into respective `models.py` files.  Run `python manage.py makemigrations` and `python manage.py migrate` to create tables.
4. **Create serializers and viewsets**: Use DRF’s `ModelSerializer` for each model.  Create viewsets (e.g. `JobViewSet`, `TaskViewSet`) that support list/create/retrieve/update.  Write custom actions for `approve` endpoints.
5. **Define API routes**: In `design_portal/urls.py`, register routers for each viewset.  Add extra URLs for search (`/api/users/search`) and default approvers.  Use permission classes to control access.
6. **Implement Graph integration**: Write helper functions in `notifications/utils.py` (or separate module) to acquire Graph tokens and call the People API.  Use them in the search and default endpoints.  Ensure rate limiting.
7. **Implement approval logic**: Create an `ApprovalService` or functions in `approvals/views.py` to handle route instantiation, stage progression, and notifications.  Use signals to trigger notifications when an approval decision is made.
8. **Set up authentication**: Configure `django-auth-adfs` or `django-allauth` in settings.  Provide Azure AD client ID, tenant ID, client secret and authority.  Map `aad_object_id` and group claims to roles via a custom authentication backend or middleware.
9. **Testing**: Write unit tests for models, views, and helpers.  Use DRF’s `APITestCase` to verify endpoint behavior, permission enforcement and multi-step form data.

### 9.2 Front-End Setup

1. **Initialize project**: Run `npx create-react-app frontend --template vite` or `npx create-next-app@latest frontend`.  Install dependencies (`react-router-dom`, `axios`, `chart.js`, `@mui/material` or `chakra-ui`, `msal-browser` for token handling).  Configure a proxy to forward `/api` requests to the Django server during development.
2. **Set up theme & components**: Define global CSS variables for glass-morphism (blur, transparency).  Build a `Layout` component with header, side nav and dark/light mode toggle.  Include `ThemeProvider` if using a UI library.
3. **Create context providers**: An `AuthContext` stores user info, roles and tokens.  A `FormContext` stores multi-step form state.  A `NotificationContext` can manage notifications.
4. **Implement pages**: Make directories under `src/pages` for each route (Dashboard, JobCreate, TaskCreate, JobDetail, TaskDetail, Approvals, Admin, Settings, etc.).  On JobCreate page, fetch the form definition and implement the multi-step wizard using the `FormWizard` component.
5. **Implement PeoplePicker & Search**: Use input fields with asynchronous data sources from the `/api/users/search` endpoint.  For default lists, call `/api/default-approvers` and disable the input for non-admins.
6. **Handle authentication**: Use `msal-browser` to sign in users and acquire an ID token.  Send this token to the Django backend with each API request (in the `Authorization` header).  The backend decodes the token and sets request.user accordingly.
7. **Forms & validation**: Use Formik or React Hook Form to manage input state.  On each step, use the `required` attribute and custom logic to validate fields.  Show error messages next to invalid controls.
8. **Testing & CI**: Use Jest for unit testing components and Cypress for end-to-end tests.  Configure a GitHub Actions workflow to run tests and build the project for each PR.

### 9.3 Deployment

1. **Containerize**: Write a `Dockerfile` for the backend (starting with `python:3.11-slim`) and another for the frontend.  Use Docker Compose to orchestrate PostgreSQL, Redis (optional) and Django.  The React build can be served by Nginx.
2. **Environment secrets**: Use environment variables (via `.env`) to store DB credentials, Azure AD app secrets, Graph secrets, file storage credentials and email sender details.
3. **CI/CD**: Set up actions to build Docker images, run migrations, collect static files, run tests, and deploy to your chosen environment (Azure App Service, AWS ECS, or on-prem).  Use `migration` jobs in CI to ensure DB schema is up to date.
4. **Security & Monitoring**: Enforce HTTPS via the reverse proxy, enable CSRF and secure cookie settings.  Use `django-axes` or built-in throttling to prevent brute-force attacks.  Add logging to catch exceptions and integrate with an APM service (Azure Application Insights, Sentry).  Create an admin page to view audit logs.

## 10. Summary

This comprehensive plan brings together all requirements discussed in our conversations:

- **Multi-step dynamic forms** driven by JSON definitions, with mandatory field enforcement and conditional logic.
- **Design-team-specific fields and metadata** stored in JSONB (Django’s JSONField) to allow schema flexibility.
- **Editable tables** for line items, attachments management and file uploads to SharePoint/Azure Blob, with metadata captured in the database.
- **People Picker integration with Azure AD** using Microsoft Graph.  The system restricts search capability by role and pre-populates default approvers for each design team and request type.
- **Default approval routes & user-defined routes** stored in configuration tables, with job/task creation automatically instantiating approval flows and triggering notifications.
- **Role-based access control** ensuring that only authorized roles can override approval lists, modify routes or search the directory, while normal users follow default policies.
- **Clear project structure** with separate Django apps for accounts, jobs, tasks, approvals, design-team configuration and notifications; and a React front-end with pages corresponding to product workflows.
- **Deployment guidance** for setting up the project, running it locally, hooking up authentication, implementing Graph calls, and rolling it out in production with monitoring and security.

Following this document will help you create a robust, maintainable and secure design-job/task portal tailored to your organization’s workflow.  If you need additional details—such as sample API code or database seeding scripts—feel free to request them.
