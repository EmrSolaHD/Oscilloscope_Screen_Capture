# Design-Job & Task Management Portal — C4 Project Plan

> **Single Source of Truth** — This document is the sole authoritative reference for building the portal. It consolidates all prior drafts (architecture_plan, final_full_stack_plan, lookup_defaults, master_plan, master_plan_with_waitress, masterplan_with_diagrams) into one actionable, step-by-step instruction set using the **C4 model** (Context → Containers → Components → Code).

---

## 0  Project Identity

| Item | Value |
|------|-------|
| **Project Name** | Design-Job & Task Management Portal (DesignPortal) |
| **Purpose** | Localized ticketing / design-request system for an engineering team |
| **Host OS** | Windows 11 domain-joined PC |
| **Backend Runtime** | Python 3.11+ / Django 4.x / Django REST Framework |
| **Frontend Runtime** | React 18 + Vite |
| **WSGI Server** | Waitress on port **9091** |
| **Database** | PostgreSQL 15+ |
| **Identity Provider** | Azure AD / Okta (OIDC) |
| **Email / Directory** | Microsoft Graph API |
| **File Storage** | SharePoint / OneDrive (Graph) or local network share |
| **UI Aesthetic** | Glass-morphism — fixed header, fixed footer, collapsible sidebar nav, light/dark mode |

---

## 1  Technology Stack (Full Inventory)

### 1.1  Backend

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.11+ | Primary backend language |
| Framework | Django 4.x | ORM, routing, admin, middleware |
| API | Django REST Framework (DRF) | RESTful JSON API for the SPA |
| Database | PostgreSQL 15+ | Relational storage with JSONB |
| Auth/SSO | `mozilla-django-oidc` or `django-auth-adfs` + MSAL | Okta / Azure AD OpenID Connect |
| Graph Client | `msgraph-core` / `msal` | Directory search, email, file upload |
| Permissions | `django-guardian` (optional) | Row-level object permissions |
| History | `django-simple-history` | Audit trail on models |
| JWT | `djangorestframework-simplejwt` | Access + refresh token pair for SPA auth |
| Rate Limiting | `django-ratelimit` or DRF throttle classes | API rate limiting (100 req/min auth, 30 req/min search) |
| Async Tasks | Celery + Redis (optional) | Background email, file uploads |
| WSGI Server | Waitress | Production server on Windows (port 9091) |
| Service Wrapper | NSSM or Windows Task Scheduler | Run Waitress as a Windows service |
| Static Files | WhiteNoise | Serve static assets without separate web server |
| Environment | `python-dotenv` | Load `.env` secrets |
| Testing | pytest + pytest-django + DRF APITestCase | Unit + integration tests |

### 1.2  Frontend

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | TypeScript / JavaScript (ES2022+) | Frontend language |
| Framework | React 18 | Component-based SPA |
| Bundler | Vite 5 | Fast HMR and build |
| Styling | Tailwind CSS 3 + custom glass-morphism utilities | Utility-first CSS with frosted-glass tokens |
| State | React Context + useReducer (or Zustand) | Global state (auth, theme, form wizard) |
| Routing | React Router 6 | Client-side page routing |
| Forms | React Hook Form | Multi-step form state and validation |
| HTTP | Axios | API calls to DRF endpoints |
| Auth | `@azure/msal-browser` or Okta OIDC SDK | SSO token acquisition |
| Charts | Chart.js (via react-chartjs-2) or ECharts | Dashboard metrics visualization |
| Icons | Lucide React or Heroicons | Consistent iconography |
| Testing | Vitest + React Testing Library + Cypress | Unit, component, E2E tests |

### 1.3  Infrastructure & DevOps

| Layer | Technology | Purpose |
|-------|-----------|---------|
| VCS | Git (GitHub / Azure DevOps) | Version control |
| CI/CD | GitHub Actions or Azure Pipelines | Automated test, build, deploy |
| Reverse Proxy | IIS or Nginx (optional) | TLS termination, compression, static caching |
| Containerization | Docker + Docker Compose (optional) | Portable dev/staging environment |
| Monitoring | Django Logging + Sentry (optional) | Error tracking |

---

## 2  C4 Level 1 — System Context

The System Context diagram identifies the portal and every external actor / system it interacts with.

```mermaid
C4Context
    title System Context — DesignPortal

    Person(requester, "Requester (User)", "Submits design job requests and tasks")
    Person(groupLeader, "Group Leader", "Triages, assigns, overrides approval defaults")
    Person(approver, "Approver", "Reviews and approves/declines items")
    Person(admin, "Admin", "Manages users, config, routes, design teams")

    System(portal, "DesignPortal", "Ticketing & design-job management portal")

    System_Ext(azureAD, "Azure AD / Okta", "Identity provider — OIDC SSO")
    System_Ext(msGraph, "Microsoft Graph", "Directory search, email, file upload")
    System_Ext(sharePoint, "SharePoint / OneDrive", "Artifact / attachment storage")
    System_Ext(postgres, "PostgreSQL", "Relational database")

    Rel(requester, portal, "Creates jobs/tasks, uploads files")
    Rel(groupLeader, portal, "Triages, assigns, overrides defaults")
    Rel(approver, portal, "Approves/rejects items")
    Rel(admin, portal, "Configures system")
    Rel(portal, azureAD, "Authenticates users via OIDC")
    Rel(portal, msGraph, "Sends email, searches directory, uploads files")
    Rel(portal, sharePoint, "Stores attachments")
    Rel(portal, postgres, "Reads/writes data")
```

### Actors

| Actor | Role Enum | Capabilities |
|-------|-----------|-------------|
| **Requester (User)** | `USER` | Create jobs/tasks, view own items, upload attachments, select from default approvers only |
| **Group Leader** | `GROUP_LEADER` | Everything USER can do **plus** triage, assign, override approval defaults, search full directory |
| **Approver** | `APPROVER` (derived from route membership) | Approve/reject items in their queue |
| **Admin** | `ADMIN` | Full system access — manage users, roles, groups, design teams, routes, form definitions, defaults |

### External Systems

| System | Integration Method | Key Permissions |
|--------|-------------------|----------------|
| **Azure AD / Okta** | OIDC Authorization Code Flow | `openid`, `profile`, `email` |
| **Microsoft Graph** | OAuth 2.0 Client Credentials + Delegated | `Mail.Send.Shared`, `User.ReadBasic.All`, `Files.ReadWrite.All` |
| **SharePoint / OneDrive** | Graph `driveItem` endpoints | Upload / download via `Files.ReadWrite.All` |
| **PostgreSQL** | Django ORM via `psycopg2` | Full schema access |

---

## 3  C4 Level 2 — Container Diagram

Shows the major deployable/runnable units and how data flows between them.

```mermaid
C4Container
    title Container Diagram — DesignPortal

    Person(user, "Portal User")

    Container(react, "React SPA", "React 18, Vite, Tailwind", "Glass-morphism UI with fixed header/footer, collapsible sidebar")
    Container(django, "Django API Server", "Django 4, DRF, Waitress:9091", "RESTful backend serving JSON APIs")
    ContainerDb(pg, "PostgreSQL", "PostgreSQL 15", "Stores all relational + JSONB data")
    Container(redis, "Redis (optional)", "Redis 7", "Message broker for Celery background tasks")

    System_Ext(ad, "Azure AD / Okta")
    System_Ext(graph, "Microsoft Graph")
    System_Ext(sp, "SharePoint")

    Rel(user, react, "HTTPS", "Browser")
    Rel(react, django, "HTTPS JSON", "/api/*")
    Rel(django, pg, "SQL", "psycopg2")
    Rel(django, redis, "AMQP", "Celery tasks")
    Rel(django, ad, "OIDC", "Token validation")
    Rel(django, graph, "REST", "Mail.Send, Users, Files")
    Rel(django, sp, "Graph", "Upload/download artifacts")
```

### Container Details

| Container | Runtime | Port | Notes |
|-----------|---------|------|-------|
| **React SPA** | Node 20 (dev) / static files (prod) | 5173 (dev) / served by Django or IIS (prod) | Built with `npm run build`; output collected to Django `static/` |
| **Django API** | Python 3.11 + Waitress | **9091** | `waitress-serve --listen=0.0.0.0:9091 config.wsgi:application` |
| **PostgreSQL** | PostgreSQL 15 | 5432 | Separate service or container |
| **Redis** | Redis 7 | 6379 | Only needed if Celery is used for async tasks |

---

## 4  C4 Level 3 — Component Diagram

### 4.1  Backend Components (Django Apps)

```mermaid
C4Component
    title Backend Components — Django Apps

    Container_Boundary(django, "Django API Server") {
        Component(accounts, "accounts", "Django App", "User model, Group, UserGroupMembership, SSO, RBAC permission classes")
        Component(design_teams, "design_teams", "Django App", "DesignTeam, FormDefinition, DefaultApprover CRUD + APIs")
        Component(jobs, "jobs", "Django App", "Job, JobLineItem CRUD, business logic, history")
        Component(tasks, "tasks", "Django App", "Task, TaskLineItem CRUD, linkage to Job")
        Component(approvals, "approvals", "Django App", "ApprovalRoute, ApprovalInstance, approval progression logic")
        Component(notifications, "notifications", "Django App", "GraphEmailClient, email templates, signals, Celery tasks")
        Component(dashboard, "dashboard", "Django App", "Aggregated metrics endpoints for charts")
        Component(attachments, "attachments", "Django Module", "Attachment model, upload/download via Graph or local storage")
    }
```

#### 4.1.1  accounts App

| File | Responsibility |
|------|---------------|
| `models.py` | `User` (extends `AbstractUser` — adds `aad_object_id`, `role`, `department`, `display_name`, `preferences JSON`), `Group` (name, `aad_group_id`), `UserGroupMembership` (FK → User, FK → Group) |
| `serializers.py` | `UserSerializer`, `GroupSerializer`, `UserGroupMembershipSerializer` |
| `views.py` | `UserViewSet` (list, detail, search), OIDC callback view, `GroupViewSet` |
| `permissions.py` | `IsAdmin`, `IsGroupLeaderOrAbove`, `IsAuthenticated` — DRF permission classes |
| `urls.py` | Routes for user CRUD, group CRUD, directory search |
| `admin.py` | Register User, Group, Membership in Django admin |
| `backends.py` | Custom OIDC authentication backend mapping AD claims to local User |

#### 4.1.2  design_teams App

| File | Responsibility |
|------|---------------|
| `models.py` | `DesignTeam` (name, `form_definition JSON`, `default_route FK → ApprovalRoute`), `DefaultApprover` (FK → DesignTeam, `request_type`, `approver_ids JSON`), `FormDefinition` (`request_type`, `definition JSON`, `permissions JSON`) |
| `serializers.py` | `DesignTeamSerializer`, `DefaultApproverSerializer`, `FormDefinitionSerializer` |
| `views.py` | `DesignTeamViewSet`, `DefaultApproverViewSet`, `FormDefinitionViewSet` — CRUD with admin-only write |
| `urls.py` | `/api/design-teams/`, `/api/default-approvers/`, `/api/form-definitions/` |
| `admin.py` | Register DesignTeam, DefaultApprover, FormDefinition |

#### 4.1.3  jobs App

| File | Responsibility |
|------|---------------|
| `models.py` | `Job` (UUID PK, title, description, `request_type`, priority, status, `due_date`, `created_by FK → User`, `group FK → Group`, `design_team FK → DesignTeam`, `approval_route FK → ApprovalRoute`, `metadata JSON`, timestamps), `JobLineItem` (FK → Job, `order_index`, `data JSON`, timestamp) |
| `serializers.py` | `JobSerializer` (nested line items, attachments), `JobLineItemSerializer` |
| `views.py` | `JobViewSet` (list with filters, create with multi-step payload, detail, update, `@action accept`, `@action reject`, `@action submit_for_approval`, `@action approve`, `@action close`), `JobLineItemViewSet` |
| `signals.py` | On status/assignee change → create `HistoryEntry`, trigger notification |
| `filters.py` | DRF filter backends for status, priority, design_team, date range, group |
| `urls.py` | `/api/jobs/`, `/api/jobs/{id}/`, `/api/jobs/{id}/accept/`, `/api/jobs/{id}/reject/`, `/api/jobs/{id}/submit-for-approval/`, `/api/jobs/{id}/approve/`, `/api/jobs/{id}/close/`, `/api/jobs/{id}/attachments/`, `/api/jobs/{id}/references/` |
| `admin.py` | Register Job, JobLineItem |

#### 4.1.4  tasks App

| File | Responsibility |
|------|---------------|
| `models.py` | `Task` (UUID PK, `parent_job FK → Job` (nullable), title, description, priority, status, `due_date`, `assignee FK → User`, `group FK → Group`, `design_team FK → DesignTeam`, `approval_route FK → ApprovalRoute`, `metadata JSON`, timestamps), `TaskLineItem` (FK → Task, `order_index`, `data JSON`, timestamp) |
| `serializers.py` | `TaskSerializer`, `TaskLineItemSerializer` |
| `views.py` | `TaskViewSet` (same pattern as jobs), `TaskLineItemViewSet` |
| `signals.py` | History + notifications on changes |
| `urls.py` | `/api/tasks/`, `/api/tasks/{id}/`, `/api/tasks/{id}/accept/`, `/api/tasks/{id}/reject/`, `/api/tasks/{id}/submit-for-approval/`, `/api/tasks/{id}/approve/`, `/api/tasks/{id}/close/`, `/api/tasks/{id}/attachments/`, `/api/tasks/{id}/references/` |
| `admin.py` | Register Task, TaskLineItem |

#### 4.1.5  approvals App

| File | Responsibility |
|------|---------------|
| `models.py` | `ApprovalRoute` (name, `route JSON` — ordered list of steps with role/user IDs), `ApprovalInstance` (`parent_job FK`, `parent_task FK`, `route FK → ApprovalRoute`, `current_stage INT`, `status` [PENDING/APPROVED/REJECTED], `decisions JSON`, timestamps) |
| `serializers.py` | `ApprovalRouteSerializer`, `ApprovalInstanceSerializer` |
| `views.py` | `ApprovalRouteViewSet` (admin only), `ApprovalInstanceViewSet` (list queue for current user, approve/reject action) |
| `services.py` | `create_approval_instance(job_or_task)`, `advance_stage(instance, decision, comment)`, `is_fully_approved(instance)` |
| `urls.py` | `/api/config/approval-routes/`, `/api/approval-instances/` |
| `admin.py` | Register ApprovalRoute, ApprovalInstance |

#### 4.1.6  notifications App

| File | Responsibility |
|------|---------------|
| `utils.py` | `GraphEmailClient` — acquires Graph token via MSAL client credentials, sends email via `/sendMail` from dedicated address (e.g. `Ticketing_Portal@company.com`), sets `saveToSentItems=false` |
| `signals.py` | Listens on Job/Task post_save → queues notification |
| `tasks.py` | Celery tasks: `send_approval_notification`, `send_status_update`, `send_completion_notice` |
| `templates/` | HTML email templates: `approval_request.html`, `status_change.html`, `completed.html` |

#### 4.1.7  dashboard App

| File | Responsibility |
|------|---------------|
| `views.py` | `DashboardMetricsView` — aggregated counts by status, priority, design team, group; average turnaround time; upcoming approvals. `MyTasksView` — current user's active tasks and pending approvals |
| `serializers.py` | `MetricSerializer` (label, value, category), `MyTaskSerializer` |
| `urls.py` | `/api/dashboard/metrics/`, `/api/dashboard/my-tasks/` |

#### 4.1.8  Shared / Attachments Module

| File | Responsibility |
|------|---------------|
| `models.py` (in jobs or shared app) | `Attachment` (`parent_job FK`, `parent_task FK`, `file_name`, `file_path` (SharePoint URL or local path), `mime_type`, `size`, `version`, `uploaded_by FK → User`, timestamp) |
| `views.py` | `AttachmentViewSet` — upload (streams to SharePoint via Graph or saves locally), download (redirect URL), delete |
| `services.py` | `upload_to_sharepoint(file, folder_path)`, `upload_to_local(file, media_root)` |

---

### 4.2  Frontend Components (React)

```mermaid
C4Component
    title Frontend Components — React SPA

    Container_Boundary(react, "React SPA") {
        Component(layout, "Layout", "React Component", "Fixed header, fixed footer, collapsible sidebar, theme toggle")
        Component(formWizard, "FormWizard", "React Component", "Multi-step form engine driven by JSON definitions")
        Component(fieldRenderer, "FieldRenderer", "React Component", "Maps field type → input control")
        Component(peoplePicker, "PeoplePicker", "React Component", "Directory lookup / default approver selector")
        Component(editableTable, "EditableTable", "React Component", "Inline CRUD spreadsheet for line items")
        Component(attachmentUploader, "AttachmentUploader", "React Component", "Drag-and-drop file upload with progress")
        Component(chartWidgets, "ChartWidgets", "React Component", "Bar, pie, line chart wrappers")
        Component(rbacGuard, "RBACGuard", "React Component", "Wraps routes/components with role checks")
        Component(authContext, "AuthContext", "React Context", "Current user, roles, tokens")
        Component(themeContext, "ThemeContext", "React Context", "Light/dark mode, glass-morphism tokens")
    }
```

---

## 5  C4 Level 4 — Code (Data Model)

### 5.1  Database Tables — Complete Reference

Every table the application requires is listed below with all columns. Use this as migration source-of-truth.

#### Table: `user` (extends Django `auth_user`)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | Django default user PK |
| username | Varchar(150) | Unique, Not Null | Login identifier |
| email | Varchar(254) | Not Null | Corporate email from AD |
| first_name | Varchar(150) | | Given name |
| last_name | Varchar(150) | | Surname |
| aad_object_id | Varchar(64) | Unique, Not Null | Azure AD object ID — immutable reference |
| role | Varchar(20) | Not Null, Default `USER` | Enum: `ADMIN`, `GROUP_LEADER`, `USER` |
| department | Varchar(100) | Nullable | Organizational department |
| display_name | Varchar(200) | | Full display name from AD |
| preferences | JSONB | Default `{}` | User prefs: default filters, theme, default design team |
| is_active | Boolean | Default True | Account status |
| date_joined | Timestamp | Auto | |

#### Table: `group`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| name | Varchar(100) | Unique, Not Null | Group / department name |
| aad_group_id | Varchar(64) | Nullable | Linked Azure AD security group |
| description | Text | Nullable | Purpose of group |
| created_at | Timestamp | Auto | |

#### Table: `user_group_membership`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| user_id | Integer | FK → user, Not Null | |
| group_id | Integer | FK → group, Not Null | |
| role_in_group | Varchar(30) | Nullable | Optional role within group (e.g. `LEAD`) |
| joined_at | Timestamp | Auto | |
| **Unique** | | `(user_id, group_id)` | Prevent duplicate membership |

#### Table: `design_team`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| name | Varchar(50) | Unique, Not Null | e.g. PCB, Drawing, Hardware, Firmware |
| description | Text | Nullable | Team description |
| form_definition | JSONB | Not Null, Default `{}` | JSON schema for team-specific custom fields |
| default_route_id | Integer | FK → approval_route, Nullable | Default approval route for this team |
| is_active | Boolean | Default True | Soft-delete |
| created_at | Timestamp | Auto | |
| updated_at | Timestamp | Auto | |

#### Table: `approval_route`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| name | Varchar(100) | Not Null | Human-readable route name |
| description | Text | Nullable | |
| route | JSONB | Not Null | Ordered array of steps. Each step: `{ "step": 1, "role": "GROUP_LEADER", "user_ids": ["aad_id_1"], "action": "approve" }` |
| is_active | Boolean | Default True | |
| created_at | Timestamp | Auto | |
| updated_at | Timestamp | Auto | |

#### Table: `default_approver`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| design_team_id | Integer | FK → design_team, Not Null | |
| request_type | Varchar(50) | Not Null | e.g. `JOB`, `TASK` |
| approver_ids | JSONB | Not Null | Array of Azure AD object IDs |
| created_at | Timestamp | Auto | |
| updated_at | Timestamp | Auto | |
| **Unique** | | `(design_team_id, request_type)` | One default list per team + type |

#### Table: `form_definition`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| request_type | Varchar(50) | Unique, Not Null | e.g. `JOB`, `TASK` |
| definition | JSONB | Not Null | Multi-step form schema: steps, fields, labels, types, validation rules, conditional display |
| permissions | JSONB | Default `{}` | Which roles can view/edit each field or step |
| version | Integer | Default 1 | Schema version for backward compatibility |
| created_at | Timestamp | Auto | |
| updated_at | Timestamp | Auto | |

#### Table: `job`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, Default `uuid4` | System-generated, immutable |
| title | Varchar(200) | Not Null | Short title |
| description | Text | Nullable | Detailed description |
| request_type | Varchar(50) | Not Null | Category (e.g. `NEW_DESIGN`, `MODIFICATION`, `REVIEW`) |
| priority | Varchar(20) | Not Null | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| status | Varchar(30) | Not Null, Default `DRAFT` | `DRAFT`, `SUBMITTED`, `ACCEPTED`, `REJECTED`, `IN_PROGRESS`, `PENDING_APPROVAL`, `APPROVAL_REJECTED`, `APPROVED`, `PENDING_CLOSE`, `RE_APPROVAL_REQUIRED`, `COMPLETED` — see Section 5.3 |
| due_date | Date | Nullable | Requested completion date |
| created_by_id | Integer | FK → user, Not Null | Requester |
| group_id | Integer | FK → group, Not Null | Owning department — scopes visibility |
| design_team_id | Integer | FK → design_team, Not Null | Determines custom fields + default route |
| approval_route_id | Integer | FK → approval_route, Nullable | Route used for this job |
| parent_job_id | UUID | FK → job, Nullable | Hierarchical jobs (sub-jobs) |
| metadata | JSONB | Default `{}` | `{ custom_fields: {}, approver_ids: [], watcher_ids: [], approval_stage: 0, reminders_sent: {} }` |
| created_at | Timestamp | Auto | |
| updated_at | Timestamp | Auto | |

#### Table: `task`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, Default `uuid4` | System-generated |
| parent_job_id | UUID | FK → job, Nullable | Null = standalone task |
| title | Varchar(200) | Not Null | |
| description | Text | Nullable | |
| priority | Varchar(20) | Not Null | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| status | Varchar(30) | Not Null, Default `DRAFT` | Same state machine as Job — see Section 5.3 |
| due_date | Date | Nullable | |
| assignee_id | Integer | FK → user, Nullable | Person executing the task |
| created_by_id | Integer | FK → user, Not Null | |
| group_id | Integer | FK → group, Not Null | |
| design_team_id | Integer | FK → design_team, Not Null | |
| approval_route_id | Integer | FK → approval_route, Nullable | |
| metadata | JSONB | Default `{}` | Same structure as Job metadata |
| created_at | Timestamp | Auto | |
| updated_at | Timestamp | Auto | |

#### Table: `job_line_item`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| job_id | UUID | FK → job, Not Null | |
| order_index | Integer | Not Null | Display/sort order |
| data | JSONB | Not Null | Arbitrary row data defined by form schema |
| created_at | Timestamp | Auto | |
| updated_at | Timestamp | Auto | |

#### Table: `task_line_item`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| task_id | UUID | FK → task, Not Null | |
| order_index | Integer | Not Null | |
| data | JSONB | Not Null | |
| created_at | Timestamp | Auto | |
| updated_at | Timestamp | Auto | |

#### Table: `attachment`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| parent_job_id | UUID | FK → job, Nullable | |
| parent_task_id | UUID | FK → task, Nullable | |
| file_name | Varchar(255) | Not Null | Original file name |
| file_path | Varchar(500) | Not Null | SharePoint URL or local path |
| mime_type | Varchar(100) | Not Null | e.g. `application/pdf` |
| size | BigInteger | Not Null | Bytes |
| version | Integer | Default 1 | Attachment version |
| uploaded_by_id | Integer | FK → user, Nullable | |
| created_at | Timestamp | Auto | |
| **Check** | | `parent_job_id IS NOT NULL OR parent_task_id IS NOT NULL` | Must belong to one parent |

#### Table: `approval_instance`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| parent_job_id | UUID | FK → job, Nullable | |
| parent_task_id | UUID | FK → task, Nullable | |
| route_id | Integer | FK → approval_route, Not Null | |
| current_stage | Integer | Default 0 | Index into `route.route[]` |
| status | Varchar(20) | Default `PENDING` | `PENDING`, `APPROVED`, `REJECTED` |
| decisions | JSONB | Default `[]` | Array: `{ stage, approver_aad_id, decision, comment, timestamp }` |
| created_at | Timestamp | Auto | |
| updated_at | Timestamp | Auto | |

#### Table: `comment`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| parent_job_id | UUID | FK → job, Nullable | |
| parent_task_id | UUID | FK → task, Nullable | |
| author_id | Integer | FK → user, Not Null | |
| body | Text | Not Null | Comment text (supports markdown) |
| created_at | Timestamp | Auto | |
| updated_at | Timestamp | Auto | |

#### Table: `history_entry`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| parent_job_id | UUID | FK → job, Nullable | |
| parent_task_id | UUID | FK → task, Nullable | |
| action | Varchar(50) | Not Null | e.g. `STATUS_CHANGE`, `ASSIGNEE_CHANGE`, `APPROVAL_DECISION`, `ATTACHMENT_ADDED`, `COMMENT_ADDED` |
| actor_id | Integer | FK → user, Not Null | Who performed the action |
| old_value | Text | Nullable | Previous value |
| new_value | Text | Nullable | New value |
| details | JSONB | Default `{}` | Additional context |
| created_at | Timestamp | Auto | Immutable |

#### Table: `notification`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| recipient_id | Integer | FK → user, Not Null | Who receives this notification |
| event_type | Varchar(50) | Not Null | e.g. `APPROVAL_REQUESTED`, `DUE_DATE_REMINDER`, `STATUS_CHANGE` |
| title | Varchar(200) | Not Null | Short display title |
| body | Text | Not Null | Detail message |
| link | Varchar(500) | Nullable | Frontend URL to navigate to (e.g. `/jobs/{id}`) |
| is_read | Boolean | Default `false` | Read status for bell badge |
| parent_job_id | UUID | FK → job, Nullable | Related job (for context) |
| parent_task_id | UUID | FK → task, Nullable | Related task (for context) |
| created_at | Timestamp | Auto | |

#### Table: `job_reference`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto | |
| source_job_id | UUID | FK → job, Nullable | Source job (mutually exclusive with source_task_id) |
| source_task_id | UUID | FK → task, Nullable | Source task |
| target_job_id | UUID | FK → job, Nullable | Target job (mutually exclusive with target_task_id) |
| target_task_id | UUID | FK → task, Nullable | Target task |
| reference_type | Varchar(20) | Not Null | `PARENT_CHILD`, `RELATED`, `BLOCKS`, `BLOCKED_BY`, `DUPLICATE`, `SUPERSEDES` |
| notes | Text | Nullable | Optional description of the relationship |
| created_by_id | Integer | FK → user, Not Null | Who created the reference |
| created_at | Timestamp | Auto | |
| **Check** | | At least one source + one target must be non-null | Referential integrity |

---

### 5.2  Entity Relationship Diagram

```mermaid
erDiagram
    USER ||--o{ USER_GROUP_MEMBERSHIP : belongs_to
    GROUP ||--o{ USER_GROUP_MEMBERSHIP : has

    USER ||--o{ JOB : creates
    USER ||--o{ TASK : creates
    USER ||--o{ TASK : assigned_to
    USER ||--o{ COMMENT : authors
    USER ||--o{ ATTACHMENT : uploads
    USER ||--o{ HISTORY_ENTRY : acts

    GROUP ||--o{ JOB : owns
    GROUP ||--o{ TASK : owns

    DESIGN_TEAM ||--o{ JOB : typed_as
    DESIGN_TEAM ||--o{ TASK : typed_as
    DESIGN_TEAM ||--o{ DEFAULT_APPROVER : has
    DESIGN_TEAM }o--|| APPROVAL_ROUTE : default_route

    JOB ||--o{ TASK : has_children
    JOB ||--o{ JOB : has_sub_jobs
    JOB ||--o{ JOB_LINE_ITEM : has
    JOB ||--o{ ATTACHMENT : has
    JOB ||--o{ COMMENT : has
    JOB ||--o{ HISTORY_ENTRY : has
    JOB ||--o{ APPROVAL_INSTANCE : has

    TASK ||--o{ TASK_LINE_ITEM : has
    TASK ||--o{ ATTACHMENT : has
    TASK ||--o{ COMMENT : has
    TASK ||--o{ HISTORY_ENTRY : has
    TASK ||--o{ APPROVAL_INSTANCE : has

    USER ||--o{ NOTIFICATION : receives
    JOB ||--o{ NOTIFICATION : triggers
    TASK ||--o{ NOTIFICATION : triggers

    JOB ||--o{ JOB_REFERENCE : referenced_by
    TASK ||--o{ JOB_REFERENCE : referenced_by

    APPROVAL_ROUTE ||--o{ APPROVAL_INSTANCE : instantiated_as
    APPROVAL_ROUTE ||--o{ JOB : used_by
    APPROVAL_ROUTE ||--o{ TASK : used_by

    USER {
        int id PK
        string aad_object_id UK
        string role
        string department
        jsonb preferences
    }
    GROUP {
        int id PK
        string name UK
        string aad_group_id
    }
    DESIGN_TEAM {
        int id PK
        string name UK
        jsonb form_definition
        int default_route_id FK
    }
    JOB {
        uuid id PK
        string title
        string status
        string priority
        jsonb metadata
    }
    TASK {
        uuid id PK
        uuid parent_job_id FK
        string title
        string status
        jsonb metadata
    }
    JOB_LINE_ITEM {
        int id PK
        uuid job_id FK
        int order_index
        jsonb data
    }
    TASK_LINE_ITEM {
        int id PK
        uuid task_id FK
        int order_index
        jsonb data
    }
    ATTACHMENT {
        int id PK
        string file_name
        string file_path
    }
    APPROVAL_ROUTE {
        int id PK
        string name
        jsonb route
    }
    DEFAULT_APPROVER {
        int id PK
        int design_team_id FK
        string request_type
        jsonb approver_ids
    }
    FORM_DEFINITION {
        int id PK
        string request_type UK
        jsonb definition
        jsonb permissions
    }
    APPROVAL_INSTANCE {
        int id PK
        int current_stage
        string status
        jsonb decisions
    }
    COMMENT {
        int id PK
        text body
    }
    HISTORY_ENTRY {
        int id PK
        string action
    }
    NOTIFICATION {
        int id PK
        int recipient_id FK
        string event_type
        boolean is_read
    }
    JOB_REFERENCE {
        int id PK
        string reference_type
        int created_by_id FK
    }
```

---

### 5.3  Job / Task State Machine

Both Job and Task share the same lifecycle. **Key distinction:** the first "approval" after submission is merely **job acceptance** (Group Leader acknowledges the request). The **actual multi-stage approval route** happens only after work is complete (status = `IN_PROGRESS` → `PENDING_APPROVAL`).

#### 5.3.1  State Diagram

```mermaid
stateDiagram-v2
    [*] --> Draft

    Draft --> Submitted : Requester submits

    state AcceptanceGate <<choice>>
    Submitted --> AcceptanceGate : Group Leader reviews
    AcceptanceGate --> Accepted : GL accepts job
    AcceptanceGate --> Rejected : GL declines job
    Rejected --> Draft : Requester revises & resubmits

    Accepted --> InProgress : Work begins (assigned)

    InProgress --> PendingApproval : Work completed → approval route triggered
    note right of PendingApproval
      Default approvers (sequential):
      1. Group Leader (GL)
      2. Technical Manager (TM)
      3. Design Manager (DM)
      Optional (if configured):
      4. Mechanical Lead
      5. Safety Lead
      6. Project Manager
    end note

    PendingApproval --> ApprovalRejected : Any approver rejects
    ApprovalRejected --> InProgress : Rework required

    PendingApproval --> Approved : All required approvers approve

    Approved --> PendingClose : Returns to GL for closing

    state CloseGate <<choice>>
    PendingClose --> CloseGate : GL reviews for closure
    CloseGate --> Completed : GL closes — no modifications
    CloseGate --> ReApprovalRequired : Job/Task modified before closing

    ReApprovalRequired --> PendingApproval : Re-triggers approval route

    Completed --> [*]
```

#### 5.3.2  State Descriptions

| Status | Description |
|--------|-------------|
| `DRAFT` | Created but not yet submitted |
| `SUBMITTED` | Sent for Group Leader acceptance |
| `ACCEPTED` | Group Leader accepted the job/task — ready for assignment |
| `REJECTED` | Group Leader declined — requester can revise and resubmit |
| `IN_PROGRESS` | Actively being worked on by the assignee |
| `PENDING_APPROVAL` | Work complete — awaiting sequential approval from GL → TM → DM (+ optional approvers) |
| `APPROVAL_REJECTED` | An approver rejected during the approval route — returns to `IN_PROGRESS` for rework |
| `APPROVED` | All required approvers have approved |
| `PENDING_CLOSE` | Approved work returned to Group Leader for final closing review |
| `RE_APPROVAL_REQUIRED` | Job/Task was modified after approval but before closing — must re-enter the approval route |
| `COMPLETED` | Group Leader closed the item — fully done and archived |

#### 5.3.3  Transition Rules

| # | From | To | Trigger | Actor | Side Effects |
|---|------|----|---------|-------|-------------|
| T1 | `DRAFT` | `SUBMITTED` | Requester clicks "Submit" | Requester | Notification to GL; history entry |
| T2 | `SUBMITTED` | `ACCEPTED` | GL clicks "Accept" | Group Leader | Notification to requester; job available for assignment |
| T3 | `SUBMITTED` | `REJECTED` | GL clicks "Reject" with comment | Group Leader | Notification to requester with reason; status reverts path to DRAFT |
| T4 | `REJECTED` | `DRAFT` | Requester edits and saves | Requester | Previous rejection comment preserved in history |
| T5 | `ACCEPTED` | `IN_PROGRESS` | GL assigns work (or self-assigns) | Group Leader | Assignee notified; due-date worker begins tracking |
| T6 | `IN_PROGRESS` | `PENDING_APPROVAL` | Assignee marks work complete | Assignee | Approval instance created (stage 0); first approver (GL) notified |
| T7 | `PENDING_APPROVAL` | `PENDING_APPROVAL` | Current approver approves & next stage exists | Current Approver | Stage advances; next approver notified |
| T8 | `PENDING_APPROVAL` | `APPROVED` | Final approver approves | Last Approver | GL notified to close; requester notified of approval |
| T9 | `PENDING_APPROVAL` | `APPROVAL_REJECTED` | Any approver rejects | Current Approver | Assignee + requester notified; rework details in comment |
| T10 | `APPROVAL_REJECTED` | `IN_PROGRESS` | Assignee acknowledges and begins rework | Assignee | History entry; previous approval decisions preserved |
| T11 | `APPROVED` | `PENDING_CLOSE` | Automatic transition after final approval | System | GL notified to perform closing review |
| T12 | `PENDING_CLOSE` | `COMPLETED` | GL clicks "Close" — no modifications detected | Group Leader | All stakeholders notified; item archived; due-date worker stops |
| T13 | `PENDING_CLOSE` | `RE_APPROVAL_REQUIRED` | System detects modifications to the item | System | GL notified; modification diff logged in history |
| T14 | `RE_APPROVAL_REQUIRED` | `PENDING_APPROVAL` | System re-triggers approval route | System | New approval instance created; all approvers re-notified |

#### 5.3.4  Default Approval Route Structure

When a job/task transitions from `IN_PROGRESS` → `PENDING_APPROVAL`, the system creates an `ApprovalInstance` using this default route:

| Stage | Approver Role | Required | Can Be Skipped |
|-------|--------------|----------|----------------|
| 1 | **Group Leader (GL)** | Yes | Skip if assignee is the GL |
| 2 | **Technical Manager (TM)** | Yes | No |
| 3 | **Design Manager (DM)** | Yes | No |
| 4 | Mechanical Lead | Optional (if configured for the design team) | Yes |
| 5 | Safety Lead | Optional (if configured for the design team) | Yes |
| 6 | Project Manager | Optional (if configured for the design team) | Yes |

> **Re-approval rule:** If any field of a job/task is modified while in `PENDING_CLOSE` status, the system automatically sets the status to `RE_APPROVAL_REQUIRED` and creates a fresh `ApprovalInstance`. All previously recorded approval decisions are archived in `history_entry` but do not carry over to the new instance.

---

## 6  API Endpoint Reference

### 6.1  Authentication

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|---------|
| GET | `/api/auth/login/` | Public | Redirect to IdP |
| GET | `/api/auth/callback/` | Public | OIDC callback; creates/updates local User, returns JWT |
| POST | `/api/auth/logout/` | Authenticated | Invalidates session |
| GET | `/api/auth/me/` | Authenticated | Returns current user profile with roles |

### 6.2  Configuration (Admin)

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|---------|
| GET | `/api/design-teams/` | Authenticated | List design teams |
| POST | `/api/design-teams/` | Admin | Create design team |
| GET/PUT/DELETE | `/api/design-teams/{id}/` | Admin (write) | Detail/update/delete design team |
| GET | `/api/form-definitions/?request_type=X` | Authenticated | Get form definition for type X |
| POST/PUT | `/api/form-definitions/` | Admin | Create/update form definitions |
| GET | `/api/config/approval-routes/` | Authenticated | List routes |
| POST/PUT/DELETE | `/api/config/approval-routes/{id}/` | Admin | Manage routes |
| GET | `/api/default-approvers/?design_team_id=X&request_type=Y` | Authenticated | Get default approver list |
| POST/PUT/DELETE | `/api/default-approvers/{id}/` | Admin | Manage defaults |

### 6.3  Directory Lookup

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|---------|
| GET | `/api/users/search/?q=John` | Admin, GroupLeader | Search AD via Graph — returns `[{ aad_id, display_name, email, department, job_title }]` |
| GET | `/api/users/` | Admin | List local portal users |

### 6.4  Jobs

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|---------|
| GET | `/api/jobs/` | Authenticated (scoped) | List jobs — filters: `status`, `priority`, `design_team`, `group`, `date_from`, `date_to`, `created_by` |
| POST | `/api/jobs/` | Authenticated | Create job (multi-step payload) |
| GET | `/api/jobs/{id}/` | Authenticated (scoped) | Job detail with metadata, line items, attachments, approvals, comments, history |
| PUT/PATCH | `/api/jobs/{id}/` | Owner/GroupLeader/Admin | Update job (restricted if approval in progress) |
| DELETE | `/api/jobs/{id}/` | Admin | Soft-delete |
| POST | `/api/jobs/{id}/accept/` | GroupLeader | Accept a submitted job (triage) `{ comment: "..." }` → status: `ACCEPTED` |
| POST | `/api/jobs/{id}/reject/` | GroupLeader | Reject a submitted job `{ comment: "reason" }` → status: `REJECTED` |
| POST | `/api/jobs/{id}/submit-for-approval/` | Assignee | Submit completed work for approval → creates `ApprovalInstance`, status: `PENDING_APPROVAL` |
| POST | `/api/jobs/{id}/approve/` | Approver at current stage | Submit approval decision `{ decision: "APPROVE"/"REJECT", comment: "..." }` |
| POST | `/api/jobs/{id}/close/` | GroupLeader | Close an approved job → status: `COMPLETED` (fails if modifications detected) |
| POST | `/api/jobs/{id}/attachments/` | Authenticated | Upload attachment |
| GET | `/api/jobs/{id}/attachments/` | Authenticated (scoped) | List attachments |
| POST | `/api/jobs/{id}/comments/` | Authenticated (scoped) | Add comment |
| GET | `/api/jobs/{id}/history/` | Authenticated (scoped) | Audit trail |
| GET | `/api/jobs/{id}/references/` | Authenticated | List all cross-references (see Section 18) |
| POST | `/api/jobs/{id}/references/` | Authenticated | Create a cross-reference to another job/task |

### 6.5  Tasks

Same pattern as Jobs at `/api/tasks/` with identical sub-resources (including `/accept/`, `/reject/`, `/submit-for-approval/`, `/close/`, `/references/`).

### 6.6  Dashboard

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|---------|
| GET | `/api/dashboard/metrics/` | Authenticated | Aggregated metrics: counts by status, priority, team; avg turnaround; upcoming approvals |
| GET | `/api/dashboard/my-tasks/` | Authenticated | Current user's active tasks and pending approvals |

### 6.7  Notifications

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|---------|
| GET | `/api/notifications/` | Authenticated | List current user's notifications (paginated, filterable by `is_read`) |
| GET | `/api/notifications/unread-count/` | Authenticated | Returns `{ count: N }` for bell badge |
| POST | `/api/notifications/{id}/read/` | Authenticated | Mark single notification as read |
| POST | `/api/notifications/read-all/` | Authenticated | Mark all as read |

### 6.8  References

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|---------|
| DELETE | `/api/references/{ref_id}/` | Owner/Admin | Remove a cross-reference |

### 6.9  System / Health

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|---------|
| GET | `/api/health/` | Public (unauthenticated) | Health check — returns `{ status: "ok", db: "ok", timestamp }`. Used by monitoring and load-balancers |
| GET | `/api/version/` | Authenticated | Returns `{ version: "1.0.0", api_version: "v1", build: "..." }` |

> **API Versioning:** All endpoints are served under `/api/` (implicitly v1). If a breaking change is needed in the future, prefix with `/api/v2/` and maintain `/api/v1/` in parallel during migration. The `Accept` header `application/json; version=2` is also supported as an alternative versioning mechanism.

---

## 7  Frontend — Page & Component Specifications

### 7.1  Layout Shell

The entire SPA is wrapped in a persistent **Layout** component.

| Element | Behavior | Glass-morphism Spec |
|---------|----------|---------------------|
| **Header** (fixed top) | Shows app logo/title, search bar, notification bell, user avatar + dropdown (profile, logout), theme toggle (light/dark) | `backdrop-filter: blur(16px); background: rgba(255,255,255,0.15);` (light) / `rgba(30,30,30,0.25);` (dark); bottom border `1px solid rgba(255,255,255,0.18)` |
| **Footer** (fixed bottom) | App version, copyright, status indicators | Same glass treatment; height ~40px; `z-index: 50` |
| **Sidebar** (collapsible left) | Navigation links grouped by section; collapse toggle button; icons + labels when expanded, icons only when collapsed; active link highlighted | Glass panel with `backdrop-filter: blur(20px); background: rgba(255,255,255,0.08);`; width 260px expanded / 64px collapsed; transition 200ms ease |
| **Main Content Area** | Scrollable area between header and footer, right of sidebar | `padding: 24px; overflow-y: auto; height: calc(100vh - header - footer)` |

#### Sidebar Navigation Structure

| Section | Menu Item | Route | Required Role |
|---------|-----------|-------|---------------|
| **Main** | Dashboard | `/dashboard` | All |
| | My Tasks | `/my-tasks` | All |
| **Create** | New Job | `/jobs/new` | All |
| | New Task | `/tasks/new` | All |
| **Work** | Jobs List | `/jobs` | All |
| | Tasks List | `/tasks` | All |
| | Approvals | `/approvals` | All (filtered to user) |
| **Manage** | Triage | `/manage/triage` | GroupLeader, Admin |
| | Assignments | `/manage/assignments` | GroupLeader, Admin |
| **Admin** | Users & Groups | `/admin/users` | Admin |
| | Design Teams | `/admin/design-teams` | Admin |
| | Approval Routes | `/admin/approval-routes` | Admin |
| | Form Definitions | `/admin/form-definitions` | Admin |
| | Default Approvers | `/admin/default-approvers` | Admin |
| **Settings** | Preferences | `/settings` | All |

---

### 7.2  Page Specifications

Each page below includes its purpose, route, data source, and a component/element inventory.

---

#### 7.2.1  Dashboard (`/dashboard`)

**Purpose:** Overview of active work, metrics, and notifications.

| Component / Element | Description | Data Source |
|---------------------|------------|-------------|
| **StatusSummaryCards** | Row of 4-6 glass cards showing counts: Total Jobs, Total Tasks, Pending Approvals, Overdue, Completed (This Month) | `GET /api/dashboard/metrics/` |
| **JobsByStatusChart** | Bar chart — jobs grouped by status | `GET /api/dashboard/metrics/` |
| **TasksByTeamChart** | Pie/doughnut chart — tasks grouped by design team | `GET /api/dashboard/metrics/` |
| **UpcomingApprovalsTable** | Table of items awaiting current user's approval (columns: Title, Type, Due Date, Priority, Actions) | `GET /api/dashboard/my-tasks/` |
| **RecentActivityFeed** | Timeline list of recent history entries across user's scope | `GET /api/jobs/?ordering=-updated_at&limit=10` |
| **FilterBar** | Drop-downs: Date Range, Design Team, Group, Priority | Local state → refetches metrics |
| **NotificationBadge** | Bell icon in header showing count of unread | `GET /api/notifications/unread-count/` (or WebSocket) |

---

#### 7.2.2  Jobs List (`/jobs`)

**Purpose:** Browse, search, and filter all jobs visible to the user.

| Component / Element | Description | Data Source |
|---------------------|------------|-------------|
| **FilterPanel** | Collapsible side panel with filters: Status (multi-select), Priority (multi-select), Design Team, Group, Date Range, Created By | Local state → query params on `GET /api/jobs/` |
| **JobsTable** | Sortable data table | `GET /api/jobs/?status=X&priority=Y&...` |
| → Column: ID | UUID (short display) — clickable link to detail | |
| → Column: Title | Job title | |
| → Column: Status | Badge with color coding | |
| → Column: Priority | Badge (Low/Med/High/Critical) | |
| → Column: Design Team | Team name | |
| → Column: Created By | User display name | |
| → Column: Due Date | Date with overdue highlight | |
| → Column: Created At | Timestamp | |
| → Column: Actions | View, Edit (if permitted) | |
| **Pagination** | Page size selector (10/25/50) + page nav | DRF pagination |
| **CreateButton** | "New Job" FAB or top-right button → `/jobs/new` | |
| **ExportButton** | Export filtered results as CSV | Client-side or backend endpoint |

---

#### 7.2.3  Job Detail (`/jobs/{id}`)

**Purpose:** View and edit a specific job with all related data.

| Component / Element | Description | Data Source |
|---------------------|------------|-------------|
| **BreadcrumbNav** | Dashboard > Jobs > {Job Title} | |
| **JobHeaderCard** | Glass card: Title, Status badge, Priority badge, Design Team, Due Date, Created By, Created At | `GET /api/jobs/{id}/` |
| **MetadataSection** | Rendered custom fields from `metadata.custom_fields` | Part of job detail response |
| **ApprovalStatusTracker** | Horizontal stepper showing approval route stages; current stage highlighted; each stage shows approver name + decision | `approval_instance` in response |
| **LineItemsTable** | Read-only (or editable if permitted) table of `JobLineItem` rows | Nested in job detail |
| **AttachmentsList** | List of attached files with download links, file size, uploader, version | Nested in job detail |
| **AttachmentUploader** | (If edit permitted) Drag-and-drop upload area | `POST /api/jobs/{id}/attachments/` |
| **CommentThread** | Chronological list of comments with author + timestamp; add-comment input at bottom | `GET /api/jobs/{id}/comments/` |
| **HistoryTimeline** | Vertical timeline: status changes, assignments, approvals, uploads | `GET /api/jobs/{id}/history/` |
| **ActionButtons** | Edit, Submit for Approval, Cancel, Delete (role-dependent visibility) | `PUT /api/jobs/{id}/`, etc. |
| **PeoplePicker (read-only or editable)** | Shows current approvers and watchers | Part of metadata |

---

#### 7.2.4  Create Job (`/jobs/new`) — Multi-Step Wizard

**Purpose:** Step-by-step form for submitting a new design job request.

The FormWizard loads the form schema from `GET /api/form-definitions/?request_type=JOB` and renders each step. Below is the step-by-step breakdown:

**Step 1 — Basic Information**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | Text input | Yes | Short descriptive title |
| Description | Textarea (rich text optional) | No | Detailed description |
| Request Type | Select | Yes | Options: `NEW_DESIGN`, `MODIFICATION`, `REVIEW`, `OTHER` |
| Design Team | Select | Yes | Options loaded from `GET /api/design-teams/` |
| Priority | Select | Yes | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| Due Date | Date picker | No | Desired completion date |
| Group | Select | Yes | User's groups pre-populated; select owning group |

**Step 2 — Stakeholders & Approval**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Approval Route | Read-only display / Select (Admin/GL only) | Yes | Default route loaded from `DesignTeam.default_route`; Admin/GL can change |
| Approvers (PeoplePicker) | PeoplePicker component | Yes (≥1) | Standard users: pre-populated from `GET /api/default-approvers/`; Admin/GL: full directory search via `GET /api/users/search/` |
| Watchers (PeoplePicker) | PeoplePicker component | No | Optional — anyone to notify of status changes |
| Use Default Route | Checkbox | — | Checked by default; uncheck to override (Admin/GL only) |

**Step 3 — Design-Team-Specific Fields**

Dynamically rendered from `DesignTeam.form_definition`. Examples:

| Design Team | Example Fields | Types |
|-------------|---------------|-------|
| **PCB** | Layer Count (number), Board Dimensions (text), Impedance Control (checkbox), Stack-up Type (select) | number, text, checkbox, select |
| **Hardware** | Enclosure Type (select), Power Supply Spec (text), Thermal Requirements (textarea) | select, text, textarea |
| **Firmware** | MCU Type (select), RTOS (select), Code Repository URL (text), Flash Size (number) | select, select, text, number |
| **Drawing** | Drawing Standard (select), Sheet Size (select), Revision Level (text), CAD Tool (select) | select, select, text, select |

Each field definition includes: `{ name, label, type, required, options[], conditionalDisplay, helpText }`.

**Step 4 — Attachments & Artifacts**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| File Upload | AttachmentUploader (drag-and-drop) | No | Multiple files; show progress bar; accepted types configurable |
| Artifact Folder | Text input | No | Optional: path to network share or SharePoint folder |
| Version Notes | Textarea | No | Description of uploaded files |

**Step 5 — Line Items / Custom Table**

| Component | Description |
|-----------|-------------|
| EditableTable | Columns defined in `FormDefinition.definition` for the line-item step. Example columns for a BOM: Part Number, Description, Quantity, Unit, Supplier, Notes. Users add/remove/reorder rows. Each row becomes a `JobLineItem`. |

**Step 6 — Review & Submit**

| Component | Description |
|-----------|-------------|
| ReviewSummary | Read-only display of all data entered in Steps 1-5, grouped by step. Allows user to click "Edit" on any step to return to it. |
| SubmitButton | Validates all required fields; sends `POST /api/jobs/` with full payload; shows loading spinner; redirects to job detail on success. |
| SaveDraftButton | Saves current state as a `DRAFT` job without kicking off approval. |

---

#### 7.2.5  Tasks List (`/tasks`)

Mirrors the Jobs List with the same filter panel and table structure. Additional column: **Parent Job** (link to parent if exists).

| Component / Element | Description |
|---------------------|-------------|
| **FilterPanel** | Same as Jobs + additional filter: Parent Job |
| **TasksTable** | Columns: ID, Title, Status, Priority, Design Team, Assignee, Parent Job, Due Date, Created At, Actions |
| **CreateButton** | → `/tasks/new` |

---

#### 7.2.6  Create Task (`/tasks/new`) — Multi-Step Wizard

Same 6-step structure as Create Job. Differences:

- **Step 1** adds an optional **Parent Job** selector (type-ahead searching existing jobs).
- **Step 1** adds an **Assignee** field (PeoplePicker — same role restrictions apply).
- If a Parent Job is selected, Design Team and Group auto-populate from the parent.

---

#### 7.2.7  Task Detail (`/tasks/{id}`)

Same structure as Job Detail. Additional elements:

| Component / Element | Description |
|---------------------|-------------|
| **ParentJobLink** | If task has a parent, show link to parent job |
| **AssigneeCard** | Shows assignee with avatar, name, department |
| **SubtasksList** | If this task can have sub-tasks, list them |

---

#### 7.2.8  Approvals (`/approvals`)

**Purpose:** Centralized queue of items awaiting the current user's approval decision.

| Component / Element | Description | Data Source |
|---------------------|------------|-------------|
| **ApprovalsTable** | Table of pending items | `GET /api/approval-instances/?status=PENDING&approver=me` |
| → Column: Type | Job / Task | |
| → Column: Title | Clickable link to detail | |
| → Column: Requester | Who submitted | |
| → Column: Design Team | | |
| → Column: Stage | Current stage name/number | |
| → Column: Due Date | | |
| → Column: Priority | Badge | |
| → Column: Actions | Approve / Reject buttons — open modal | |
| **ApprovalModal** | Modal with: item summary, attachments, comment input, Approve/Reject buttons | `POST /api/jobs/{id}/approve/` or tasks |
| **FilterBar** | Filter by type (Job/Task), priority, design team, date range | |

---

#### 7.2.9  Manage / Triage (`/manage/triage`)

**Purpose:** Group Leaders triage incoming requests — accept, hold, assign, reject.

| Component / Element | Description | Data Source |
|---------------------|------------|-------------|
| **TriageTable** | Table of `SUBMITTED` jobs/tasks in the leader's groups | `GET /api/jobs/?status=SUBMITTED&group=my_groups` |
| → Column: Title, Requester, Design Team, Priority, Due Date | Standard columns | |
| → Column: Actions | Accept → set `IN_PROGRESS` + assign; Hold; Reject → set `REJECTED` with comment; Create Sub-Task | |
| **AssignmentModal** | PeoplePicker to select assignee; set priority; add comment | `PUT /api/jobs/{id}/ or /api/tasks/` |
| **QuickCreateTask** | Inline form to create a child task from a job | `POST /api/tasks/` with `parent_job_id` |

---

#### 7.2.10  Manage / Assignments (`/manage/assignments`)

**Purpose:** View workload distribution and reassign tasks.

| Component / Element | Description |
|---------------------|-------------|
| **AssignmentBoard** | Kanban-style board with columns per assignee or per status |
| **WorkloadChart** | Bar chart showing task count per assignee |
| **ReassignAction** | Drag-drop or button to reassign a task to another user |

---

#### 7.2.11  Admin — Users & Groups (`/admin/users`)

**Purpose:** Manage portal users and group memberships.

| Component / Element | Description | Data Source |
|---------------------|------------|-------------|
| **UsersTable** | Columns: Name, Email, Role, Department, Groups, Status, Actions (Edit/Deactivate) | `GET /api/users/` |
| **EditUserModal** | Change role, department, group memberships | `PUT /api/users/{id}/` |
| **GroupsTable** | Columns: Name, AD Group ID, Member Count, Actions | `GET /api/groups/` |
| **EditGroupModal** | Change name, link AD group | `PUT /api/groups/{id}/` |
| **SyncADButton** | Trigger AD sync (management command) | `POST /api/admin/sync-ad/` |

---

#### 7.2.12  Admin — Design Teams (`/admin/design-teams`)

| Component / Element | Description |
|---------------------|-------------|
| **TeamsList** | Cards or table listing design teams with name, default route, field count |
| **EditTeamForm** | Name, description, default approval route (select), form_definition JSON editor (with preview) |
| **FormDefinitionPreview** | Live preview of how team-specific fields will render in the wizard |

---

#### 7.2.13  Admin — Approval Routes (`/admin/approval-routes`)

| Component / Element | Description |
|---------------------|-------------|
| **RoutesList** | Table: Name, Steps Count, Used By (design teams), Actions |
| **RouteEditor** | Ordered list editor: add/remove/reorder steps; each step specifies role or specific users (PeoplePicker); drag to reorder |
| **RoutePreview** | Visual stepper preview of the route |

---

#### 7.2.14  Admin — Form Definitions (`/admin/form-definitions`)

| Component / Element | Description |
|---------------------|-------------|
| **DefinitionsList** | Table: Request Type, Steps Count, Last Updated |
| **JSONEditor** | Structured JSON editor for defining steps, fields, types, validation rules, conditional display logic |
| **LivePreview** | Renders the form wizard with current definition — read-only data |

---

#### 7.2.15  Admin — Default Approvers (`/admin/default-approvers`)

| Component / Element | Description |
|---------------------|-------------|
| **DefaultsTable** | Columns: Design Team, Request Type, Approver Count, Actions |
| **EditDefaultsForm** | Select design team + request type; PeoplePicker (full search for admin) to set default approver list |

---

#### 7.2.16  Settings / Preferences (`/settings`)

| Component / Element | Description |
|---------------------|-------------|
| **ThemeSelector** | Toggle: Light / Dark / System |
| **DefaultFilters** | Set default design team, priority, group for list views |
| **NotificationPrefs** | Toggle email vs. in-app for different event types |
| **LanguageSelector** | (Future) Locale selection |

---

## 8  Glass-Morphism Design System

### 8.1  CSS Token Reference

Define these as CSS custom properties in `theme/variables.css`:

```css
:root {
  /* ── Light Mode ── */
  --glass-bg: rgba(255, 255, 255, 0.15);
  --glass-bg-card: rgba(255, 255, 255, 0.25);
  --glass-border: rgba(255, 255, 255, 0.18);
  --glass-shadow: 0 8px 32px rgba(31, 38, 135, 0.15);
  --glass-blur: 16px;
  --glass-blur-heavy: 24px;

  --color-primary: #4F46E5;
  --color-primary-hover: #4338CA;
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-danger: #EF4444;
  --color-text: #1F2937;
  --color-text-secondary: #6B7280;
  --color-bg: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --color-surface: #FFFFFF;

  --header-height: 64px;
  --footer-height: 40px;
  --sidebar-width: 260px;
  --sidebar-collapsed-width: 64px;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;

  --transition-speed: 200ms;
}

[data-theme="dark"] {
  --glass-bg: rgba(30, 30, 30, 0.25);
  --glass-bg-card: rgba(40, 40, 40, 0.35);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);

  --color-text: #F9FAFB;
  --color-text-secondary: #9CA3AF;
  --color-bg: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  --color-surface: #1F2937;
}
```

### 8.2  Glass Card Utility Classes (Tailwind-compatible)

```css
/* theme/glass.css */
.glass-panel {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--glass-shadow);
}

.glass-card {
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--glass-blur-heavy));
  -webkit-backdrop-filter: blur(var(--glass-blur-heavy));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
  padding: 24px;
}

.glass-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--header-height);
  z-index: 100;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur-heavy));
  border-bottom: 1px solid var(--glass-border);
}

.glass-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: var(--footer-height);
  z-index: 100;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur-heavy));
  border-top: 1px solid var(--glass-border);
}

.glass-sidebar {
  position: fixed;
  top: var(--header-height);
  left: 0;
  bottom: var(--footer-height);
  width: var(--sidebar-width);
  z-index: 90;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  border-right: 1px solid var(--glass-border);
  transition: width var(--transition-speed) ease;
  overflow-y: auto;
}

.glass-sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}
```

### 8.3  Accessibility Guardrails

| Rule | Implementation |
|------|---------------|
| Contrast ratio ≥ 4.5:1 for text | Use opaque text over semi-transparent backgrounds |
| Blur fallback | Detect `backdrop-filter` support; provide solid fallback background |
| Opacity range | Keep background opacity between 10-40% for glass panels |
| Focus indicators | Visible focus rings on all interactive elements |
| Keyboard navigation | All sidebar items, form fields, and buttons reachable via Tab |
| ARIA roles | Sidebar = `navigation`, header = `banner`, footer = `contentinfo`, main = `main` |

---

## 9  Project Folder Structure

```
DesignPortal/                          # Git repository root
├── README.md
├── SECURITY.md                        # Vulnerability disclosure policy (CRA Art. 11)
├── .env.example                       # Template for environment variables
├── .gitignore
├── docker-compose.yml                 # Optional: PG + Redis + Django
│
├── backend/                           # Django project
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                        # Django settings package
│   │   ├── __init__.py
│   │   ├── base.py                    # Common: INSTALLED_APPS, DRF, CORS, auth
│   │   ├── dev.py                     # DEBUG=True, SQLite fallback
│   │   ├── prod.py                    # DEBUG=False, allowed hosts, static root
│   │   ├── wsgi.py                    # Waitress entry: `config.wsgi:application`
│   │   └── urls.py                    # Root URLConf
│   │
│   ├── apps/
│   │   ├── accounts/
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # User, Group, UserGroupMembership
│   │   │   ├── serializers.py
│   │   │   ├── views.py              # UserViewSet, directory search, debug login
│   │   │   ├── permissions.py         # IsAdmin, IsGroupLeaderOrAbove
│   │   │   ├── backends.py           # Custom OIDC backend + DebugAuthBackend
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── tests.py
│   │   │   └── management/
│   │   │       └── commands/
│   │   │           └── seed_debug_users.py  # Debug user seeder (Section 10.1)
│   │   │
│   │   ├── design_teams/
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # DesignTeam, DefaultApprover, FormDefinition
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests.py
│   │   │
│   │   ├── jobs/
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # Job, JobLineItem
│   │   │   ├── serializers.py
│   │   │   ├── views.py              # JobViewSet with approve action
│   │   │   ├── filters.py            # DRF filter backends
│   │   │   ├── signals.py            # History + notification triggers
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests.py
│   │   │
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # Task, TaskLineItem
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── filters.py
│   │   │   ├── signals.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests.py
│   │   │
│   │   ├── approvals/
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # ApprovalRoute, ApprovalInstance
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── services.py           # create_instance, advance_stage
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests.py
│   │   │
│   │   ├── notifications/
│   │   │   ├── __init__.py
│   │   │   ├── models.py              # Notification (in-app bell notifications)
│   │   │   ├── serializers.py
│   │   │   ├── views.py               # NotificationViewSet (list, mark-read)
│   │   │   ├── utils.py              # GraphEmailClient
│   │   │   ├── signals.py            # Event listeners
│   │   │   ├── tasks.py              # Celery async tasks
│   │   │   ├── workers.py            # Due-date monitoring logic
│   │   │   ├── urls.py
│   │   │   ├── tests.py
│   │   │   ├── management/
│   │   │   │   └── commands/
│   │   │   │       └── check_due_dates.py  # Due-date worker (Section 16)
│   │   │   └── templates/
│   │   │       ├── approval_request.html
│   │   │       ├── status_change.html
│   │   │       ├── completed.html
│   │   │       ├── due_date_reminder.html
│   │   │       ├── due_date_urgent.html
│   │   │       ├── due_date_final.html
│   │   │       ├── due_date_today.html
│   │   │       └── due_date_overdue.html
│   │   │
│   │   ├── dashboard/
│   │   │   ├── __init__.py
│   │   │   ├── views.py              # Metrics + my-tasks endpoints
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   └── tests.py
│   │   │
│   │   └── shared/
│   │       ├── __init__.py
│   │       ├── models.py             # Attachment, Comment, HistoryEntry, JobReference
│   │       ├── serializers.py
│   │       ├── views.py              # AttachmentViewSet, CommentViewSet, ReferenceViewSet, HealthCheckView
│   │       ├── services.py           # upload_to_sharepoint, upload_to_local
│   │       ├── urls.py
│   │       └── tests.py
│   │
│   ├── static/                        # collectstatic output
│   └── media/                         # Local uploads (dev)
│
├── frontend/                          # React + Vite project
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx                   # Entrypoint
│       ├── App.tsx                    # Router + Layout wrapper
│       │
│       ├── theme/
│       │   ├── variables.css          # CSS custom properties (Section 8.1)
│       │   └── glass.css             # Glass-morphism utilities (Section 8.2)
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Layout.tsx         # Shell: Header + Sidebar + Footer + Main
│       │   │   ├── Header.tsx         # Fixed top bar
│       │   │   ├── Footer.tsx         # Fixed bottom bar
│       │   │   ├── Sidebar.tsx        # Collapsible left nav
│       │   │   └── ThemeToggle.tsx    # Light/Dark switch
│       │   │
│       │   ├── forms/
│       │   │   ├── FormWizard.tsx     # Multi-step engine
│       │   │   ├── FieldRenderer.tsx  # Dynamic field → input mapper
│       │   │   ├── PeoplePicker.tsx   # Directory lookup / default approvers
│       │   │   ├── EditableTable.tsx  # Inline CRUD table for line items
│       │   │   └── AttachmentUploader.tsx  # Drag-drop file upload
│       │   │
│       │   ├── data/
│       │   │   ├── DataTable.tsx      # Reusable sortable, paginated table
│       │   │   ├── FilterPanel.tsx    # Collapsible filter controls
│       │   │   └── Pagination.tsx     # Page nav component
│       │   │
│       │   ├── feedback/
│       │   │   ├── Modal.tsx          # Glass-morphism modal dialog
│       │   │   ├── Toast.tsx          # Notification toast
│       │   │   └── LoadingSpinner.tsx # Spinner / skeleton
│       │   │
│       │   ├── display/
│       │   │   ├── GlassCard.tsx      # Generic glass container
│       │   │   ├── StatusBadge.tsx    # Colored status pill
│       │   │   ├── PriorityBadge.tsx  # Priority indicator
│       │   │   ├── ApprovalStepper.tsx # Horizontal approval stage tracker
│       │   │   ├── HistoryTimeline.tsx # Vertical history feed
│       │   │   └── ChartWidgets.tsx   # Chart.js wrappers
│       │   │
│       │   └── guards/
│       │       └── RBACGuard.tsx      # Role-based route/component wrapper
│       │
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── jobs/
│       │   │   ├── JobsList.tsx
│       │   │   ├── JobNew.tsx         # Hosts FormWizard for job creation
│       │   │   └── JobDetail.tsx
│       │   ├── tasks/
│       │   │   ├── TasksList.tsx
│       │   │   ├── TaskNew.tsx
│       │   │   └── TaskDetail.tsx
│       │   ├── approvals/
│       │   │   └── Approvals.tsx
│       │   ├── manage/
│       │   │   ├── Triage.tsx
│       │   │   └── Assignments.tsx
│       │   ├── admin/
│       │   │   ├── UsersGroups.tsx
│       │   │   ├── DesignTeams.tsx
│       │   │   ├── ApprovalRoutes.tsx
│       │   │   ├── FormDefinitions.tsx
│       │   │   └── DefaultApprovers.tsx
│       │   └── settings/
│       │       └── Settings.tsx
│       │
│       ├── context/
│       │   ├── AuthContext.tsx         # User, roles, token
│       │   ├── ThemeContext.tsx        # Light/dark mode state
│       │   └── FormContext.tsx         # Wizard state (optional)
│       │
│       ├── services/
│       │   ├── api.ts                 # Axios instance + interceptors
│       │   ├── auth.ts                # MSAL / Okta SDK wrappers
│       │   ├── jobsApi.ts             # Typed API functions for /api/jobs/
│       │   ├── tasksApi.ts
│       │   ├── approvalsApi.ts
│       │   ├── designTeamsApi.ts
│       │   ├── dashboardApi.ts
│       │   └── usersApi.ts
│       │
│       ├── hooks/
│       │   ├── useAuth.ts             # Access AuthContext
│       │   ├── useTheme.ts
│       │   ├── usePeoplePicker.ts     # Encapsulates search + defaults logic
│       │   └── useFormWizard.ts       # Step navigation + validation
│       │
│       └── types/
│           ├── models.ts              # TS interfaces for Job, Task, User, etc.
│           ├── api.ts                 # API request/response types
│           └── forms.ts               # FormDefinition, FieldDefinition types
│
└── docs/
    ├── C4_PROJECT_PLAN.md             # THIS DOCUMENT
    └── CHANGELOG.md
```

---

## 10  Environment Variables (`.env`)

```env
# ── Django ──
DJANGO_SECRET_KEY=change-me-to-random-string
DJANGO_SETTINGS_MODULE=config.prod
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,your-hostname
DJANGO_DEBUG=False

# ── Database ──
DATABASE_URL=postgres://portal_user:password@localhost:5432/design_portal
# or individual vars:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=design_portal
DB_USER=portal_user
DB_PASSWORD=change-me

# ── Azure AD / Okta ──
OIDC_CLIENT_ID=your-app-client-id
OIDC_CLIENT_SECRET=your-app-client-secret
OIDC_AUTHORITY=https://login.microsoftonline.com/your-tenant-id
OIDC_REDIRECT_URI=http://localhost:9091/api/auth/callback/

# ── Microsoft Graph ──
GRAPH_CLIENT_ID=your-graph-app-client-id
GRAPH_CLIENT_SECRET=your-graph-app-client-secret
GRAPH_TENANT_ID=your-tenant-id
GRAPH_SENDER_EMAIL=Ticketing_Portal@company.com

# ── File Storage ──
FILE_STORAGE_BACKEND=sharepoint   # or 'local'
SHAREPOINT_SITE_ID=your-site-id
SHAREPOINT_DRIVE_ID=your-drive-id
LOCAL_MEDIA_ROOT=C:\PortalFiles\media

# ── Waitress ──
WAITRESS_HOST=0.0.0.0
WAITRESS_PORT=9091

# ── Redis (optional for Celery) ──
REDIS_URL=redis://localhost:6379/0

# ── Debug / Seed Users (dev only) ──
DEBUG_AUTH_ENABLED=True              # Enables local login bypass (NEVER True in production)
DEBUG_AUTH_HEADER=X-Debug-User       # Header name for impersonation
SEED_USERS_ON_STARTUP=False          # Auto-run seed_debug_users on first migrate
```

---

## 10.1  Debug / Seed Users

These local-only users are **not in Azure AD**. They exist solely for UI testing across all RBAC roles without requiring an IdP connection. They are created via a management command and use a special `DebugAuthBackend` that bypasses OIDC.

> **Security:** Debug auth MUST be disabled in production. The `DebugAuthBackend` is gated behind `DEBUG_AUTH_ENABLED=True` and the `DEBUG=True` Django setting. Both must be true for the bypass to function.

### 10.1.1  Seed User Table

| # | Username | Email | Password | Role | Group | Design Team | Department | Purpose |
|---|----------|-------|----------|------|-------|-------------|------------|----------|
| 1 | `debug_admin` | debug.admin@local.test | `DebugAdmin!2025` | `ADMIN` | All (membership in every group) | — | IT | Test admin panel, user management, config CRUD, full system visibility |
| 2 | `debug_gl_pcb` | debug.gl.pcb@local.test | `DebugGL!2025` | `GROUP_LEADER` | Electronics | PCB | Electronics Engineering | Test triage, job acceptance/rejection, assignment, closing, GL-level approval |
| 3 | `debug_gl_hw` | debug.gl.hw@local.test | `DebugGL!2025` | `GROUP_LEADER` | Mechanical | Hardware | Mechanical Engineering | Test GL workflow for a different team |
| 4 | `debug_tm` | debug.tm@local.test | `DebugTM!2025` | `USER` + `TECHNICAL_MANAGER` flag | Electronics | PCB | Electronics Engineering | Test Technical Manager approval stage |
| 5 | `debug_dm` | debug.dm@local.test | `DebugDM!2025` | `USER` + `DESIGN_MANAGER` flag | Electronics | PCB | Electronics Engineering | Test Design Manager approval stage |
| 6 | `debug_user_pcb` | debug.user.pcb@local.test | `DebugUser!2025` | `USER` | Electronics | PCB | Electronics Engineering | Test standard user: create jobs/tasks, view own items, limited search |
| 7 | `debug_user_fw` | debug.user.fw@local.test | `DebugUser!2025` | `USER` | Firmware | Firmware | Firmware Engineering | Test standard user in a different team |
| 8 | `debug_user_draw` | debug.user.draw@local.test | `DebugUser!2025` | `USER` | Drafting | Drawing | Drafting & Documentation | Test Drawing team fields and workflow |
| 9 | `debug_approver_mech` | debug.mech@local.test | `DebugAppr!2025` | `USER` + `MECHANICAL_LEAD` flag | Mechanical | Hardware | Mechanical Engineering | Test optional Mechanical Lead approval stage |
| 10 | `debug_approver_safety` | debug.safety@local.test | `DebugAppr!2025` | `USER` + `SAFETY_LEAD` flag | Quality | Hardware | Safety & Compliance | Test optional Safety Lead approval stage |

### 10.1.2  Seed Groups & Design Teams

The seed command also creates these groups and teams if they don't already exist:

| Group | Design Team | Default Approval Route |
|-------|-------------|------------------------|
| Electronics | PCB | Standard 6-Stage (GL → TM → DM → Mech → Safety → PM) |
| Mechanical | Hardware | Standard 6-Stage |
| Firmware | Firmware | Standard 3-Stage (GL → TM → DM) |
| Drafting | Drawing | Standard 3-Stage |
| Quality | — | — |
| IT | — | — |

### 10.1.3  Management Command: `seed_debug_users`

**File:** `backend/apps/accounts/management/commands/seed_debug_users.py`

```python
# Usage:
#   python manage.py seed_debug_users          # Create all debug users
#   python manage.py seed_debug_users --reset   # Delete & recreate all debug users
#   python manage.py seed_debug_users --list     # List existing debug users

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import Group, UserGroupMembership
from apps.design_teams.models import DesignTeam

User = get_user_model()

DEBUG_USERS = [
    {
        "username": "debug_admin",
        "email": "debug.admin@local.test",
        "password": "DebugAdmin!2025",
        "first_name": "Debug",
        "last_name": "Admin",
        "role": "ADMIN",
        "department": "IT",
        "aad_object_id": "00000000-0000-0000-0000-000000000001",
        "groups": ["__ALL__"],
    },
    {
        "username": "debug_gl_pcb",
        "email": "debug.gl.pcb@local.test",
        "password": "DebugGL!2025",
        "first_name": "Debug",
        "last_name": "GL-PCB",
        "role": "GROUP_LEADER",
        "department": "Electronics Engineering",
        "aad_object_id": "00000000-0000-0000-0000-000000000002",
        "groups": ["Electronics"],
    },
    {
        "username": "debug_gl_hw",
        "email": "debug.gl.hw@local.test",
        "password": "DebugGL!2025",
        "first_name": "Debug",
        "last_name": "GL-HW",
        "role": "GROUP_LEADER",
        "department": "Mechanical Engineering",
        "aad_object_id": "00000000-0000-0000-0000-000000000003",
        "groups": ["Mechanical"],
    },
    {
        "username": "debug_tm",
        "email": "debug.tm@local.test",
        "password": "DebugTM!2025",
        "first_name": "Debug",
        "last_name": "TechMgr",
        "role": "USER",
        "department": "Electronics Engineering",
        "aad_object_id": "00000000-0000-0000-0000-000000000004",
        "groups": ["Electronics"],
        "extra_flags": {"is_technical_manager": True},
    },
    {
        "username": "debug_dm",
        "email": "debug.dm@local.test",
        "password": "DebugDM!2025",
        "first_name": "Debug",
        "last_name": "DesignMgr",
        "role": "USER",
        "department": "Electronics Engineering",
        "aad_object_id": "00000000-0000-0000-0000-000000000005",
        "groups": ["Electronics"],
        "extra_flags": {"is_design_manager": True},
    },
    {
        "username": "debug_user_pcb",
        "email": "debug.user.pcb@local.test",
        "password": "DebugUser!2025",
        "first_name": "Debug",
        "last_name": "User-PCB",
        "role": "USER",
        "department": "Electronics Engineering",
        "aad_object_id": "00000000-0000-0000-0000-000000000006",
        "groups": ["Electronics"],
    },
    {
        "username": "debug_user_fw",
        "email": "debug.user.fw@local.test",
        "password": "DebugUser!2025",
        "first_name": "Debug",
        "last_name": "User-FW",
        "role": "USER",
        "department": "Firmware Engineering",
        "aad_object_id": "00000000-0000-0000-0000-000000000007",
        "groups": ["Firmware"],
    },
    {
        "username": "debug_user_draw",
        "email": "debug.user.draw@local.test",
        "password": "DebugUser!2025",
        "first_name": "Debug",
        "last_name": "User-Draw",
        "role": "USER",
        "department": "Drafting & Documentation",
        "aad_object_id": "00000000-0000-0000-0000-000000000008",
        "groups": ["Drafting"],
    },
    {
        "username": "debug_approver_mech",
        "email": "debug.mech@local.test",
        "password": "DebugAppr!2025",
        "first_name": "Debug",
        "last_name": "MechLead",
        "role": "USER",
        "department": "Mechanical Engineering",
        "aad_object_id": "00000000-0000-0000-0000-000000000009",
        "groups": ["Mechanical"],
        "extra_flags": {"is_mechanical_lead": True},
    },
    {
        "username": "debug_approver_safety",
        "email": "debug.safety@local.test",
        "password": "DebugAppr!2025",
        "first_name": "Debug",
        "last_name": "SafetyLead",
        "role": "USER",
        "department": "Safety & Compliance",
        "aad_object_id": "00000000-0000-0000-0000-000000000010",
        "groups": ["Quality"],
        "extra_flags": {"is_safety_lead": True},
    },
]

class Command(BaseCommand):
    help = "Create debug/seed users for local UI testing (not in AAD)"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete and recreate all debug users")
        parser.add_argument("--list", action="store_true", help="List existing debug users")

    def handle(self, *args, **options):
        if options["list"]:
            for u in User.objects.filter(aad_object_id__startswith="00000000-0000-0000-0000"):
                self.stdout.write(f"{u.username} | {u.role} | {u.email}")
            return

        if options["reset"]:
            deleted, _ = User.objects.filter(aad_object_id__startswith="00000000-0000-0000-0000").delete()
            self.stdout.write(f"Deleted {deleted} debug users")

        for data in DEBUG_USERS:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": data["email"],
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "role": data["role"],
                    "department": data["department"],
                    "aad_object_id": data["aad_object_id"],
                    "display_name": f"{data['first_name']} {data['last_name']}",
                },
            )
            if created:
                user.set_password(data["password"])
                user.save()
                # extra_flags stored in preferences JSONB
                if "extra_flags" in data:
                    user.preferences = {**user.preferences, **data["extra_flags"]}
                    user.save(update_fields=["preferences"])

            # Group membership
            group_names = data.get("groups", [])
            if "__ALL__" in group_names:
                group_names = list(Group.objects.values_list("name", flat=True))
            for gname in group_names:
                grp, _ = Group.objects.get_or_create(name=gname)
                UserGroupMembership.objects.get_or_create(user=user, group=grp)

            status = "CREATED" if created else "EXISTS"
            self.stdout.write(f"  [{status}] {data['username']} ({data['role']})")

        self.stdout.write(self.style.SUCCESS("Debug users seeded successfully."))
```

### 10.1.4  Debug Authentication Backend

**File:** `backend/apps/accounts/backends.py` — add alongside the OIDC backend:

```python
import os
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class DebugAuthBackend:
    """
    Local-only authentication backend for debug/seed users.
    Authenticates via username + password (standard Django auth).
    Only active when BOTH settings.DEBUG=True AND DEBUG_AUTH_ENABLED=True.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not (settings.DEBUG and os.getenv("DEBUG_AUTH_ENABLED", "False").lower() == "true"):
            return None
        try:
            user = User.objects.get(username=username)
            if user.check_password(password) and user.is_active:
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
```

**Settings (`config/dev.py`):**

```python
# Add DebugAuthBackend BEFORE the OIDC backend so local users can log in
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.DebugAuthBackend",   # Debug users (dev only)
    "apps.accounts.backends.OIDCBackend",         # Azure AD / Okta
    "django.contrib.auth.backends.ModelBackend",  # Django admin
]
```

### 10.1.5  Frontend Debug Login Page

When `DEBUG_AUTH_ENABLED=True`, the frontend shows an additional **"Dev Login"** panel on the login page:

```
┌──────────────────────────────────────────────────────────────┐
│                     DesignPortal Login                        │
│                                                              │
│       ┌──────────────────────────────────┐                   │
│       │  [🔐 Sign in with Azure AD]       │   ← Production   │
│       └──────────────────────────────────┘                   │
│                                                              │
│       ─────────── OR (Dev Only) ──────────                   │
│                                                              │
│       ┌──────────────────────────────────┐                   │
│       │  Quick Login As:                  │                   │
│       │                                   │                   │
│       │  [👑 Admin        ] debug_admin    │                   │
│       │  [👔 GL (PCB)     ] debug_gl_pcb   │                   │
│       │  [👔 GL (HW)      ] debug_gl_hw    │                   │
│       │  [🔧 Tech Mgr     ] debug_tm       │                   │
│       │  [🎨 Design Mgr   ] debug_dm       │                   │
│       │  [👤 User (PCB)   ] debug_user_pcb │                   │
│       │  [👤 User (FW)    ] debug_user_fw  │                   │
│       │  [👤 User (Draw)  ] debug_user_draw│                   │
│       │  [🔩 Mech Lead    ] debug_mech     │                   │
│       │  [🛡 Safety Lead  ] debug_safety   │                   │
│       │                                   │                   │
│       │  ── Manual ──                     │                   │
│       │  Username: [___________________]  │                   │
│       │  Password: [___________________]  │                   │
│       │  [Login]                           │                   │
│       └──────────────────────────────────┘                   │
│                                                              │
│       ⚠ Debug login is for development only                  │
└──────────────────────────────────────────────────────────────┘
```

**API endpoint** for debug login:

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|----------|
| POST | `/api/auth/debug-login/` | Public (dev only) | Accepts `{ username, password }` → returns JWT + user profile. Returns 404 in production. |
| GET | `/api/auth/debug-users/` | Public (dev only) | Returns list of available debug users (username, role, department). Returns 404 in production. |

### 10.1.6  UI Testing Matrix

Use these debug users to verify each role sees the correct UI:

| Test Scenario | Login As | Expected Behavior |
|---------------|----------|--------------------|
| Full admin access | `debug_admin` | All sidebar sections visible; Admin pages accessible; can manage users, groups, teams, routes, form definitions |
| Triage & acceptance | `debug_gl_pcb` | Triage page visible; can accept/reject submitted jobs; can assign work; can close approved jobs |
| GL for different team | `debug_gl_hw` | Same GL features scoped to Mechanical/Hardware group |
| Submit job as standard user | `debug_user_pcb` | Can create jobs/tasks; PeoplePicker search disabled (defaults only); Admin/Manage sections hidden |
| Approval stage 2 (TM) | `debug_tm` | Appears in /approvals when a PCB job reaches stage 2; can approve/reject |
| Approval stage 3 (DM) | `debug_dm` | Appears in /approvals when a PCB job reaches stage 3 |
| Optional approval (Mech Lead) | `debug_approver_mech` | Only appears in /approvals if the route has Mech Lead configured |
| Optional approval (Safety Lead) | `debug_approver_safety` | Only appears in /approvals if the route has Safety Lead configured |
| Cross-team visibility | `debug_user_fw` | Can only see Firmware group items; PCB/HW items hidden |
| Drawing team fields | `debug_user_draw` | Step 3 wizard shows Drawing-specific fields (Drawing Standard, Sheet Size, CAD Tool, etc.) |
| End-to-end approval flow | All users sequentially | Create job as `debug_user_pcb` → accept as `debug_gl_pcb` → mark complete → approve as `debug_gl_pcb` (GL) → approve as `debug_tm` (TM) → approve as `debug_dm` (DM) → close as `debug_gl_pcb` |
| Re-approval after modification | `debug_gl_pcb` + `debug_admin` | Modify a PENDING_CLOSE job → verify RE_APPROVAL_REQUIRED status → re-run approval |
| Due-date reminders | `debug_user_pcb` | Create job with due date = today+3 → run `check_due_dates` → verify notification received |

---

## 11  Step-by-Step Build Instructions

### Phase 1 — Foundation (Backend Core)

| Step | Action | Verification |
|------|--------|-------------|
| 1.1 | Install Python 3.11, PostgreSQL 15, Node 20, Git on Windows 11 | `python --version`, `psql --version`, `node --version` |
| 1.2 | Create Git repo: `git init DesignPortal` | |
| 1.3 | Create backend venv: `cd DesignPortal/backend && python -m venv venv && venv\Scripts\activate` | |
| 1.4 | `pip install django djangorestframework psycopg2-binary python-dotenv whitenoise waitress django-cors-headers mozilla-django-oidc msal django-filter django-simple-history` | `pip freeze > requirements.txt` |
| 1.5 | `django-admin startproject config .` (inside `backend/`) | `python manage.py runserver` works |
| 1.6 | Split settings into `config/base.py`, `config/dev.py`, `config/prod.py`; configure DB, INSTALLED_APPS, REST_FRAMEWORK, CORS, OIDC | Migrations run: `python manage.py migrate` |
| 1.7 | Create Django apps: `python manage.py startapp accounts`, repeat for `design_teams`, `jobs`, `tasks`, `approvals`, `notifications`, `dashboard`, `shared` — move each into `apps/` | Apps appear in `INSTALLED_APPS` |
| 1.8 | Define all models as per Section 5.1 (tables in Section 5.1) | `python manage.py makemigrations && python manage.py migrate` — no errors |
| 1.9 | Register models in `admin.py` for each app | Superuser can browse all models at `/admin/` |
| 1.10 | Create superuser: `python manage.py createsuperuser` | Login at `/admin/` succeeds |
| 1.11 | Seed debug users: `python manage.py seed_debug_users` (see Section 10.1) | 10 debug users created; `python manage.py seed_debug_users --list` shows all |
| 1.12 | Add `DebugAuthBackend` to `config/dev.py` `AUTHENTICATION_BACKENDS` | Login as `debug_admin` / `DebugAdmin!2025` via `/api/auth/debug-login/` succeeds |

### Phase 2 — API Layer

| Step | Action | Verification |
|------|--------|-------------|
| 2.1 | Write serializers for all models (Section 4.1.x) | |
| 2.2 | Write ViewSets with DRF routers for each app | |
| 2.3 | Write custom permission classes: `IsAdmin`, `IsGroupLeaderOrAbove` | |
| 2.4 | Wire URLs: include each app's `urls.py` in `config/urls.py` under `/api/` | |
| 2.5 | Add DRF filter backends for Jobs and Tasks (status, priority, team, date range, group) | |
| 2.6 | Add `@action(detail=True)` for `accept`, `reject`, `submit_for_approval`, `approve`, `close` on Job and Task ViewSets | |
| 2.7 | Test all endpoints with curl / Postman | Each CRUD returns correct status codes |

### Phase 3 — Authentication & Directory

| Step | Action | Verification |
|------|--------|-------------|
| 3.1 | Register app in Azure AD / Okta; set redirect URI to `http://localhost:9091/api/auth/callback/` | |
| 3.2 | Configure `mozilla-django-oidc` (or `django-auth-adfs`) in settings with client ID, secret, authority | |
| 3.3 | Implement custom backend to map AD claims → local User (create/update `aad_object_id`, `role`) | Login via browser redirects, User created locally |
| 3.4 | Register Graph app with `User.ReadBasic.All` + `Mail.Send.Shared` permissions | |
| 3.5 | Implement `GET /api/users/search/` — calls Graph `/v1.0/users?$filter=...`; restrict to Admin/GL | curl returns user results for Admin, 403 for User |
| 3.6 | Implement `GET /api/default-approvers/` — returns approver list from DB | |

### Phase 4 — Approval Workflow

| Step | Action | Verification |
|------|--------|-------------|
| 4.1 | Implement `services.py` in approvals: `create_approval_instance()`, `advance_stage()` | |
| 4.2 | On `POST /api/jobs/{id}/submit-for-approval/` → call `create_approval_instance()` using the job’s `approval_route` | ApprovalInstance created, stage=0 |
| 4.3 | On `POST /api/jobs/{id}/approve/` → call `advance_stage()` | Stage increments or status changes to APPROVED/REJECTED |
| 4.4 | Wire signals: approval decision → notification trigger | Email sent to next approver or requester |
| 4.5 | Test full flow: create job → approval instance created → approve each stage → job status = APPROVED | |

### Phase 5 — File Storage & Notifications

| Step | Action | Verification |
|------|--------|-------------|
| 5.1 | Implement `upload_to_sharepoint()` in `shared/services.py` using Graph `driveItem` endpoints | File appears in SharePoint; Attachment record created |
| 5.2 | Implement `upload_to_local()` fallback for dev | File appears in `media/` |
| 5.3 | Implement `GraphEmailClient` in `notifications/utils.py` | Send test email from `Ticketing_Portal@company.com` |
| 5.4 | Implement signals in jobs/tasks to trigger notifications on status change, approval request, completion | |
| 5.5 | (Optional) Set up Celery + Redis for async email sending | |

### Phase 6 — Frontend Scaffold

| Step | Action | Verification |
|------|--------|-------------|
| 6.1 | `cd frontend && npm create vite@latest . -- --template react-ts` | `npm run dev` opens browser |
| 6.2 | Install: `npm install tailwindcss postcss autoprefixer axios react-router-dom react-hook-form chart.js react-chartjs-2 @azure/msal-browser lucide-react` | |
| 6.3 | Configure Tailwind + PostCSS; add `theme/variables.css` and `theme/glass.css` (Section 8) | Glass styles applied |
| 6.4 | Configure Vite proxy: `/api` → `http://localhost:9091` | API calls from frontend reach Django |
| 6.5 | Build Layout shell: `Header.tsx`, `Footer.tsx`, `Sidebar.tsx` — all with glass-morphism + fixed positioning | Layout renders with fixed header/footer, collapsible sidebar |
| 6.6 | Implement `AuthContext.tsx` with MSAL or Okta SDK | User can sign in; token available in context |
| 6.7 | Implement `ThemeContext.tsx` with `data-theme` toggle | Light/dark mode toggles correctly |
| 6.8 | Implement `RBACGuard.tsx` to wrap protected routes | Admin pages hidden for USER role |

### Phase 7 — Frontend Pages

| Step | Action | Verification |
|------|--------|-------------|
| 7.1 | Build `Dashboard.tsx` with StatusSummaryCards, charts, UpcomingApprovalsTable | Metrics display from `/api/dashboard/metrics/` |
| 7.2 | Build `DataTable.tsx` (reusable) — sortable, paginated, filterable | |
| 7.3 | Build `FilterPanel.tsx` — collapsible side filters | |
| 7.4 | Build `JobsList.tsx` using DataTable + FilterPanel | Lists jobs with all filters |
| 7.5 | Build `FormWizard.tsx` + `FieldRenderer.tsx` | Multi-step form renders from JSON definition |
| 7.6 | Build `PeoplePicker.tsx` with role-based behavior | Standard user sees defaults only; Admin can search |
| 7.7 | Build `EditableTable.tsx` for line items | Add/edit/remove rows inline |
| 7.8 | Build `AttachmentUploader.tsx` with drag-and-drop | Files upload with progress |
| 7.9 | Build `JobNew.tsx` — wire FormWizard for 6-step job creation | Full job creation flow works |
| 7.10 | Build `JobDetail.tsx` with all sub-components (approval stepper, comments, history, attachments) | |
| 7.11 | Build `TasksList.tsx`, `TaskNew.tsx`, `TaskDetail.tsx` — mirrors Jobs | |
| 7.12 | Build `Approvals.tsx` with approval table and modal | Approve/reject works end-to-end |
| 7.13 | Build `Triage.tsx` and `Assignments.tsx` for Group Leaders | |
| 7.14 | Build all Admin pages (7.2.11 – 7.2.15) | Config CRUD works |
| 7.15 | Build `Settings.tsx` for user preferences | Theme and defaults persist |

### Phase 8 — Deployment (Windows 11)

| Step | Action | Verification |
|------|--------|-------------|
| 8.1 | Build frontend: `cd frontend && npm run build` | `dist/` folder created |
| 8.2 | Collect static: `cd backend && python manage.py collectstatic` | Static files in `backend/static/` including frontend build |
| 8.3 | Configure `prod.py`: `ALLOWED_HOSTS`, `STATIC_ROOT`, WhiteNoise middleware, `SECURE_*` settings | |
| 8.4 | Run Waitress: `waitress-serve --listen=0.0.0.0:9091 config.wsgi:application` | Browser at `http://hostname:9091` shows app |
| 8.5 | Install NSSM: `nssm install DesignPortal "C:\path\to\venv\Scripts\waitress-serve.exe" "--listen=0.0.0.0:9091 config.wsgi:application"` | Service starts on boot |
| 8.6 | (Optional) Configure IIS as reverse proxy with URL Rewrite → `http://localhost:9091` with HTTPS certificate | HTTPS works |
| 8.7 | Verify all flows in production mode | |

### Phase 9 — Hardening & QA

| Step | Action | Verification |
|------|--------|-------------|
| 9.1 | Add Django logging config (file + console) | Logs appear in `logs/` folder |
| 9.2 | Add `django-simple-history` to tracked models | History entries created on save |
| 9.3 | Write pytest tests for all ViewSets (permission checks, validation, approval flow) | `pytest` passes |
| 9.4 | Write Cypress E2E tests for critical flows (job creation, approval) | `npx cypress run` passes |
| 9.5 | Security: CSRF, secure cookies, CORS whitelist, rate limiting on search | |
| 9.6 | Performance: add DB indexes on `status`, `design_team_id`, `group_id`, `created_at` | |
| 9.7 | Set up CI pipeline (GitHub Actions): lint → test → build → deploy | Pipeline green |

---

## 12  Key Application Flows (Sequence Diagrams)

### 12.1  Job Creation Flow

```mermaid
sequenceDiagram
    participant U as User Browser
    participant FE as React FormWizard
    participant API as Django API :9091
    participant DB as PostgreSQL
    participant Graph as Microsoft Graph

    U->>FE: Navigate to /jobs/new
    FE->>API: GET /api/form-definitions/?request_type=JOB
    API->>DB: SELECT form_definition
    DB-->>API: FormDefinition JSON
    API-->>FE: Form schema (steps, fields)

    FE->>API: GET /api/design-teams/
    API-->>FE: [PCB, Hardware, Firmware, Drawing]

    U->>FE: Step 1: Fill basic info, select "PCB"
    FE->>API: GET /api/default-approvers/?design_team_id=1&request_type=JOB
    API->>DB: SELECT default_approver WHERE design_team=1
    DB-->>API: approver_ids: [aad_1, aad_2]
    API-->>FE: Default approvers with names

    Note over FE: Step 2: PeoplePicker shows defaults
    alt Admin or GroupLeader
        U->>FE: Type search query
        FE->>API: GET /api/users/search/?q=Jane
        API->>Graph: GET /v1.0/users?$filter=startswith(displayName,'Jane')
        Graph-->>API: Matching users
        API-->>FE: Search results
    end

    U->>FE: Steps 3-5: Custom fields, attachments, line items
    U->>FE: Step 6: Review & Submit

    FE->>API: POST /api/jobs/ { title, metadata, line_items, ... }
    API->>DB: INSERT Job, JobLineItems, Attachments
    API->>DB: Job status = DRAFT (saved) or SUBMITTED (if user clicked Submit)
    alt Status = SUBMITTED
        API->>Graph: Send email to Group Leader (new submission)
    end
    API-->>FE: 201 Created { id: "uuid-..." }

    FE->>U: Redirect to /jobs/uuid-...
```

### 12.2  Approval Decision Flow

```mermaid
sequenceDiagram
    participant GL as Group Leader
    participant FE as React App
    participant API as Django API :9091
    participant DB as PostgreSQL
    participant Graph as Microsoft Graph

    Note over GL,Graph: Phase 1 — Job Acceptance (Triage)
    GL->>FE: Open /manage/triage
    FE->>API: GET /api/jobs/?status=SUBMITTED&group=my-group
    API-->>FE: List of submitted items

    GL->>FE: Click "Accept" on Job #123
    FE->>API: POST /api/jobs/123/accept/ { comment: "Accepted, assign to team" }
    API->>DB: UPDATE job SET status = 'ACCEPTED'
    API->>Graph: Send email to requester (accepted)
    API-->>FE: { status: "ACCEPTED" }

    Note over GL,Graph: Phase 2 — Work Execution
    GL->>FE: Assign job → status moves to IN_PROGRESS
    Note over FE: Assignee works on the job...

    Note over GL,Graph: Phase 3 — Approval Route (after work complete)
    participant A as Assignee
    A->>FE: Mark work complete
    FE->>API: POST /api/jobs/123/submit-for-approval/
    API->>DB: INSERT ApprovalInstance (stage=0, route: GL→TM→DM)
    API->>DB: UPDATE job SET status = 'PENDING_APPROVAL'
    API->>Graph: Send email to GL (first approver)
    API-->>FE: { status: "PENDING_APPROVAL" }

    participant Approver as Current Approver
    Approver->>FE: Open /approvals
    FE->>API: GET /api/approval-instances/?status=PENDING&approver=me
    API-->>FE: List of pending items

    Approver->>FE: Click "Approve" → modal opens
    Approver->>FE: Add comment, click "Approve"
    FE->>API: POST /api/jobs/123/approve/ { decision: "APPROVE", comment: "Looks good" }
    API->>DB: UPDATE approval_instance SET decisions += new_decision
    API->>DB: advance_stage(): current_stage += 1

    alt More stages remain (TM, DM, optional approvers)
        API->>Graph: Send email to next-stage approver
        API-->>FE: { status: "PENDING_APPROVAL", current_stage: 2 }
    else All stages complete
        API->>DB: UPDATE job SET status = 'APPROVED' → 'PENDING_CLOSE'
        API->>Graph: Send email to GL (close the job)
        API->>Graph: Send email to requester (approved)
        API-->>FE: { status: "PENDING_CLOSE" }
    end

    Note over GL,Graph: Phase 4 — Closing
    GL->>FE: Open /manage/triage (Pending Close section)
    alt No modifications detected
        GL->>FE: Click "Close"
        FE->>API: POST /api/jobs/123/close/
        API->>DB: UPDATE job SET status = 'COMPLETED'
        API->>Graph: Notify all stakeholders (completed)
    else Modifications detected before closing
        API->>DB: UPDATE job SET status = 'RE_APPROVAL_REQUIRED'
        API->>DB: INSERT new ApprovalInstance (fresh route)
        API->>Graph: Notify all approvers (re-approval needed)
        Note over FE: Flow returns to Phase 3
    end
```

### 12.3  People Picker Flow

```mermaid
flowchart TD
    Start([PeoplePicker Mounted]) --> FetchDefaults[GET /api/default-approvers/]
    FetchDefaults --> ShowChips[Display default approvers as chips]
    ShowChips --> CheckRole{User Role?}

    CheckRole -->|USER| LockSearch[Search input disabled]
    LockSearch --> SelectFromDefaults[User selects/deselects from defaults]

    CheckRole -->|ADMIN or GROUP_LEADER| EnableSearch[Search input enabled]
    EnableSearch --> TypeQuery[User types search query]
    TypeQuery --> Debounce[Debounce 300ms]
    Debounce --> CallAPI[GET /api/users/search/?q=...]
    CallAPI --> ShowSuggestions[Show dropdown with results]
    ShowSuggestions --> SelectUser[User clicks to add]

    SelectFromDefaults --> StoreIDs[Store selected aad_object_ids in form state]
    SelectUser --> StoreIDs
    StoreIDs --> OnSubmit[Include in POST payload as metadata.approver_ids]
```

---

## 13  FormDefinition JSON Schema Reference

This is the structure of the `definition` field in the `form_definition` table. Use this as a contract between backend and frontend.

```jsonc
{
  "request_type": "JOB",
  "version": 1,
  "steps": [
    {
      "step": 1,
      "title": "Basic Information",
      "description": "Provide core details for your request",
      "fields": [
        {
          "name": "title",
          "label": "Job Title",
          "type": "text",           // text | textarea | number | date | select | multi-select | checkbox | file | people-picker | editable-table
          "required": true,
          "maxLength": 200,
          "helpText": "A short, descriptive title for the job"
        },
        {
          "name": "description",
          "label": "Description",
          "type": "textarea",
          "required": false,
          "maxLength": 5000
        },
        {
          "name": "request_type",
          "label": "Request Type",
          "type": "select",
          "required": true,
          "options": [
            { "value": "NEW_DESIGN", "label": "New Design" },
            { "value": "MODIFICATION", "label": "Modification" },
            { "value": "REVIEW", "label": "Review" },
            { "value": "OTHER", "label": "Other" }
          ]
        },
        {
          "name": "design_team_id",
          "label": "Design Team",
          "type": "select",
          "required": true,
          "dataSource": "/api/design-teams/",  // dynamic options from API
          "displayField": "name",
          "valueField": "id"
        },
        {
          "name": "priority",
          "label": "Priority",
          "type": "select",
          "required": true,
          "options": [
            { "value": "LOW", "label": "Low" },
            { "value": "MEDIUM", "label": "Medium" },
            { "value": "HIGH", "label": "High" },
            { "value": "CRITICAL", "label": "Critical" }
          ]
        },
        {
          "name": "due_date",
          "label": "Due Date",
          "type": "date",
          "required": false
        }
      ]
    },
    {
      "step": 2,
      "title": "Stakeholders & Approval",
      "fields": [
        {
          "name": "approvers",
          "label": "Approvers",
          "type": "people-picker",
          "required": true,
          "minSelections": 1,
          "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&request_type=JOB",
          "searchEndpoint": "/api/users/search/",
          "restrictSearchToRoles": ["ADMIN", "GROUP_LEADER"]
        },
        {
          "name": "watchers",
          "label": "Watchers",
          "type": "people-picker",
          "required": false
        },
        {
          "name": "use_default_route",
          "label": "Use Default Approval Route",
          "type": "checkbox",
          "defaultValue": true,
          "helpText": "Uncheck to select a custom approval route (Admin/Group Leader only)"
        }
      ]
    },
    {
      "step": 3,
      "title": "Design-Team Specific Fields",
      "description": "Fields below depend on selected design team",
      "dynamicSource": "design_team.form_definition",
      "fields": []  // merged at runtime from DesignTeam.form_definition
    },
    {
      "step": 4,
      "title": "Attachments & Artifacts",
      "fields": [
        {
          "name": "attachments",
          "label": "Upload Files",
          "type": "file",
          "required": false,
          "multiple": true,
          "acceptedTypes": [".pdf", ".docx", ".xlsx", ".png", ".jpg", ".zip", ".dwg", ".brd", ".sch", ".step"]
        },
        {
          "name": "artifact_folder",
          "label": "Network / SharePoint Folder Path",
          "type": "text",
          "required": false,
          "helpText": "Optional path to existing artifacts"
        }
      ]
    },
    {
      "step": 5,
      "title": "Line Items",
      "fields": [
        {
          "name": "line_items",
          "label": "Item Details",
          "type": "editable-table",
          "required": false,
          "columns": [
            { "name": "part_number", "label": "Part Number", "type": "text" },
            { "name": "description", "label": "Description", "type": "text" },
            { "name": "quantity", "label": "Qty", "type": "number", "min": 1 },
            { "name": "unit", "label": "Unit", "type": "select", "options": ["pcs", "kg", "m", "set"] },
            { "name": "supplier", "label": "Supplier", "type": "text" },
            { "name": "notes", "label": "Notes", "type": "text" }
          ]
        }
      ]
    },
    {
      "step": 6,
      "title": "Review & Submit",
      "isReview": true,
      "fields": []  // read-only summary of all previous steps
    }
  ]
}
```

---

## 14  Design-Team-Specific Field Definitions

Each `DesignTeam.form_definition` JSON provides fields merged into Step 3 of the wizard. All teams share a common set of **management & tracking fields** (Group Leader, Technical Manager, Design Manager, optional approvers, Due Date, Priority, Status, Progress, Attachments). The **technical fields** differ per team.

### 14.0  Common Fields (All Teams)

These fields appear on every group's page in addition to team-specific technical fields:

> **Note:** `due_date` and `priority` below mirror the values from Step 1 of the wizard. When rendered in Step 3 (team-specific view), they are **read-only displays** of the Step 1 values — not duplicate inputs. `status` is always read-only and driven by the state machine.

| Field Name | Label | Type | Required | Options / Notes |
|------------|-------|------|----------|----------------|
| `group_leader` | Group Leader | people-picker | Yes | Default from team config; auto-populated |
| `technical_manager` | Technical Manager | people-picker | Yes | Default from team config; auto-populated |
| `design_manager` | Design Manager | people-picker | Yes | Default from team config; auto-populated |
| `optional_mechanical_lead` | Mechanical Lead (Optional) | people-picker | No | Optional approver — appears only if configured for the design team |
| `optional_safety_lead` | Safety Lead (Optional) | people-picker | No | Optional approver |
| `optional_project_manager` | Project Manager (Optional) | people-picker | No | Optional approver |
| `due_date` | Due Date | date | Yes | Calendar picker; feeds due-date monitoring worker |
| `priority` | Priority | select | Yes | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `status` | Status | select (read-only on form) | Auto | Mirrors job/task state machine status; displayed as badge |
| `progress` | Progress (%) | number (slider or input) | No | 0–100; shown as progress bar on detail page |
| `attachments` | Attached Files | file (multi-upload) | No | Methods: **Drag & Drop**, **Browse**, **SharePoint Link/Select** |
| `attachment_location` | Location of Attachment | select | Conditional (if files attached) | `LOCAL_UPLOAD`, `SHAREPOINT`, `NETWORK_SHARE`; indicates where file is stored |

### 14.1  PCB Team

```jsonc
{
  "fields": [
    // ── Technical Fields ──
    { "name": "model_name", "label": "Model Name", "type": "text", "required": true, "helpText": "Product or model this PCB belongs to" },
    { "name": "design_stage", "label": "Design Stage", "type": "select", "required": true, "options": ["Concept", "Schematic", "Layout", "Prototype", "Pre-Production", "Production"] },
    { "name": "board_name", "label": "Board Name", "type": "text", "required": true, "helpText": "Unique name for this PCB board" },
    { "name": "pcb_type", "label": "PCB Type", "type": "select", "required": true, "options": ["Single-Sided", "Double-Sided", "Multi-Layer", "Rigid", "Flex", "Rigid-Flex", "HDI", "Metal-Core"] },
    { "name": "layer_type", "label": "Layer Type", "type": "select", "required": true, "options": ["1-Layer", "2-Layer", "4-Layer", "6-Layer", "8-Layer", "10-Layer", "12-Layer", "Custom"], "helpText": "Number and configuration of PCB layers" },
    { "name": "layer_count", "label": "Layer Count", "type": "number", "required": true, "min": 1, "max": 32 },
    { "name": "pcb_material", "label": "PCB Material", "type": "select", "required": true, "options": ["FR-4", "Rogers", "Aluminum", "Ceramic", "Polyimide", "Teflon/PTFE", "CEM-1", "CEM-3"] },
    { "name": "board_dimensions", "label": "Board Dimensions (mm)", "type": "text", "required": true, "helpText": "W x H" },
    { "name": "manufacturing_location", "label": "Manufacturing Location", "type": "select", "required": true, "options": ["Internal", "External - Domestic", "External - International"], "helpText": "Where the PCB will be manufactured" },
    { "name": "impedance_control", "label": "Impedance Control Required", "type": "checkbox", "defaultValue": false },
    { "name": "stackup_type", "label": "Stack-up Type", "type": "select", "options": ["Standard", "HDI", "Rigid-Flex", "Flex"], "required": true },
    { "name": "finish", "label": "Surface Finish", "type": "select", "options": ["HASL", "ENIG", "OSP", "Immersion Silver", "Immersion Tin"], "required": false },

    // ── Management & Tracking Fields (common) ──
    { "name": "group_leader", "label": "Group Leader", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=GROUP_LEADER" },
    { "name": "technical_manager", "label": "Technical Manager", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=TECHNICAL_MANAGER" },
    { "name": "design_manager", "label": "Design Manager", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=DESIGN_MANAGER" },
    { "name": "optional_mechanical_lead", "label": "Mechanical Lead (Optional)", "type": "people-picker", "required": false },
    { "name": "optional_safety_lead", "label": "Safety Lead (Optional)", "type": "people-picker", "required": false },
    { "name": "optional_project_manager", "label": "Project Manager (Optional)", "type": "people-picker", "required": false },
    { "name": "due_date", "label": "Due Date", "type": "date", "required": true },
    { "name": "priority", "label": "Priority", "type": "select", "required": true, "options": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
    { "name": "progress", "label": "Progress (%)", "type": "number", "required": false, "min": 0, "max": 100, "helpText": "Percentage of work completed" },
    { "name": "attachments", "label": "Attached Files", "type": "file", "required": false, "multiple": true, "uploadMethods": ["drag-drop", "browse", "sharepoint-select"], "acceptedTypes": [".pdf", ".brd", ".sch", ".zip", ".step", ".gerber", ".dxf"] },
    { "name": "attachment_location", "label": "Location of Attachment", "type": "select", "required": false, "options": ["LOCAL_UPLOAD", "SHAREPOINT", "NETWORK_SHARE"], "conditionalDisplay": { "dependsOn": "attachments", "condition": "hasValue" } }
  ]
}
```

### 14.2  Hardware Team

```jsonc
{
  "fields": [
    // ── Technical Fields ──
    { "name": "model_name", "label": "Model Name", "type": "text", "required": true, "helpText": "Product or model this hardware design belongs to" },
    { "name": "design_stage", "label": "Design Stage", "type": "select", "required": true, "options": ["Concept", "Preliminary Design", "Detailed Design", "Prototype", "Testing", "Production"] },
    { "name": "assembly_name", "label": "Assembly Name", "type": "text", "required": true, "helpText": "Unique name for this hardware assembly" },
    { "name": "enclosure_type", "label": "Enclosure Type", "type": "select", "options": ["Desktop", "Rack-mount", "IP67 Sealed", "Custom", "N/A"], "required": true },
    { "name": "power_supply_spec", "label": "Power Supply Specification", "type": "text", "required": true },
    { "name": "thermal_requirements", "label": "Thermal Requirements", "type": "textarea", "required": false },
    { "name": "input_voltage", "label": "Input Voltage Range", "type": "text", "required": true, "helpText": "e.g. 12-48VDC" },
    { "name": "operating_temp", "label": "Operating Temperature Range", "type": "text", "required": false, "helpText": "e.g. -20°C to +70°C" },
    { "name": "manufacturing_location", "label": "Manufacturing Location", "type": "select", "required": true, "options": ["Internal", "External - Domestic", "External - International"] },

    // ── Management & Tracking Fields (common) ──
    { "name": "group_leader", "label": "Group Leader", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=GROUP_LEADER" },
    { "name": "technical_manager", "label": "Technical Manager", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=TECHNICAL_MANAGER" },
    { "name": "design_manager", "label": "Design Manager", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=DESIGN_MANAGER" },
    { "name": "optional_mechanical_lead", "label": "Mechanical Lead (Optional)", "type": "people-picker", "required": false },
    { "name": "optional_safety_lead", "label": "Safety Lead (Optional)", "type": "people-picker", "required": false },
    { "name": "optional_project_manager", "label": "Project Manager (Optional)", "type": "people-picker", "required": false },
    { "name": "due_date", "label": "Due Date", "type": "date", "required": true },
    { "name": "priority", "label": "Priority", "type": "select", "required": true, "options": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
    { "name": "progress", "label": "Progress (%)", "type": "number", "required": false, "min": 0, "max": 100 },
    { "name": "attachments", "label": "Attached Files", "type": "file", "required": false, "multiple": true, "uploadMethods": ["drag-drop", "browse", "sharepoint-select"], "acceptedTypes": [".pdf", ".docx", ".xlsx", ".step", ".stp", ".iges", ".zip"] },
    { "name": "attachment_location", "label": "Location of Attachment", "type": "select", "required": false, "options": ["LOCAL_UPLOAD", "SHAREPOINT", "NETWORK_SHARE"], "conditionalDisplay": { "dependsOn": "attachments", "condition": "hasValue" } }
  ]
}
```

### 14.3  Firmware Team

```jsonc
{
  "fields": [
    // ── Technical Fields ──
    { "name": "model_name", "label": "Model Name", "type": "text", "required": true, "helpText": "Product or model this firmware targets" },
    { "name": "design_stage", "label": "Design Stage", "type": "select", "required": true, "options": ["Requirements", "Architecture", "Development", "Integration Testing", "Validation", "Release"] },
    { "name": "firmware_name", "label": "Firmware Module Name", "type": "text", "required": true, "helpText": "Unique name for this firmware component" },
    { "name": "mcu_type", "label": "MCU Type", "type": "select", "options": ["STM32", "ESP32", "nRF52", "Renesas", "TI MSP430", "Other"], "required": true },
    { "name": "rtos", "label": "RTOS", "type": "select", "options": ["FreeRTOS", "Zephyr", "Bare Metal", "Linux", "Other"], "required": true },
    { "name": "code_repo_url", "label": "Code Repository URL", "type": "text", "required": false, "helpText": "Link to Git repository" },
    { "name": "flash_size_kb", "label": "Flash Size (KB)", "type": "number", "required": false },
    { "name": "ram_size_kb", "label": "RAM Size (KB)", "type": "number", "required": false },
    { "name": "comm_protocols", "label": "Communication Protocols", "type": "multi-select", "options": ["UART", "SPI", "I2C", "CAN", "Ethernet", "BLE", "WiFi", "USB"], "required": false },
    { "name": "manufacturing_location", "label": "Build/Flash Location", "type": "select", "required": true, "options": ["Internal Lab", "External - Domestic", "External - International"] },

    // ── Management & Tracking Fields (common) ──
    { "name": "group_leader", "label": "Group Leader", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=GROUP_LEADER" },
    { "name": "technical_manager", "label": "Technical Manager", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=TECHNICAL_MANAGER" },
    { "name": "design_manager", "label": "Design Manager", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=DESIGN_MANAGER" },
    { "name": "optional_mechanical_lead", "label": "Mechanical Lead (Optional)", "type": "people-picker", "required": false },
    { "name": "optional_safety_lead", "label": "Safety Lead (Optional)", "type": "people-picker", "required": false },
    { "name": "optional_project_manager", "label": "Project Manager (Optional)", "type": "people-picker", "required": false },
    { "name": "due_date", "label": "Due Date", "type": "date", "required": true },
    { "name": "priority", "label": "Priority", "type": "select", "required": true, "options": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
    { "name": "progress", "label": "Progress (%)", "type": "number", "required": false, "min": 0, "max": 100 },
    { "name": "attachments", "label": "Attached Files", "type": "file", "required": false, "multiple": true, "uploadMethods": ["drag-drop", "browse", "sharepoint-select"], "acceptedTypes": [".bin", ".hex", ".elf", ".c", ".h", ".zip", ".pdf"] },
    { "name": "attachment_location", "label": "Location of Attachment", "type": "select", "required": false, "options": ["LOCAL_UPLOAD", "SHAREPOINT", "NETWORK_SHARE"], "conditionalDisplay": { "dependsOn": "attachments", "condition": "hasValue" } }
  ]
}
```

### 14.4  Drawing Team

```jsonc
{
  "fields": [
    // ── Technical Fields ──
    { "name": "model_name", "label": "Model Name", "type": "text", "required": true, "helpText": "Product or model this drawing documents" },
    { "name": "design_stage", "label": "Design Stage", "type": "select", "required": true, "options": ["Concept Sketch", "Preliminary", "Detail Drawing", "Assembly Drawing", "As-Built", "Release"] },
    { "name": "drawing_name", "label": "Drawing Name", "type": "text", "required": true, "helpText": "Unique name or number for this drawing" },
    { "name": "drawing_standard", "label": "Drawing Standard", "type": "select", "options": ["ASME Y14.5", "ISO 8015", "Company Standard", "Other"], "required": true },
    { "name": "sheet_size", "label": "Sheet Size", "type": "select", "options": ["A4", "A3", "A2", "A1", "A0", "ANSI A", "ANSI B", "ANSI C", "ANSI D"], "required": true },
    { "name": "revision_level", "label": "Revision Level", "type": "text", "required": true, "helpText": "e.g. Rev A, Rev 1.0" },
    { "name": "cad_tool", "label": "CAD Tool", "type": "select", "options": ["SolidWorks", "AutoCAD", "Creo", "Inventor", "Fusion 360", "Other"], "required": true },
    { "name": "tolerance_class", "label": "General Tolerance Class", "type": "select", "options": ["Fine", "Medium", "Coarse", "Very Coarse"], "required": false },
    { "name": "manufacturing_location", "label": "Manufacturing Location", "type": "select", "required": true, "options": ["Internal", "External - Domestic", "External - International"] },

    // ── Management & Tracking Fields (common) ──
    { "name": "group_leader", "label": "Group Leader", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=GROUP_LEADER" },
    { "name": "technical_manager", "label": "Technical Manager", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=TECHNICAL_MANAGER" },
    { "name": "design_manager", "label": "Design Manager", "type": "people-picker", "required": true, "defaultSource": "/api/default-approvers/?design_team_id={design_team_id}&role=DESIGN_MANAGER" },
    { "name": "optional_mechanical_lead", "label": "Mechanical Lead (Optional)", "type": "people-picker", "required": false },
    { "name": "optional_safety_lead", "label": "Safety Lead (Optional)", "type": "people-picker", "required": false },
    { "name": "optional_project_manager", "label": "Project Manager (Optional)", "type": "people-picker", "required": false },
    { "name": "due_date", "label": "Due Date", "type": "date", "required": true },
    { "name": "priority", "label": "Priority", "type": "select", "required": true, "options": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
    { "name": "progress", "label": "Progress (%)", "type": "number", "required": false, "min": 0, "max": 100 },
    { "name": "attachments", "label": "Attached Files", "type": "file", "required": false, "multiple": true, "uploadMethods": ["drag-drop", "browse", "sharepoint-select"], "acceptedTypes": [".pdf", ".dwg", ".dxf", ".step", ".stp", ".iges", ".zip"] },
    { "name": "attachment_location", "label": "Location of Attachment", "type": "select", "required": false, "options": ["LOCAL_UPLOAD", "SHAREPOINT", "NETWORK_SHARE"], "conditionalDisplay": { "dependsOn": "attachments", "condition": "hasValue" } }
  ]
}
```

---

## 15  ApprovalRoute JSON Schema Reference

The `route` column in `approval_route` stores an ordered array of approval steps. This route is triggered **after work is completed** (status moves from `IN_PROGRESS` → `PENDING_APPROVAL`), **not** at initial submission.

> **Important:** The initial submission goes to the Group Leader for **acceptance** (triage), which is a separate step from the approval route. The approval route below runs only after the assignee marks work as complete.

```jsonc
{
  "route": [
    {
      "step": 1,
      "name": "Group Leader Review",
      "type": "role",                    // "role" or "specific_users"
      "role": "GROUP_LEADER",            // when type=role
      "user_ids": [],                    // when type=specific_users → ["aad_id_1", "aad_id_2"]
      "require_all": false,              // false = any one can approve; true = all must approve
      "auto_skip_if_requester": false,
      "auto_skip_if_assignee": true      // skip if the assignee is the GL (avoid self-approval)
    },
    {
      "step": 2,
      "name": "Technical Manager Approval",
      "type": "role",
      "role": "TECHNICAL_MANAGER",
      "user_ids": [],
      "require_all": false,
      "auto_skip_if_requester": false,
      "auto_skip_if_assignee": false
    },
    {
      "step": 3,
      "name": "Design Manager Final Approval",
      "type": "role",
      "role": "DESIGN_MANAGER",
      "user_ids": [],
      "require_all": false,
      "auto_skip_if_requester": false,
      "auto_skip_if_assignee": false
    },
    {
      "step": 4,
      "name": "Mechanical Lead (Optional)",
      "type": "specific_users",
      "role": null,
      "user_ids": [],                    // populated from DefaultApprover config if enabled
      "require_all": false,
      "auto_skip_if_requester": false,
      "auto_skip_if_assignee": false,
      "optional": true                   // step is skipped if user_ids is empty
    },
    {
      "step": 5,
      "name": "Safety Lead (Optional)",
      "type": "specific_users",
      "role": null,
      "user_ids": [],
      "require_all": false,
      "auto_skip_if_requester": false,
      "auto_skip_if_assignee": false,
      "optional": true
    },
    {
      "step": 6,
      "name": "Project Manager (Optional)",
      "type": "specific_users",
      "role": null,
      "user_ids": [],
      "require_all": false,
      "auto_skip_if_requester": false,
      "auto_skip_if_assignee": false,
      "optional": true
    }
  ]
}
```

### 15.1  Route Lifecycle

| Phase | Trigger | What Happens |
|-------|---------|-------------|
| **Creation** | `IN_PROGRESS` → `PENDING_APPROVAL` | System creates `ApprovalInstance` with `current_stage=0`; populates approver list from `DefaultApprover` config + route template |
| **Advance** | Approver at current stage approves | `current_stage += 1`; if optional step has empty `user_ids`, auto-skip to next |
| **Complete** | All required stages approved | Status → `APPROVED` → `PENDING_CLOSE`; GL notified for closure |
| **Reject** | Any approver rejects | Status → `APPROVAL_REJECTED` → returns to `IN_PROGRESS` for rework |
| **Re-approval** | Modification during `PENDING_CLOSE` | New `ApprovalInstance` created from same route; old one archived |

---

## 16  Due-Date Monitoring Worker

A background worker that monitors due dates on all active jobs and tasks, sending reminder notifications when deadlines approach and escalations when they are breached.

### 16.1  Architecture

| Component | Technology | Description |
|-----------|-----------|-------------|
| **Worker Process** | Celery Beat (preferred) **or** Django management command + Windows Task Scheduler | Periodic scheduler that triggers the due-date check |
| **Task Queue** | Celery + Redis | Async task execution (optional — can run synchronously via management command) |
| **Notification Dispatch** | `notifications/utils.py` → Microsoft Graph `Mail.Send.Shared` | Sends emails via shared mailbox |
| **Database Queries** | Django ORM | Queries jobs/tasks with `status NOT IN ('COMPLETED', 'DRAFT')` and `due_date IS NOT NULL` |

### 16.2  Worker Flow

```mermaid
flowchart TD
    Start([Scheduled Trigger<br>Every 1 hour]) --> Query[Query active Jobs & Tasks<br>WHERE status NOT IN COMPLETED, DRAFT<br>AND due_date IS NOT NULL]
    Query --> Loop{For each item}

    Loop --> CalcDays[Calculate days_remaining =<br>due_date − today]

    CalcDays --> Check7{days_remaining<br>≤ 7 AND > 3?}
    Check7 -->|Yes| Remind7[Send 7-day reminder<br>to Assignee + GL]
    Check7 -->|No| Check3{days_remaining<br>≤ 3 AND > 1?}

    Check3 -->|Yes| Remind3[Send 3-day urgent reminder<br>to Assignee + GL + TM]
    Check3 -->|No| Check1{days_remaining<br>≤ 1 AND > 0?}

    Check1 -->|Yes| Remind1[Send 1-day final warning<br>to Assignee + GL + TM + DM]
    Check1 -->|No| CheckOverdue{days_remaining<br>≤ 0?}

    CheckOverdue -->|Yes| Escalate[Send OVERDUE escalation<br>to Assignee + GL + TM + DM + Admin]
    CheckOverdue -->|No| Skip[No action needed]

    Remind7 --> LogHistory[Log reminder in history_entry<br>action = DUE_DATE_REMINDER]
    Remind3 --> LogHistory
    Remind1 --> LogHistory
    Escalate --> LogHistory
    Skip --> NextItem[Next item]
    LogHistory --> DedupCheck{Already sent this<br>reminder level today?}
    DedupCheck -->|Yes| NextItem
    DedupCheck -->|No| SendEmail[Dispatch email via Graph]
    SendEmail --> RecordSent[Mark reminder as sent<br>in metadata.reminders_sent]
    RecordSent --> NextItem
    NextItem --> Loop
```

### 16.3  Reminder Schedule

| Days Before Due | Reminder Level | Recipients | Email Template | Frequency |
|----------------|----------------|------------|----------------|-----------|
| 7 days | `REMINDER_7DAY` | Assignee, Group Leader | `due_date_reminder.html` | Once |
| 3 days | `REMINDER_3DAY` | Assignee, GL, Technical Manager | `due_date_urgent.html` | Once |
| 1 day | `REMINDER_1DAY` | Assignee, GL, TM, Design Manager | `due_date_final.html` | Once |
| 0 days (due today) | `DUE_TODAY` | Assignee, GL, TM, DM | `due_date_today.html` | Once |
| Overdue (< 0) | `OVERDUE` | Assignee, GL, TM, DM, Admin | `due_date_overdue.html` | Daily until resolved |

### 16.4  Implementation Details

#### Backend File: `apps/notifications/workers.py`

```python
# Celery Beat schedule (in config/base.py → CELERY_BEAT_SCHEDULE)
CELERY_BEAT_SCHEDULE = {
    'check-due-dates': {
        'task': 'apps.notifications.tasks.check_due_dates',
        'schedule': crontab(minute=0, hour='*/1'),  # Every hour
    },
}
```

#### Alternative: Django Management Command

```bash
# For environments without Celery/Redis:
python manage.py check_due_dates
# Schedule via Windows Task Scheduler to run hourly
```

#### Deduplication Strategy

The worker stores sent reminders in the job/task `metadata` JSONB field:

```jsonc
{
  "reminders_sent": {
    "REMINDER_7DAY": "2025-01-15T08:00:00Z",
    "REMINDER_3DAY": "2025-01-19T08:00:00Z",
    "OVERDUE": ["2025-01-23T08:00:00Z", "2025-01-24T08:00:00Z"]
  }
}
```

### 16.5  Project Structure Additions

```
backend/apps/notifications/
├── workers.py              # Due-date check logic
├── tasks.py                # Celery task wrappers (existing — add check_due_dates)
├── management/
│   └── commands/
│       └── check_due_dates.py   # Management command alternative
└── templates/
    ├── due_date_reminder.html
    ├── due_date_urgent.html
    ├── due_date_final.html
    ├── due_date_today.html
    └── due_date_overdue.html
```

### 16.6  Environment Variables Additions

```env
# ── Due-Date Worker ──
DUE_DATE_CHECK_INTERVAL_HOURS=1
DUE_DATE_REMINDER_DAYS=7,3,1,0
DUE_DATE_OVERDUE_REPEAT_HOURS=24
```

---

## 17  Notification Handling Map

Comprehensive map of all notification triggers, channels, recipients, and templates across the application.

### 17.1  Notification Flow Diagram

```mermaid
flowchart TD
    subgraph Triggers["Notification Triggers"]
        T1[Job/Task Submitted]
        T2[Job/Task Accepted by GL]
        T3[Job/Task Rejected by GL]
        T4[Status Change]
        T5[Approval Requested]
        T6[Approval Decision Made]
        T7[All Approvals Complete]
        T8[Approval Rejected]
        T9[Due Date Reminder]
        T10[Due Date Overdue]
        T11[Comment Added]
        T12[Attachment Uploaded]
        T13[Assignment Change]
        T14[Modification During PendingClose]
        T15[Job/Task Closed / Completed]
        T16[Re-Approval Triggered]
    end

    subgraph Dispatch["Notification Dispatcher"]
        D1[Django Signal Handler<br>apps/notifications/signals.py]
        D2[Due-Date Worker<br>apps/notifications/workers.py]
    end

    subgraph Channel["Delivery Channels"]
        C1[Email via Microsoft Graph<br>Mail.Send.Shared]
        C2[In-App Notification<br>Bell icon badge]
        C3[Optional: WebSocket<br>Real-time toast]
    end

    T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 & T11 & T12 & T13 & T14 & T15 & T16 --> D1
    T9 & T10 --> D2
    D1 --> C1
    D1 --> C2
    D1 -.-> C3
    D2 --> C1
    D2 --> C2
```

### 17.2  Notification Event Map

| # | Event | Trigger Point | Recipients | Email Template | In-App | Priority |
|---|-------|--------------|------------|----------------|--------|----------|
| N1 | **Job/Task Submitted** | `POST /api/jobs/` → signal `post_save` | Group Leader of owning group | `submission_new.html` | Yes | Normal |
| N2 | **Accepted by GL** | `POST /api/jobs/{id}/accept/` | Requester, Watchers | `accepted.html` | Yes | Normal |
| N3 | **Rejected by GL** | `POST /api/jobs/{id}/reject/` | Requester | `rejected.html` | Yes | High |
| N4 | **Status Change** | Any status transition | Requester, Assignee, Watchers | `status_change.html` | Yes | Normal |
| N5 | **Approval Requested** | Transition to `PENDING_APPROVAL` or stage advance | Next approver in route | `approval_request.html` | Yes | High |
| N6 | **Approval Decision (Approve)** | `POST /api/jobs/{id}/approve/` decision=APPROVE | Requester, next approver (if exists) | `approval_decision.html` | Yes | Normal |
| N7 | **Approval Decision (Reject)** | `POST /api/jobs/{id}/approve/` decision=REJECT | Requester, Assignee, GL | `approval_rejected.html` | Yes | High |
| N8 | **All Approvals Complete** | Final stage approved | Requester, Assignee, GL, all Watchers | `fully_approved.html` | Yes | High |
| N9 | **Due Date — 7 day** | Worker check | Assignee, GL | `due_date_reminder.html` | Yes | Normal |
| N10 | **Due Date — 3 day** | Worker check | Assignee, GL, TM | `due_date_urgent.html` | Yes | High |
| N11 | **Due Date — 1 day** | Worker check | Assignee, GL, TM, DM | `due_date_final.html` | Yes | Critical |
| N12 | **Due Date — Overdue** | Worker check (daily repeat) | Assignee, GL, TM, DM, Admin | `due_date_overdue.html` | Yes | Critical |
| N13 | **Comment Added** | `POST /api/jobs/{id}/comments/` | Requester, Assignee, Watchers (excluding author) | `comment_added.html` | Yes | Low |
| N14 | **Attachment Uploaded** | `POST /api/jobs/{id}/attachments/` | Requester, Assignee, Watchers (excluding uploader) | `attachment_added.html` | Yes | Low |
| N15 | **Assignment Change** | `PUT /api/jobs/{id}/` with new assignee | New Assignee, Previous Assignee, GL | `assignment_change.html` | Yes | Normal |
| N16 | **Modified During PendingClose** | System detects field changes on `PENDING_CLOSE` item | GL, Requester, all Approvers | `modification_detected.html` | Yes | High |
| N17 | **Job/Task Completed** | GL closes → `COMPLETED` | Requester, Assignee, all Watchers, all Approvers | `completed.html` | Yes | Normal |
| N18 | **Re-Approval Triggered** | `RE_APPROVAL_REQUIRED` → `PENDING_APPROVAL` | All approvers in route, Requester, Assignee | `reapproval_required.html` | Yes | High |

### 17.3  In-App Notification Model

Add to `apps/notifications/`:

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `recipient_id` | FK → User | Who receives this notification |
| `event_type` | Varchar(50) | e.g. `APPROVAL_REQUESTED`, `DUE_DATE_REMINDER` |
| `title` | Varchar(200) | Short display title |
| `body` | Text | Detail message |
| `link` | Varchar(500) | Frontend URL to navigate to (e.g. `/jobs/{id}`) |
| `is_read` | Boolean | Default `false` |
| `created_at` | Timestamp | Auto |

#### API Endpoints

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|---------|
| GET | `/api/notifications/` | Authenticated | List current user's notifications (paginated, filterable by `is_read`) |
| GET | `/api/notifications/unread-count/` | Authenticated | Returns `{ count: N }` for badge display |
| POST | `/api/notifications/{id}/read/` | Authenticated | Mark single notification as read |
| POST | `/api/notifications/read-all/` | Authenticated | Mark all as read |

### 17.4  Email Template Structure

All email templates extend a common base layout:

```
┌──────────────────────────────────────┐
│  DesignPortal                   Logo │
├──────────────────────────────────────┤
│                                      │
│  {{ notification_title }}            │
│                                      │
│  {{ event_description }}             │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ Item:    {{ job_title }}       │  │
│  │ Status:  {{ new_status }}      │  │
│  │ Team:    {{ design_team }}     │  │
│  │ Due:     {{ due_date }}        │  │
│  │ By:      {{ actor_name }}      │  │
│  └────────────────────────────────┘  │
│                                      │
│  [ View in DesignPortal ]  (button)  │
│                                      │
├──────────────────────────────────────┤
│  © DesignPortal • Do not reply       │
└──────────────────────────────────────┘
```

---

## 18  Reference Mapping & Cross-Referencing

Jobs and tasks can be cross-referenced to establish traceability between related work items.

### 18.1  Reference Types

| Reference Type | Direction | Description | Example |
|---------------|-----------|-------------|---------|
| `PARENT_CHILD` | Parent → Child | Job has child tasks | Job #100 → Task #201, #202 |
| `RELATED` | Bidirectional | Items are related but independent | Job #100 ↔ Job #105 (same product) |
| `BLOCKS` | A blocks B | Item A must complete before B can start | Task #201 blocks Task #300 |
| `BLOCKED_BY` | A is blocked by B | Inverse of BLOCKS | Task #300 blocked by Task #201 |
| `DUPLICATE` | Bidirectional | Items duplicate each other | Job #100 ↔ Job #110 |
| `SUPERSEDES` | A replaces B | New item supersedes an old one | Job #120 supersedes Job #100 |

### 18.2  Database Model — `job_reference`

Add to `apps/shared/models.py`:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, auto | |
| `source_job_id` | UUID | FK → Job, Nullable | Source job (mutually exclusive with source_task_id) |
| `source_task_id` | UUID | FK → Task, Nullable | Source task |
| `target_job_id` | UUID | FK → Job, Nullable | Target job (mutually exclusive with target_task_id) |
| `target_task_id` | UUID | FK → Task, Nullable | Target task |
| `reference_type` | Varchar(20) | Not Null | One of the types in 18.1 |
| `notes` | Text | Nullable | Optional description of the relationship |
| `created_by` | Integer | FK → User | Who created the reference |
| `created_at` | Timestamp | Auto | |

**Constraint:** At least one source (`source_job_id` or `source_task_id`) and one target (`target_job_id` or `target_task_id`) must be non-null.

### 18.3  API Endpoints

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|---------|
| GET | `/api/jobs/{id}/references/` | Authenticated | List all references for a job (both directions) |
| POST | `/api/jobs/{id}/references/` | Authenticated | Create a new reference |
| DELETE | `/api/references/{ref_id}/` | Owner/Admin | Remove a reference |
| GET | `/api/tasks/{id}/references/` | Authenticated | List all references for a task |
| POST | `/api/tasks/{id}/references/` | Authenticated | Create a new reference |

### 18.4  Frontend — Reference Mapping Component

Added to Job Detail and Task Detail pages:

| Component / Element | Description |
|---------------------|-------------|
| **ReferencesSection** | Collapsible section on detail page showing all linked items |
| **ReferenceTable** | Table with columns: Type (badge), Direction (→/←/↔), Linked Item (clickable link), Status (badge), Created By, Date, Actions (remove) |
| **AddReferenceModal** | Modal dialog: (1) Select reference type from dropdown, (2) Search for target job/task via type-ahead, (3) Add optional notes, (4) Submit |
| **ReferenceGraph** | Optional: Mini Mermaid diagram showing the reference network for the current item |

### 18.5  Reference Mapping UI Flow

```mermaid
flowchart TD
    Start([Job/Task Detail Page]) --> ShowRefs[Display ReferencesSection]
    ShowRefs --> HasRefs{Has references?}
    HasRefs -->|Yes| RenderTable[Render ReferenceTable<br>with linked items]
    HasRefs -->|No| EmptyState[Show 'No references yet'<br>+ Add Reference button]

    RenderTable --> ClickAdd[User clicks 'Add Reference']
    EmptyState --> ClickAdd

    ClickAdd --> OpenModal[Open AddReferenceModal]
    OpenModal --> SelectType[Select Reference Type<br>RELATED / BLOCKS / etc.]
    SelectType --> SearchTarget[Type-ahead search<br>GET /api/jobs/?search=query<br>GET /api/tasks/?search=query]
    SearchTarget --> SelectTarget[Select target item from results]
    SelectTarget --> AddNotes[Optional: add notes]
    AddNotes --> Submit[POST /api/jobs/{id}/references/]
    Submit --> RefreshTable[Refresh ReferencesSection]

    RenderTable --> ClickLink[User clicks linked item]
    ClickLink --> Navigate[Navigate to /jobs/{target_id}<br>or /tasks/{target_id}]

    RenderTable --> ClickRemove[User clicks Remove]
    ClickRemove --> Confirm[Confirm dialog]
    Confirm --> Delete[DELETE /api/references/{ref_id}/]
    Delete --> RefreshTable
```

---

## 19  GUI Skeleton Wireframes

ASCII wireframes for each major page layout. These show the structural skeleton — actual glass-morphism styling is defined in Section 8.

### 19.1  Master Layout Shell

```
┌─────────────────────────────────────────────────────────────────┐
│  🏢 DesignPortal    [🔍 Search...        ]  🔔(3)  👤 User ▾  │  ← Fixed Header (glass)
├────────┬────────────────────────────────────────────────────────┤
│        │                                                        │
│  NAV   │              MAIN CONTENT AREA                         │
│        │              (scrollable)                               │
│ ┌────┐ │                                                        │
│ │ 📊 │ │                                                        │
│ │Dash│ │                                                        │
│ ├────┤ │                                                        │
│ │ 📋 │ │                                                        │
│ │MyTk│ │                                                        │
│ ├────┤ │                                                        │
│ │ ➕ │ │                                                        │
│ │New │ │                                                        │
│ ├────┤ │                                                        │
│ │ 📁 │ │                                                        │
│ │Jobs│ │                                                        │
│ ├────┤ │                                                        │
│ │ ✅ │ │                                                        │
│ │Appr│ │                                                        │
│ ├────┤ │                                                        │
│ │ ⚙ │ │                                                        │
│ │Admn│ │                                                        │
│ └────┘ │                                                        │
│        │                                                        │
│  [◀]   │                                                        │  ← Collapse toggle
├────────┴────────────────────────────────────────────────────────┤
│  v1.0.0 │ © 2025 DesignPortal │ ● Connected                    │  ← Fixed Footer (glass)
└─────────────────────────────────────────────────────────────────┘
```

### 19.2  Dashboard (`/dashboard`)

```
┌──────────────────────────────────────────────────────────────┐
│  MAIN CONTENT AREA                                           │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Total   │ │  Active  │ │ Pending  │ │ Overdue  │       │
│  │  Jobs    │ │  Tasks   │ │ Approval │ │  Items   │       │
│  │   42     │ │   18     │ │    5     │ │    3     │       │
│  │  ↑12%    │ │  ↓3%     │ │  ──      │ │  ↑2      │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                              │
│  ┌────────────────────────┐ ┌────────────────────────┐      │
│  │  Jobs by Status        │ │  Tasks by Team          │      │
│  │  ┌──────────────────┐  │ │  ┌──────────────────┐  │      │
│  │  │   [BAR CHART]    │  │ │  │  [DOUGHNUT CHART] │  │      │
│  │  │                  │  │ │  │                   │  │      │
│  │  └──────────────────┘  │ │  └──────────────────┘  │      │
│  └────────────────────────┘ └────────────────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Upcoming Approvals                                   │   │
│  ├──────┬──────────┬──────────┬──────────┬────────┬─────┤   │
│  │ Type │ Title    │ Due Date │ Priority │ Status │ Act │   │
│  ├──────┼──────────┼──────────┼──────────┼────────┼─────┤   │
│  │ Job  │ PCB Rev3 │ Jan 25   │ 🔴 HIGH  │ Pend.  │ [→] │   │
│  │ Task │ Schem... │ Jan 28   │ 🟡 MED   │ Pend.  │ [→] │   │
│  └──────┴──────────┴──────────┴──────────┴────────┴─────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Recent Activity                                      │   │
│  │  ● 10:30  John approved Job #42 (Stage 2/3)          │   │
│  │  ● 09:15  Jane submitted Task #201                    │   │
│  │  ● 08:45  System: Due date reminder for Job #38       │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 19.3  Jobs List (`/jobs`)

```
┌──────────────────────────────────────────────────────────────┐
│  MAIN CONTENT AREA                                           │
│                                                              │
│  ┌─ Filter Panel (collapsible) ─────────────────┐  [+ New]  │
│  │ Status: [▾ All   ] Priority: [▾ All   ]      │           │
│  │ Team:   [▾ All   ] Group:    [▾ All   ]      │           │
│  │ Date:   [From    ] - [To      ]  [Apply]     │           │
│  └──────────────────────────────────────────────┘           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Jobs                                    [CSV Export] │   │
│  ├────┬──────────┬────────┬──────┬──────┬───────┬──────┤   │
│  │ ID │ Title  ▲ │ Status │ Pri  │ Team │ Due   │ Acts │   │
│  ├────┼──────────┼────────┼──────┼──────┼───────┼──────┤   │
│  │ 42 │ PCB v3   │🟢 Prog │🔴 H  │ PCB  │ 01/25 │ 👁✏ │   │
│  │ 41 │ Encl..   │🟡 Pend │🟡 M  │ HW   │ 01/28 │ 👁  │   │
│  │ 40 │ FW Up..  │🔵 Appr │🟢 L  │ FW   │ 02/01 │ 👁  │   │
│  │ 39 │ Draw..   │⚪ Draft│🟡 M  │ Draw │ --    │ 👁✏ │   │
│  └────┴──────────┴────────┴──────┴──────┴───────┴──────┘   │
│                                                              │
│  [◀ Prev]  Page 1 of 4  [10▾ per page]  [Next ▶]           │
└──────────────────────────────────────────────────────────────┘
```

### 19.4  Job Detail (`/jobs/{id}`)

```
┌──────────────────────────────────────────────────────────────┐
│  Dashboard > Jobs > PCB Board v3 Redesign                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PCB Board v3 Redesign                 [Edit] [...]  │   │
│  │  Status: 🟢 IN_PROGRESS   Priority: 🔴 HIGH          │   │
│  │  Team: PCB   |  Group: Electronics  |  Due: Jan 25   │   │
│  │  Created by: John Smith  |  Jan 10, 2025             │   │
│  │  Progress: [████████████░░░░░░░░] 65%                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Approval Status ───────────────────────────────────┐   │
│  │  ○──────●──────○──────○──────○                       │   │
│  │  GL✅   TM🔄   DM⏳   MechL   SafeL                  │   │
│  │  Approved  Reviewing  Pending  Pending  Pending      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Design-Team Fields ────────────────────────────────┐   │
│  │  Model Name: ProductX    Board Name: Main-CTRL      │   │
│  │  PCB Type: Multi-Layer   Layers: 6-Layer            │   │
│  │  Material: FR-4          Mfg: Internal              │   │
│  │  Dimensions: 120x80mm   Stack-up: Standard          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ References ────────────────────────────────────────┐   │
│  │  Type      │ Direction │ Linked Item    │ Status    │   │
│  │  RELATED   │    ↔      │ Job #41 Encl.. │ 🟡 Pend  │   │
│  │  BLOCKS    │    →      │ Task #201 Sch  │ ⏳ Wait  │   │
│  │                                  [+ Add Reference]   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Attachments ───────────────────────────────────────┐   │
│  │  📎 schematic_v3.pdf  (2.1 MB)  SharePoint  [⬇]    │   │
│  │  📎 gerber_files.zip  (5.4 MB)  Local       [⬇]    │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  📂 Drag & drop files here or [Browse]       │   │   │
│  │  │     or [Select from SharePoint]              │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Line Items ────────────────────────────────────────┐   │
│  │  Part#    │ Description  │ Qty │ Supplier │ Notes   │   │
│  │  IC-001   │ STM32F4      │ 2   │ Mouser   │ --      │   │
│  │  CAP-100  │ 100nF MLCC   │ 48  │ Digikey  │ 0402    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Comments ──────────────────────────────────────────┐   │
│  │  John (Jan 12): Updated layer count to 6            │   │
│  │  Jane (Jan 14): Approved impedance specs            │   │
│  │  ┌──────────────────────────────────────────┐       │   │
│  │  │  Add a comment...                  [Send]│       │   │
│  │  └──────────────────────────────────────────┘       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ History ───────────────────────────────────────────┐   │
│  │  ● Jan 14  Jane approved (Stage 1 - GL) ✅          │   │
│  │  ● Jan 12  John updated layer_count: 4 → 6          │   │
│  │  ● Jan 10  John created job                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [Submit for Approval]  [Cancel]  [Delete]                  │
└──────────────────────────────────────────────────────────────┘
```

### 19.5  Create Job — Multi-Step Wizard (`/jobs/new`)

```
┌──────────────────────────────────────────────────────────────┐
│  New Job Request                                             │
│                                                              │
│  ┌─ Step Progress ─────────────────────────────────────┐   │
│  │  ●━━━━━●━━━━━○━━━━━○━━━━━○━━━━━○                    │   │
│  │  1.Basic 2.Stake 3.Team  4.Files 5.Items 6.Review   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Step 1: Basic Information ─────────────────────────┐   │
│  │                                                      │   │
│  │  Title *         [________________________]          │   │
│  │                                                      │   │
│  │  Description     [________________________]          │   │
│  │                  [________________________]          │   │
│  │                                                      │   │
│  │  Request Type *  [▾ New Design           ]          │   │
│  │  Design Team *   [▾ PCB                  ]          │   │
│  │  Priority *      [▾ HIGH                 ]          │   │
│  │  Due Date        [📅 01/25/2025          ]          │   │
│  │  Group *         [▾ Electronics          ]          │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Step 3: PCB-Specific Fields (when team=PCB) ──────┐   │
│  │                                                      │   │
│  │  Model Name *        [________________________]      │   │
│  │  Design Stage *      [▾ Layout              ]       │   │
│  │  Board Name *        [________________________]      │   │
│  │  PCB Type *          [▾ Multi-Layer          ]       │   │
│  │  Layer Type *        [▾ 6-Layer              ]       │   │
│  │  Layer Count *       [6   ]                          │   │
│  │  PCB Material *      [▾ FR-4                 ]       │   │
│  │  Board Dimensions *  [120x80 mm              ]       │   │
│  │  Mfg Location *      [▾ Internal             ]       │   │
│  │  Impedance Control   [☐]                             │   │
│  │  Stack-up Type *     [▾ Standard             ]       │   │
│  │  Surface Finish      [▾ ENIG                 ]       │   │
│  │                                                      │   │
│  │  ── Management ──────────────────────────────        │   │
│  │  Group Leader *      [👤 Jane Smith    ][×]          │   │
│  │  Technical Mgr *     [👤 Bob Johnson   ][×]          │   │
│  │  Design Mgr *        [👤 Alice Wong    ][×]          │   │
│  │  Mech. Lead          [Select... (optional)  ]        │   │
│  │  Safety Lead         [Select... (optional)  ]        │   │
│  │  Project Mgr         [Select... (optional)  ]        │   │
│  │                                                      │   │
│  │  Progress (%)        [====|===========] 0%           │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Step 4: Attachments ───────────────────────────────┐   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  📂 Drag & drop files here                    │   │   │
│  │  │     [Browse]  [SharePoint Select]             │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  │  Location: [▾ SharePoint ]                          │   │
│  │                                                      │   │
│  │  📎 schematic_v3.pdf  ████████░░ 80%  [×]           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│                            [◀ Back]  [Next ▶]  [Save Draft] │
└──────────────────────────────────────────────────────────────┘
```

### 19.6  Approvals Page (`/approvals`)

```
┌──────────────────────────────────────────────────────────────┐
│  My Pending Approvals                                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Filter: [▾ All Types]  [▾ All Teams]  [▾ All Pri]   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  ├────┬──────────┬──────┬──────┬────────┬──────────────┤   │
│  │Type│ Title    │ Team │ Pri  │ Stage  │ Actions      │   │
│  ├────┼──────────┼──────┼──────┼────────┼──────────────┤   │
│  │Job │ PCB v3   │ PCB  │🔴 H  │ 2/3 TM │[✅Appr][❌Rej]│   │
│  │Task│ Schem..  │ PCB  │🟡 M  │ 1/3 GL │[✅Appr][❌Rej]│   │
│  │Job │ Encl..   │ HW   │🟢 L  │ 3/3 DM │[✅Appr][❌Rej]│   │
│  └────┴──────────┴──────┴──────┴────────┴──────────────┘   │
│                                                              │
│  ┌─ Approval Modal (on click) ─────────────────────────┐   │
│  │                                                      │   │
│  │  PCB Board v3 Redesign                               │   │
│  │  ─────────────────────────────────────────           │   │
│  │  Requester: John Smith                               │   │
│  │  Team: PCB  |  Priority: HIGH  |  Due: Jan 25       │   │
│  │                                                      │   │
│  │  Approval Stage: 2 of 3 (Technical Manager)         │   │
│  │  Previous: GL ✅ Jane (Jan 14)                       │   │
│  │                                                      │   │
│  │  Attachments: 📎 schematic_v3.pdf  📎 gerber.zip    │   │
│  │                                                      │   │
│  │  Comment: [________________________]                 │   │
│  │           [________________________]                 │   │
│  │                                                      │   │
│  │  [✅ Approve]                    [❌ Reject]          │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 19.7  Triage Page (`/manage/triage`) — Group Leader Only

```
┌──────────────────────────────────────────────────────────────┐
│  Triage — Incoming Requests                                  │
│                                                              │
│  ┌─ Submitted Items Awaiting Acceptance ───────────────┐   │
│  ├────┬──────────┬──────┬──────┬──────────┬────────────┤   │
│  │Type│ Title    │ By   │ Team │ Submitted│ Actions    │   │
│  ├────┼──────────┼──────┼──────┼──────────┼────────────┤   │
│  │Job │ New PCB  │ John │ PCB  │ Jan 20   │[✅Acc][❌Rej]│   │
│  │Task│ Review.. │ Jane │ FW   │ Jan 21   │[✅Acc][❌Rej]│   │
│  └────┴──────────┴──────┴──────┴──────────┴────────────┘   │
│                                                              │
│  ┌─ Pending Close (Approved, awaiting GL closure) ─────┐   │
│  ├────┬──────────┬──────┬──────┬──────────┬────────────┤   │
│  │Type│ Title    │ Team │ Due  │ Approvals│ Actions    │   │
│  ├────┼──────────┼──────┼──────┼──────────┼────────────┤   │
│  │Job │ HW Encl  │ HW   │Jan 15│ 3/3 ✅   │[✅Close]    │   │
│  └────┴──────────┴──────┴──────┴──────────┴────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 19.8  Admin — Design Teams (`/admin/design-teams`)

```
┌──────────────────────────────────────────────────────────────┐
│  Admin > Design Teams                            [+ New]     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  ├────┬──────────┬────────────┬──────────┬─────────────┤   │
│  │ ID │ Name     │ Default    │ Form     │ Actions     │   │
│  │    │          │ Route      │ Fields   │             │   │
│  ├────┼──────────┼────────────┼──────────┼─────────────┤   │
│  │  1 │ PCB      │ Standard3  │ 12 fields│ [✏][🗑]     │   │
│  │  2 │ Hardware │ Standard3  │  9 fields│ [✏][🗑]     │   │
│  │  3 │ Firmware │ Standard3  │ 10 fields│ [✏][🗑]     │   │
│  │  4 │ Drawing  │ Standard3  │  9 fields│ [✏][🗑]     │   │
│  └────┴──────────┴────────────┴──────────┴─────────────┘   │
│                                                              │
│  ┌─ Edit Team Modal ───────────────────────────────────┐   │
│  │  Name *           [PCB                     ]         │   │
│  │  AAD Group ID     [azure-group-id-here     ]         │   │
│  │  Default Route *  [▾ Standard 3-Stage      ]         │   │
│  │  Form Definition  [{ JSON editor... }      ]         │   │
│  │                   [Save]  [Cancel]                    │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 20  Validation Checklist — Does This Plan Meet All Targets?

| Target | Section Covered | Status |
|--------|----------------|--------|
| C4 Model (Context, Container, Component, Code) | Sections 2, 3, 4, 5 | YES |
| Python backend (Django + DRF) | Section 1.1, 4.1, 9, 11 | YES |
| Windows 11 domain PC hosting | Section 0, 3, 8.4, 11 Phase 8 | YES |
| Waitress WSGI server on port **9091** | Section 0, 3, 10, 11 Phase 8 | YES |
| Glass-morphism design | Section 8 (full token + utility system) | YES |
| Fixed header | Section 7.1, 8.2 (`.glass-header`) | YES |
| Fixed footer | Section 7.1, 8.2 (`.glass-footer`) | YES |
| Collapsible navigation panel (sidebar) | Section 7.1, 8.2 (`.glass-sidebar`) | YES |
| Light / Dark mode | Section 8.1 (`[data-theme="dark"]`) | YES |
| All database tables with column details | Section 5.1 (14 tables + `job_reference` in 18.2) | YES |
| ERD diagram | Section 5.2 | YES |
| State machine for Job/Task lifecycle (acceptance → work → approval → close) | Section 5.3 (4 subsections, 14 transitions) | YES |
| API endpoint reference (full) | Section 6 (8 groups, all methods) + 17.3, 18.3 | YES |
| Page specifications with component lists | Section 7.2 (16 pages detailed) | YES |
| Multi-step form wizard (6 steps) | Section 7.2.4 | YES |
| FormDefinition JSON contract | Section 13 | YES |
| Design-team-specific fields with management fields (PCB, HW, FW, Drawing) | Section 14 (14.0 common + 4 teams fully specified) | YES |
| ApprovalRoute JSON schema | Section 15 | YES |
| People Picker with role-based behavior | Sections 7.2.4 Step 2, 12.3 | YES |
| Editable inline table for line items | Sections 7.2.4 Step 5, 13 | YES |
| Attachment upload (Drag & Drop, Browse, SharePoint Select) | Sections 4.1.8, 7.2.4 Step 4, 14.0, 11 Phase 5 | YES |
| Default approvers per team/type (GL, TM, DM + optional) | Sections 5.1 (table), 5.3.4, 6.2 (API), 14.0 | YES |
| RBAC (Admin, GroupLeader, User) | Sections 2, 4.1.1, 6, 7.1 | YES |
| Audit trail / history | Sections 5.1 (`history_entry` table), 7.2.3 | YES |
| Email notifications via Graph | Section 4.1.6, 11 Phase 5, 17 | YES |
| Due-date monitoring worker with reminders | Section 16 (worker flow, reminder schedule, deduplication) | YES |
| Notification handling map (all events, recipients, templates) | Section 17 (18 event types mapped) | YES |
| Reference mapping / cross-referencing between jobs/tasks | Section 18 (model, API, UI flow) | YES |
| GUI skeleton wireframes | Section 19 (8 page wireframes) | YES |
| Sequence diagrams (job creation, approval) | Section 12 | YES |
| Project folder structure (backend + frontend) | Section 9 | YES |
| Environment variables template | Section 10 | YES |
| Step-by-step build instructions (9 phases) | Section 11 | YES |
| Easily extendable/reducible | JSON-driven forms + JSONB metadata — add/remove fields without schema changes | YES |
| Debug/seed users for UI testing (all roles) | Section 10.1 (10 users, testing matrix, debug auth backend) | YES |
| All database tables listed in Section 5.1 (including notification, job_reference) | Section 5.1 (16 tables) | YES |
| Health check & API versioning endpoints | Section 6.9 | YES |
| Standardized error response format | Section 22.6 | YES |
| ISO/IEC 27001 alignment (Information Security) | Section 22.1 | YES |
| ISO 9001 alignment (Quality Management) | Section 22.2 | YES |
| ISO/IEC 12207 / IEEE 12207 alignment (Software Lifecycle) | Section 22.3 | YES |
| IEEE 730 alignment (Software Quality Assurance) | Section 22.4 | YES |
| IEC 62443 alignment (Industrial Cybersecurity principles) | Section 22.5 | YES |
| OWASP Top 10 protection matrix | Section 23.1 | YES |
| Authentication & session hardening | Section 23.2 | YES |
| Input validation & data sanitization | Section 23.3 | YES |
| Security logging & monitoring | Section 23.4 | YES |
| Network & transport security (TLS, HSTS, CSP, CORS, rate limiting) | Section 23.5 | YES |
| EU Cyber Resilience Act (CRA) compliance mapping | Section 23.6 | YES |
| Secret & credential management policy | Section 23.7 | YES |
| Backup & recovery strategy (RTO/RPO) | Section 23.8 | YES |
| Data privacy & retention policy | Section 23.9 | YES |
| Performance requirements & caching strategy | Section 24.1–24.2 | YES |
| Database performance optimization (indexes, pooling) | Section 24.3 | YES |
| Internationalization (i18n) preparation | Section 24.4 | YES |

---

## 21  Glossary

| Term | Definition |
|------|-----------|
| **Job** | A top-level design request (e.g. "Design new PCB for product X") |
| **Task** | A work item — either standalone or a child of a Job |
| **Design Team** | An engineering discipline: PCB, Drawing, Hardware, Firmware |
| **Approval Route** | An ordered sequence of approval steps that a Job/Task must pass (default: GL → TM → DM) |
| **Approval Instance** | A runtime record tracking a specific Job/Task's progress through its route |
| **Default Approver** | Pre-configured approver list per design team + request type |
| **Form Definition** | JSON schema defining the multi-step form for a request type |
| **Line Item** | A row in the editable table (e.g. BOM entry) |
| **Metadata** | JSONB column storing dynamic custom fields, approver IDs, watchers, approval stage |
| **People Picker** | UI component for selecting users from the corporate directory |
| **Glass-morphism** | UI design style using frosted glass effects (blur, transparency, layered panels) |
| **RBAC** | Role-Based Access Control |
| **AAD Object ID** | Azure Active Directory unique identifier for a user |
| **Acceptance** | The initial step where a Group Leader acknowledges a submitted job/task (not the approval route) |
| **Approval Route** | The sequential multi-stage review (GL → TM → DM + optional) triggered after work completion |
| **Re-Approval** | Required when a job/task is modified after approval but before the Group Leader closes it |
| **Due-Date Worker** | Background process that monitors deadlines and sends escalating reminders |
| **Reference** | A typed link between two jobs/tasks (RELATED, BLOCKS, SUPERSEDES, etc.) |
| **PendingClose** | Status after all approvals pass — GL must review and close; modifications trigger re-approval |
| **Debug User** | A local-only user (not in AAD) created via `seed_debug_users` for testing the UI at different roles without an IdP |
| **DebugAuthBackend** | Django authentication backend that allows username/password login for debug users; gated behind `DEBUG=True` + `DEBUG_AUTH_ENABLED=True` |
| **CRA** | EU Cyber Resilience Act (Regulation EU 2024/2847) — cybersecurity requirements for products with digital elements |
| **OWASP** | Open Web Application Security Project — produces the Top 10 web application security risks list |
| **CSP** | Content Security Policy — HTTP header that restricts which resources the browser can load |
| **HSTS** | HTTP Strict Transport Security — forces HTTPS connections |
| **SCA** | Software Composition Analysis — scanning dependencies for known vulnerabilities |
| **RTO** | Recovery Time Objective — maximum acceptable downtime after a failure |
| **RPO** | Recovery Point Objective — maximum acceptable data loss measured in time |
| **SIEM** | Security Information and Event Management — centralized log analysis for threat detection |
| **WAL** | Write-Ahead Log — PostgreSQL mechanism for point-in-time recovery |
| **DSAR** | Data Subject Access Request — GDPR right to access personal data |

---

## 22  Standards & Compliance Alignment

This section maps how the DesignPortal architecture aligns with relevant international standards. Each sub-section identifies the standard, its applicability, and specific implementation guidance.

### 22.1  ISO/IEC 27001 — Information Security Management

| Control Area | Standard Clause | Implementation in DesignPortal |
|-------------|----------------|-------------------------------|
| **Access Control** | A.9 | RBAC (Admin, Group Leader, User); OIDC SSO via Azure AD / Okta; row-level scoping by Group; `django-guardian` for object-level permissions |
| **Cryptography** | A.10 | TLS termination at IIS/Nginx reverse proxy; passwords hashed via Django's PBKDF2/Argon2; OIDC tokens encrypted in transit; `DJANGO_SECRET_KEY` stored in `.env` outside VCS |
| **Operations Security** | A.12 | Django logging (file + console); `django-simple-history` for change audit trail; `history_entry` table records all mutations; Sentry error tracking (optional) |
| **Communications Security** | A.13 | HTTPS enforced in production; CORS whitelist; API rate limiting; `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` in `prod.py` |
| **Supplier Relationships** | A.15 | Dependency pinning via `requirements.txt` and `package-lock.json`; SCA scanning in CI pipeline (see Section 23.6) |
| **Incident Management** | A.16 | Structured error responses (Section 22.5); security logging (Section 23.4); notification escalation for system events |
| **Business Continuity** | A.17 | Database backup strategy (Section 22.4); NSSM service auto-restart; health check endpoint `/api/health/` |
| **Compliance** | A.18 | Audit trail on all models; immutable `history_entry` records; debug auth disabled in production |

### 22.2  ISO 9001 — Quality Management (Process Alignment)

| QMS Principle | Application in DesignPortal |
|--------------|----------------------------|
| **Document Control** | Job/task versioning via `metadata` JSONB + `history_entry`; attachment versioning (`version` column); `FormDefinition.version` for schema evolution |
| **Traceability** | Full audit trail (`history_entry`); cross-referencing (Section 18 — `BLOCKS`, `RELATED`, `SUPERSEDES`); approval decisions recorded with timestamp, actor, and comment |
| **Process Approach** | State machine (Section 5.3) defines a repeatable workflow: Draft → Submit → Accept → Work → Approve → Close; ApprovalRoute enforces mandatory checkpoints |
| **Continual Improvement** | Dashboard metrics (Section 7.2.1) provide visibility into turnaround times, bottleneck stages, and overdue rates; exportable CSV for analysis |
| **Customer Focus** | Requester is notified at every status transition; can track progress via detail page; watchers receive updates |
| **Non-conformance Handling** | `REJECTED` and `APPROVAL_REJECTED` statuses with mandatory comments document non-conformances; re-submission flow preserves rejection history |

### 22.3  ISO/IEC 12207 / IEEE 12207 — Software Lifecycle Processes

| Lifecycle Process | Coverage in This Plan |
|------------------|----------------------|
| **Requirements Analysis** | Sections 0–7: project identity, actors, C4 diagrams, DB schema, API contracts, UI specifications |
| **Architectural Design** | C4 Levels 1–3 (Sections 2–4): context, container, component decomposition |
| **Detailed Design** | C4 Level 4 (Section 5): database tables, state machine, ERD; Section 13–15: JSON schemas |
| **Implementation** | Section 11: 9-phase build instructions with verification gates |
| **Testing** | Phase 9: pytest + Cypress; Section 10.1: debug users for manual testing across all roles |
| **Deployment** | Phase 8: Waitress + NSSM on Windows 11; optional IIS reverse proxy; CI/CD pipeline |
| **Maintenance** | JSON-driven forms (extendable without schema changes); `JSONB` metadata for forward compatibility; API versioning strategy (Section 6.9) |

### 22.4  IEEE 730 — Software Quality Assurance

| SQA Element | Implementation |
|-------------|---------------|
| **Configuration Management** | Git VCS; `.env.example` template; `requirements.txt` + `package-lock.json` dependency lock |
| **Reviews & Audits** | Approval route provides mandatory peer review (GL → TM → DM); Section 20 validation checklist |
| **Testing Strategy** | Unit (pytest), integration (DRF APITestCase), component (Vitest + RTL), E2E (Cypress) |
| **Metrics & Measurement** | Dashboard metrics: completion rate, average turnaround, overdue count, approval cycle time |
| **Risk Management** | Due-date worker escalation (Section 16); re-approval on modification (Section 5.3); fallback file storage (local if SharePoint unavailable) |

### 22.5  IEC 62443 — Industrial Cybersecurity (Applicable Principles)

While DesignPortal is not an industrial control system, it manages engineering design data for products that may include PCB, firmware, and hardware destined for industrial environments. Relevant IEC 62443 principles applied:

| IEC 62443 Principle | Application |
|--------------------|-------------|
| **Zones & Conduits** | Database (PostgreSQL) runs on a separate service/port from the application server; Graph API calls go through dedicated service layer; no direct DB exposure to frontend |
| **Least Privilege** | RBAC with three tiers; API endpoints enforce role-based access; PeoplePicker search restricted by role; row-scoping by Group |
| **Defense in Depth** | TLS + CORS + CSRF + rate limiting + input validation + parameterized queries (Django ORM) + audit logging |
| **Security Monitoring** | `history_entry` for application-level audit; Django logging for system events; security event logging (Section 23.4) |
| **Patch Management** | CI pipeline runs dependency vulnerability scan; `pip-audit` + `npm audit` in Phase 9 |

### 22.6  Standardized Error Response Format

All API endpoints return errors in a consistent JSON envelope:

```jsonc
{
  "error": {
    "code": "VALIDATION_ERROR",           // Machine-readable code
    "message": "Title is required.",       // Human-readable message
    "field": "title",                      // Field name (for validation errors)
    "details": []                          // Array of sub-errors for bulk validation
  },
  "status": 400                            // HTTP status code mirror
}
```

| HTTP Status | Error Code | Usage |
|-------------|-----------|-------|
| 400 | `VALIDATION_ERROR` | Missing/invalid field, business rule violation |
| 401 | `AUTHENTICATION_REQUIRED` | Missing or expired token |
| 403 | `PERMISSION_DENIED` | User lacks role/scope |
| 404 | `NOT_FOUND` | Resource does not exist or is outside user's scope |
| 409 | `CONFLICT` | State machine violation (e.g. closing a non-approved job) |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unhandled server error (details hidden in production) |

---

## 23  Cybersecurity & CRA Compliance

This section addresses cybersecurity hardening requirements aligned with the **EU Cyber Resilience Act (CRA)**, **OWASP Top 10 2021**, and general application security best practices.

### 23.1  OWASP Top 10 Protection Matrix

| # | OWASP Category | Risk | Mitigation in DesignPortal |
|---|---------------|------|----------------------------|
| A01 | **Broken Access Control** | Unauthorized data access | RBAC with DRF permission classes (`IsAdmin`, `IsGroupLeaderOrAbove`); row-level Group scoping on all queries; `RBACGuard` on frontend routes; object-level permissions via `django-guardian`; session invalidation on logout |
| A02 | **Cryptographic Failures** | Data exposure | TLS 1.2+ enforced via reverse proxy; `SECURE_SSL_REDIRECT=True`; passwords hashed with PBKDF2/Argon2; `DJANGO_SECRET_KEY` ≥50 chars, rotated quarterly; no secrets in Git (`.env` excluded via `.gitignore`) |
| A03 | **Injection** | SQL/NoSQL/LDAP injection | Django ORM for all queries (parameterized); DRF serializer validation on all inputs; `bleach` or `DOMPurify` for any rendered HTML (comments); JSONB fields validated against schemas |
| A04 | **Insecure Design** | Architectural flaws | C4 model architecture; state machine enforces valid transitions only; approval route cannot be bypassed; debug auth gated behind two flags; separation of concerns (apps per domain) |
| A05 | **Security Misconfiguration** | Default/weak config exposed | `DEBUG=False` in production; `ALLOWED_HOSTS` set explicitly; CORS whitelist (no `*`); `X-Content-Type-Options: nosniff`; `X-Frame-Options: DENY`; Django security middleware enabled |
| A06 | **Vulnerable Components** | Known CVE in dependencies | `pip-audit` in CI; `npm audit` in CI; dependency pinning; Dependabot/Renovate for auto-updates; Python 3.11+ (supported LTS) |
| A07 | **Auth Failures** | Credential stuffing, session hijack | OIDC SSO (no local passwords for real users); short-lived JWT access tokens (15 min); refresh tokens (HttpOnly, Secure, SameSite=Strict); account lockout after 5 failed debug logins; session ID rotation on login |
| A08 | **Data Integrity Failures** | Unsigned updates, CI/CD tampering | `django-simple-history` for change tracking; approval decisions immutable once recorded; CI pipeline signs build artifacts; `SECURE_HSTS_SECONDS` prevents downgrade attacks |
| A09 | **Logging & Monitoring Failures** | Blind to attacks | Structured security logging (Section 23.4); failed auth attempts logged; rate-limit breaches logged; file upload policy violations logged; log aggregation to SIEM-compatible JSON format |
| A10 | **SSRF** | Internal resource access | Graph API URLs validated against allowlist; file upload paths validated; no user-controlled URL fetching; network share paths restricted to configured roots |

### 23.2  Authentication & Session Security

| Control | Implementation |
|---------|---------------|
| **SSO (Production)** | Azure AD / Okta via OIDC Authorization Code Flow with PKCE |
| **Token Strategy** | Access token: JWT, 15-minute expiry; Refresh token: HttpOnly cookie, 8-hour expiry, rotate on use |
| **Session Security** | `SESSION_COOKIE_SECURE=True`; `SESSION_COOKIE_HTTPONLY=True`; `SESSION_COOKIE_SAMESITE='Strict'`; `SESSION_COOKIE_AGE=28800` (8 hours) |
| **CSRF Protection** | Django CSRF middleware enabled; `CSRF_COOKIE_SECURE=True`; frontend sends `X-CSRFToken` header via Axios interceptor |
| **Debug Auth Isolation** | `DebugAuthBackend` only active when BOTH `DEBUG=True` AND `DEBUG_AUTH_ENABLED=True`; returns 404 in production; no debug users have `is_superuser=True` |
| **Account Lockout** | After 5 failed login attempts for debug users: 15-minute lockout; logged as security event |
| **Token Revocation** | Refresh token blacklist stored in DB; logout invalidates all active tokens |

### 23.3  Input Validation & Data Sanitization

| Layer | Control |
|-------|---------|
| **API Serializers** | All input validated through DRF serializers; `CharField(max_length=...)`, `IntegerField(min_value=..., max_value=...)`, `ChoiceField(choices=...)` |
| **JSONB Validation** | `metadata` and `form_definition` validated against JSON schemas before storage; reject unknown keys |
| **File Uploads** | Allowed MIME types enforced server-side (not just extension); maximum file size: 50MB per file, 200MB per request; file names sanitized (remove `../`, null bytes, unicode exploits); antivirus scan hook (optional, ClamAV integration) |
| **SQL Injection** | Django ORM only — no raw SQL; `extra()` and `RawSQL` prohibited by code review policy |
| **XSS Prevention** | Comment `body` sanitized with `bleach.clean()` on save; frontend uses React's default JSX escaping; CSP header restricts inline scripts |
| **Path Traversal** | `file_path` validated against `SHAREPOINT_SITE_ID` or `LOCAL_MEDIA_ROOT` base path; `os.path.realpath()` + `startswith()` check |

### 23.4  Security Logging & Monitoring

All security-relevant events are logged in structured JSON format for SIEM integration:

```jsonc
{
  "timestamp": "2025-01-20T10:30:00Z",
  "level": "WARNING",
  "event": "AUTH_FAILURE",
  "actor": "debug_admin",
  "ip": "10.0.1.50",
  "user_agent": "Mozilla/5.0 ...",
  "details": { "reason": "invalid_password", "attempts": 3 }
}
```

| Event Category | Events Logged |
|---------------|---------------|
| **Authentication** | Login success, login failure, logout, token refresh, token revocation, account lockout |
| **Authorization** | Permission denied (403), scope violation (accessing another group's data), role escalation attempt |
| **Data Modification** | Record create/update/delete (via `history_entry`); bulk operations; admin config changes |
| **File Operations** | Upload success, upload rejected (type/size), download, delete |
| **System** | Health check failures, DB connection errors, Graph API errors, rate limit triggers |
| **Approval Workflow** | State transitions, approval decisions, re-approval triggers, modification detection |

**Log Retention:** Security logs retained for **90 days** on local disk; archived to network share monthly. Production logs exclude debug-level output.

### 23.5  Network & Transport Security

| Control | Setting |
|---------|---------|
| **TLS** | TLS 1.2 minimum (1.3 preferred); configured at IIS/Nginx reverse proxy level |
| **HSTS** | `SECURE_HSTS_SECONDS=31536000` (1 year); `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`; `SECURE_HSTS_PRELOAD=True` |
| **Content Security Policy** | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' https://graph.microsoft.com https://login.microsoftonline.com; font-src 'self'; frame-ancestors 'none';` |
| **Security Headers** | `X-Content-Type-Options: nosniff`; `X-Frame-Options: DENY`; `Referrer-Policy: strict-origin-when-cross-origin`; `Permissions-Policy: camera=(), microphone=(), geolocation=()` |
| **CORS** | Explicit origin whitelist (no wildcard); `Access-Control-Allow-Credentials: true` only for the SPA origin |
| **Rate Limiting** | API: 100 requests/minute per user (authenticated); Search endpoints: 30 requests/minute; Login: 10 attempts/minute per IP; implemented via `django-ratelimit` or DRF throttle classes |

### 23.6  EU Cyber Resilience Act (CRA) — Compliance Mapping

The CRA (Regulation EU 2024/2847) establishes cybersecurity requirements for products with digital elements. While DesignPortal is an internal tool, it processes design data for products potentially subject to CRA. Relevant requirements:

| CRA Essential Requirement | Article | Implementation |
|--------------------------|---------|----------------|
| **Security by Design** | Art. 10(1) | C4 architecture with separation of concerns; RBAC; principle of least privilege; defense in depth |
| **No Known Exploitable Vulnerabilities** | Art. 10(2) | CI pipeline runs `pip-audit`, `npm audit`, and OAST scanning; Dependabot enabled; critical CVEs patched within 48 hours |
| **Secure Default Configuration** | Art. 10(3) | `DEBUG=False` by default; `DEBUG_AUTH_ENABLED=False` by default; CORS locked to specific origins; all security headers enabled; CSRF enforced |
| **Access Control** | Art. 10(4) | OIDC SSO; RBAC; row-level Group scoping; session timeouts; API rate limiting |
| **Data Confidentiality** | Art. 10(5) | TLS in transit; sensitive fields (passwords, secrets) never returned in API responses; `GRAPH_CLIENT_SECRET` protected in `.env` |
| **Data Integrity** | Art. 10(6) | Immutable `history_entry`; `django-simple-history` on tracked models; approval decisions append-only |
| **Minimal Data Processing** | Art. 10(7) | Only required user attributes fetched from AD (`displayName`, `mail`, `department`); no excessive data collection |
| **Availability & Resilience** | Art. 10(8) | NSSM auto-restart; health check endpoint; database backup strategy; due-date worker heartbeat |
| **Incident Handling** | Art. 10(9) | Security event logging (Section 23.4); structured error responses; log aggregation for incident investigation |
| **Software Updates** | Art. 10(10) | CI/CD pipeline for automated build and deploy; versioned API (Section 6.9); migration-safe schema changes |
| **Vulnerability Disclosure** | Art. 11 | `SECURITY.md` file in repository root with disclosure policy, contact email, and PGP key |

### 23.7  Secret & Credential Management

| Secret | Storage | Rotation |
|--------|---------|----------|
| `DJANGO_SECRET_KEY` | `.env` file (640 permissions, owned by service account) | Quarterly |
| `DB_PASSWORD` | `.env` file | Quarterly |
| `OIDC_CLIENT_SECRET` | `.env` file + Azure Key Vault (recommended) | On compromise |
| `GRAPH_CLIENT_SECRET` | `.env` file + Azure Key Vault (recommended) | Annually or on compromise |
| JWT signing key | Derived from `DJANGO_SECRET_KEY` or dedicated RSA key pair | Quarterly |
| Debug user passwords | Hardcoded in seed command (dev only); never promoted to production | N/A |

> **Best practice:** Migrate secrets to **Azure Key Vault** or **HashiCorp Vault** for production. Use `azure-identity` SDK to read secrets at startup instead of `.env` files.

### 23.8  Backup & Recovery

| Component | Strategy | Frequency | Retention |
|-----------|----------|-----------|-----------|
| **PostgreSQL** | `pg_dump` full backup → encrypted archive to network share | Daily (02:00) | 30 days |
| **PostgreSQL** | WAL archiving for point-in-time recovery (PITR) | Continuous | 7 days |
| **File Storage (Local)** | Robocopy mirror to secondary network share | Nightly | 30 days |
| **File Storage (SharePoint)** | SharePoint built-in versioning and recycle bin | Automatic | Per SharePoint policy |
| **Application Config** | `.env` backed up with DB backup (excluded from Git) | With DB backup | 30 days |
| **Git Repository** | Azure DevOps / GitHub — distributed by nature | On push | Indefinite |

**Recovery Time Objective (RTO):** 4 hours. **Recovery Point Objective (RPO):** 24 hours (daily backup) or near-zero with WAL archiving.

### 23.9  Data Privacy & Retention

| Data Category | Retention Period | Disposal Method |
|--------------|-----------------|-----------------|
| Active jobs/tasks | Indefinite (while in use) | Soft-delete → `is_active=False` |
| Completed jobs/tasks | 5 years (configurable) | Archive to read-only schema; purge after retention |
| User accounts | Active while employed | Deactivate on AD sync; purge PII after 1 year post-deactivation |
| History entries | 5 years | Immutable — archived with parent record |
| Notifications | 90 days | Auto-purge via management command |
| Security logs | 90 days local; 1 year archived | Archive → encrypted network share → shred after retention |
| Debug users | Development lifecycle only | `python manage.py seed_debug_users --reset` before production |

> **GDPR/Privacy Note:** If users from EU jurisdictions access the portal, ensure a Privacy Notice is displayed, data subject access requests (DSAR) are supported via admin export, and the right to erasure is implemented for PII fields (`display_name`, `email`, `department`).

---

## 24  Non-Functional Requirements & Architecture Decisions

### 24.1  Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| API response time (p95) | < 500ms | Django middleware timing + APM |
| Page load time (TTI) | < 2 seconds | Lighthouse CI |
| Concurrent users | ≥ 50 simultaneous | Load test with Locust/k6 |
| Database query count per request | ≤ 10 (use `select_related`/`prefetch_related`) | Django Debug Toolbar |
| File upload throughput | ≥ 5 MB/s | Manual benchmark |

### 24.2  Caching Strategy

| Layer | Technology | What's Cached | TTL |
|-------|-----------|---------------|-----|
| **API Response** | Django per-view cache (Redis backend) | Dashboard metrics, design team list, form definitions | 60 seconds |
| **Database** | `select_related` / `prefetch_related` | Nested serializer queries (avoid N+1) | Per-request |
| **Frontend** | React Query / SWR (or Axios interceptor) | GET responses with `stale-while-revalidate` | 30 seconds |
| **Static Assets** | WhiteNoise + Cache-Control headers | JS/CSS/images | 1 year (content-hashed filenames) |
| **Session** | Django session backend (DB or Redis) | User session data | `SESSION_COOKIE_AGE` |

### 24.3  Database Performance

| Optimization | Implementation |
|-------------|---------------|
| **Indexes** | Add B-tree indexes on: `job.status`, `job.design_team_id`, `job.group_id`, `job.created_at`, `job.due_date`, `task.status`, `task.assignee_id`, `task.parent_job_id`, `approval_instance.status`, `notification.recipient_id + is_read` |
| **Composite Index** | `(status, group_id)` for scoped list queries; `(design_team_id, request_type)` on `default_approver` |
| **JSONB Indexes** | GIN index on `job.metadata` for `@>` containment queries |
| **Connection Pooling** | `django-db-connection-pool` or PgBouncer for connection reuse |
| **Query Optimization** | `select_related('created_by', 'group', 'design_team')` on all list views |

### 24.4  Internationalization (i18n) — Future-Ready

| Layer | Preparation |
|-------|-------------|
| **Backend** | Django `i18n` middleware enabled; all user-facing strings wrapped in `gettext_lazy()` |
| **Frontend** | `react-i18next` configured; all display strings in `locales/en.json`; date/time formatting via `Intl` API |
| **Database** | Multi-language fields stored as `{ "en": "...", "fr": "..." }` in JSONB (future) |
| **Settings** | Language selector on Settings page (Section 7.2.16) wired to `i18n.changeLanguage()` |

---

*End of Plan — Use this document as the single reference to build the DesignPortal application.*
