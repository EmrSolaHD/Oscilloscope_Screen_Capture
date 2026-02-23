# Comprehensive Full‑Stack Plan Using Django (Python) Backend and Dynamic Request Forms

This document consolidates all prior requirements and corrections into a single, cohesive architecture plan.  It specifies **Python/Django** as the backend (with Django REST Framework for the API) and retains the previously*agreed* features of multi‑page forms, design‑team custom fields, inline editable tables, AD directory lookup for approvers, default approval routing and role‑based access control.

## 1 Rationale

- **Multi‑step forms** reduce cognitive load by breaking complex requests into steps; they improve completion rates and fit forms with conditional logic.
- **Flexible data capture** is achieved by storing supplemental fields in a JSON column (Django’s `JSONField`) so the schema can grow without migrations.
- **Design‑team specificity** ensures only relevant fields appear when the user selects PCB, Hardware, Drawing or Firmware, improving accuracy and preventing user fatigue.
- **Mandatory fields** are enforced client‑side via HTML’s `required` attribute and server‑side via Django validators, guaranteeing required data is present.
- **People Picker / directory lookup** integrates with Azure AD via Microsoft Graph so approvers can be chosen accurately.  Only admins and group leaders may search the entire directory; ordinary users see pre‑loaded default approvers.
- **Auditability and RBAC** ensure only authorised users can modify approval workflows and that edits are logged.

## 2 Technology Stack

### 2.1 Backend (Python/Django)

- **Django 4.x** with **Django REST Framework (DRF)** to expose RESTful APIs.
- **Django JSONField** for storing dynamic metadata (custom fields and approver lists).  JSONField is supported by PostgreSQL and can be indexed.
- **Django ORM** with **PostgreSQL** for robust relational storage.
- **Django Authentication & Azure AD integration** via `django-auth-adfs` or `django-allauth` + `msal` for SSO; we store an `aad_object_id` to align application users with AD identities.
- **Celery with Redis/RabbitMQ** for background tasks such as sending notifications, file uploads and asynchronous approval processes (optional but recommended for scalability).
- **Libraries**: `requests` or `msgraph-core` for Microsoft Graph calls, `django-guardian` for row‑level permissions if fine‑grained controls are needed.

### 2.2 Frontend

- **React with Next.js** (or a plain React app) for modern, component‑based UI, with server‑side rendering where beneficial.
- **Glass‑morphism design** using CSS/SCSS modules or Tailwind CSS for consistent theming; includes light/dark mode toggles.
- **Form wizard component** to render multi‑step forms and enforce validation; custom FieldRenderer to display fields defined by JSON definitions.
- **Editable table component** for inline entry of multiple items.
- **People Picker** component integrated with a backend endpoint to query AD; restricts results based on user role.

### 2.3 File Storage & Attachments

- Files are uploaded via Django REST endpoints and stored in SharePoint/OneDrive using Microsoft Graph or in Azure Blob storage; metadata is stored in an `Attachment` model.

## 3 Data Model & Relationships (Django ORM)

Below are the core models with key fields.  Django’s `ForeignKey`, `ManyToManyField` and `JSONField` are used to model relationships and flexible data.

### 3.1 Identity & Groups

```python
class User(AbstractUser):
    aad_object_id = models.CharField(max_length=64, unique=True)  # from Azure AD
    role = models.CharField(max_length=20, choices=[('ADMIN','Admin'),('GROUP_LEADER','Group Leader'),('USER','User')])
    # additional fields: department, display_name etc.

class Group(models.Model):
    name = models.CharField(max_length=100)
    aad_group_id = models.CharField(max_length=64, blank=True, null=True)  # optional link to AD group

class UserGroupMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
```

### 3.2 Core Entities

```python
class DesignTeam(models.Model):
    name = models.CharField(max_length=50)
    form_definition = models.JSONField()  # dynamic fields specific to team
    default_route = models.ForeignKey('ApprovalRoute', null=True, blank=True, on_delete=models.SET_NULL)

class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    request_type = models.CharField(max_length=50)
    priority = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    group = models.ForeignKey(Group, on_delete=models.PROTECT)
    design_team = models.ForeignKey(DesignTeam, on_delete=models.PROTECT)
    approval_route = models.ForeignKey('ApprovalRoute', null=True, blank=True, on_delete=models.SET_NULL)
    metadata = models.JSONField(default=dict)  # custom fields, approvers, watchers, etc.
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
    approval_route = models.ForeignKey('ApprovalRoute', null=True, blank=True, on_delete=models.SET_NULL)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class JobLineItem(models.Model):
    job = models.ForeignKey(Job, related_name='line_items', on_delete=models.CASCADE)
    item_data = models.JSONField()  # each row as JSON
    order_index = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class TaskLineItem(models.Model):
    task = models.ForeignKey(Task, related_name='line_items', on_delete=models.CASCADE)
    item_data = models.JSONField()
    order_index = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class Attachment(models.Model):
    parent_job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.CASCADE)
    parent_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)  # link to SharePoint / Blob
    mime_type = models.CharField(max_length=100)
    size = models.BigIntegerField()
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
```

### 3.3 Configuration & Workflow

```python
class ApprovalRoute(models.Model):
    name = models.CharField(max_length=100)
    route = models.JSONField()  # list of steps with approver roles/IDs

class DefaultApprover(models.Model):
    design_team = models.ForeignKey(DesignTeam, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=50)
    approver_ids = models.JSONField()  # list of AD object IDs

class FormDefinition(models.Model):
    request_type = models.CharField(max_length=50)
    definition = models.JSONField()  # base multi-step form structure
    permissions = models.JSONField(default=dict)  # roles allowed to view/edit each field or step
```

### 3.4 Relationships Explained

- `User` ↔ `Group` via `UserGroupMembership`: maps users to departments or design teams; used for scoping queries and role restrictions.
- `Job` and `Task`: reference `DesignTeam` to determine specific custom fields; reference `ApprovalRoute` to determine the default approval sequence; store custom data in `metadata`. Tasks may link to a parent Job.
- `JobLineItem` and `TaskLineItem` store each row from the editable table; JSON allows storing arbitrary columns defined by the form.
- `ApprovalRoute`: defines an array of steps; each step might specify an approver role (e.g. `['GROUP_LEADER', 'ENGINEERING_LEAD']`) or explicit AD object IDs.  Jobs or tasks reference a route when the request is created.  The approval flow is progressed by storing the current step index in `metadata.approval_stage`.
- `DefaultApprover`: stores a list of default approver AD IDs per design team/request type.  When a user initiates a job/task, the backend reads this table and pre‑loads the People Picker with these entries for ordinary users.
- `FormDefinition`: stores the base multi‑page form definition per request type.  It may reference fields in `DesignTeam.form_definition` to merge custom fields.

## 4 API Endpoints (Django REST Framework)

| Method & Endpoint | Purpose |
|---|---|
| **POST `/api/auth/login/`** | Handles SSO login (handled mostly by Azure AD/Okta). Returns JWT with roles and group memberships. |
| **GET `/api/form-definitions/?request_type=X`** | Returns the base form definition for the given request type, merged with supplemental fields from `DesignTeam` if suitable.|
| **GET `/api/design-teams/`** | Lists available design teams with names and IDs; used to populate the design team drop‑down.|
| **GET `/api/default-approvers/?design_team_id=X&request_type=Y`** | Returns default approver AD IDs for a given design team and request type.|
| **GET `/api/users/search/?q=John`** | Directory lookup endpoint; only accessible to Admins and Group Leaders. Queries Microsoft Graph using the MSAL token and returns matching users (id, name, email, department).|
| **POST `/api/jobs/`** | Creates a new job. Payload includes base fields, `design_team_id`, `metadata.custom_fields`, `metadata.approver_ids/watchers`, `line_items` and attachments (handle file upload separately).  The backend validates mandatory fields, stores metadata and returns the generated UUID.|
| **GET `/api/jobs/`** | Lists jobs visible to the authenticated user. Supports filters: status, date ranges, design team.|
| **GET `/api/jobs/{id}/`** | Retrieves job details with metadata, line items, attachments and approval status. Permitted if the user belongs to the relevant group or is in `metadata.approver_ids/watchers`.|
| **PUT `/api/jobs/{id}/`** | Updates job details or metadata. Validates that the user has permission to edit (not locked by approval).|
| **POST `/api/jobs/{id}/approve/`** | Approver posts a decision with comments; moves to next stage or finalises.|
| Similar endpoints exist for `/api/tasks/` (list, detail, create, update, approve) |
| **POST `/api/jobs/{id}/attachments/`** | Upload attachments; returns metadata record for each file. |
| **GET `/api/config/approval-routes/`**, **POST/PUT** | For admins to manage approval queues and steps. |
| **GET/POST `/api/config/design-teams/`** | Manage design teams and their specific field definitions and default routes. |
| **GET/POST `/api/config/form-definitions/`** | Manage multi‑step form definitions. |

## 5 Front‑End Pages & Components

| Route/Page | Function | Notable UI Features |
|---|---|---|
| `/dashboard/` | Overview of tasks/jobs; charts summarising statuses, upcoming approvals, etc. | Charts, filters, notifications. |
| `/jobs/new/` | Multi‑step form to create a job. | Steps: (1) Basic info & design team selection; (2) Approvals step with People Picker; (3) Team‑specific custom fields; (4) Attachments & Artifacts; (5) Editable table; (6) Review & submit. |
| `/tasks/new/` | Multi‑step form to create a task. | Inherits design team and group from parent job if applicable; may skip some steps. |
| `/jobs/{id}/` | View/edit job. | Show metadata, line items, current approval stage, attachments, comment thread; allow editing if permitted. |
| `/tasks/{id}/` | View/edit task. | Similar to job view. |
| `/approvals/` | List of items awaiting the logged‑in approver; filter by urgency or due date. | Show context, attachments and forms to capture decisions. |
| `/admin/` | Admin console. | Manage users, groups, design teams, form definitions, approval routes, default approvers and configuration settings. |
| `/config/` or `/database/` | DB & configuration management for advanced admins. | Provide safe editing of JSON definitions with versioning and rollback options. |

### Key Front‑End Components

- **FormWizard**: Handles step progression, loads form definitions from `FormDefinition` and merges with `DesignTeam.form_definition`.  It renders fields via a **FieldRenderer** that chooses the appropriate input type (text, number, date, select, file, table) and binds to state.
- **PeoplePicker**: Connects to `/api/users/search/` for free search. If the user’s role is not `Admin` or `GroupLeader`, it populates from `/api/default-approvers/` and disables free typing; only the default list is shown.
- **EditableTable**: Allows adding/editing rows with per‑column validation; stores results in an array that maps to `JobLineItem` or `TaskLineItem` records.
- **AttachmentUploader**: Handles drag‑and‑drop uploads, progress tracking, and deletion; once uploaded, attachments are associated with the parent job/task.
- **Role‑Based Navigation & Guard**: Uses context or React Router to hide or disable pages/components according to the logged‑in user’s role.

## 6 Workflow Example: Creating a Job

1. **User Sign in** – The user authenticates via Azure AD.  Django receives a JWT containing claims such as `aad_object_id`, username, group membership.  The portal looks up (or creates) the `User` record using `aad_object_id` and stores their role (Admin/GroupLeader/User).
2. **Start New Job** – The user navigates to `/jobs/new/`.  The form wizard fetches the base form definition for `request_type=JOB` and lists available design teams.  The user selects *PCB*; the UI merges the PCB‑specific fields from `DesignTeam.form_definition` into the custom fields step.
3. **Approvals Step** – The wizard loads default approvers for the chosen design team using `/api/default-approvers/?design_team_id=pcb_id&request_type=JOB`.  If the user is a standard `User`, these names appear but cannot search beyond them.  If the user is `GroupLeader` or `Admin`, the People Picker offers a search box that queries Graph via `/api/users/search/`.
4. **Custom Fields** – The user fills in the dynamic fields (e.g. “Layer Count” for PCB).  Required fields are marked with the `required` attribute; the wizard prevents moving forward until they are filled. clearly indicates that HTML5’s `required` attribute stops submission when empty, but server‑side validation still checks for completeness.
5. **Attachments & Table** – The user uploads design documents and BOM spreadsheets, fills in line‑item tables; tags watchers to keep them notified.  Each row of the table is captured into `JobLineItem` instances; attachments are uploaded and recorded in `Attachment` records.
6. **Submit** – The wizard displays a summary; the user reviews and then submits.  Django’s server validates the payload (mandatory fields, allowed approvers, custom fields, role restrictions).  If valid, it inserts a `Job` record with a **system‑generated ID** (UUID) and stores the `metadata` JSON (containing custom fields, approver IDs and watchers).  It also creates `JobLineItem` and `Attachment` records as referenced.  The `approval_route` is set to the default for the design team unless the user has permission to override it.
7. **Approval Process** – The system notifies the first approver (via email or Teams).  Approvers view the job details, attach comments or files, and decide (approve/reject).  Their decisions are recorded and the process moves to the next step in `ApprovalRoute.route`.  When all steps are done, the job status changes to `APPROVED` or `REJECTED` and the job moves to implementation or returns to the triage stage.

## 7 Starting the Project

1. **Initialize Git repository** and create a monorepo or two separate repos (`frontend/`, `backend/`).  Use `Python 3.10+` for the backend and `node 18+` for the React frontend.
2. **Backend setup**:
   - Install Django: `pip install django djangorestframework psycopg2-binary django-auth-adfs celery redis`.
   - Run `django-admin startproject design_portal` and `python manage.py startapp core`.
   - Configure PostgreSQL in `settings.py` (`DATABASES`), add `rest_framework`, `core`, and `django_auth_adfs` to `INSTALLED_APPS`.
   - Define the models above in `core/models.py`.  Create serializers using DRF (`serializers.ModelSerializer`) and viewsets (e.g. `JobViewSet`, `TaskViewSet`, `ApprovalRouteViewSet`).
   - Set up URL routing for the API (use DRF’s `DefaultRouter`).  Create permissions classes (e.g. `IsAdmin`, `IsGroupLeaderOrReadOnly`, `IsOwnerForDetail`).
   - Configure SSO with Azure AD: follow `django-auth-adfs` docs; add `django_auth_adfs.middleware.LoginRequiredMiddleware` and configure `AUDIENCE`, `CLIENT_ID`, etc.  Test login with AD credentials.
   - Implement Graph client for People Picker search endpoints: register an Azure AD application for backend with `User.ReadBasic.All` permission, retrieve a client credential (client ID, secret), use MSAL to acquire a token for Graph, then call `https://graph.microsoft.com/v1.0/users` or `people` endpoints.
   - Add Celery configuration if asynchronous tasks (notifications) are needed.
   - Run migrations: `python manage.py makemigrations` and `python manage.py migrate`.

3. **Frontend setup**:
   - `npx create-next-app` or `create-react-app`.  Install dependencies such as `axios`, `react-router-dom` (or use Next.js routing), `Material‑UI` or `Chakra UI` for components, and possibly `msal-browser` for front‑end Graph calls.
   - Build the Layout with glass‑morphism styling (CSS or Tailwind).  Create pages according to the routes described.
   - Implement the FormWizard component; fetch form definitions via the `/api/form-definitions/` endpoint, and render steps accordingly using a `FieldRenderer` that maps field types to input components.
   - Implement the People Picker component: call `/api/default-approvers/` on mount; if the user is `Admin` or `GroupLeader`, show a search bar that queries `/api/users/search/`.  Show selected users as chips.
   - Use context providers (e.g. `AuthContext`) to store user roles, tokens and group memberships for RBAC logic.  Use React hook forms or Formik for form state management.

4. **Testing & Deployment**:
   - Write unit and integration tests for each API endpoint and major React component.  For the People Picker, write a test to ensure that standard users cannot search outside their default list, whereas Admins can.
   - Set up a CI pipeline (GitHub Actions or Azure Pipelines) to run tests, build Docker images and deploy.  Use environment secrets to configure the Graph app credentials and DB connection strings.  Deploy the Django backend to Azure App Service or containers; deploy the React front‑end to Vercel, Netlify or static hosting with an Nginx proxy.
   - Monitor the system with Logging (e.g. `LOGGING` in Django) and APM (e.g. Azure Application Insights).  Capture audit logs for approval actions and modifications to configuration tables.

## 8 Conclusion

This final plan corrects the earlier misalignment between backend technologies (now firmly using **Python/Django**, not Node.js) and integrates all features discussed: **multi‑page dynamic forms**, **design‑team‑specific custom fields**, **mandatory field enforcement**, **inline editable tables**, **attachments**, **directory‑based People Picker with default and role‑based search**, **approval routing** and **configurable defaults**.  By storing custom data in JSON fields and using Django’s ORM with PostgreSQL, the system remains flexible while preserving relational integrity.  The plan includes clear instructions for bootstrapping the project, designing the schema, implementing the front‑end and backend, and deploying and monitoring the application.
