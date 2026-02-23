# Architecture Plan for Custom Design-Job & Task Portal (Draft)

This document lays out a **full‑stack architecture plan** for building a fully custom design‑job and task management portal.  It outlines the project structure, key modules, integration points, UI considerations, and deployment.  The portal uses **Django** for the back end, a **modern front‑end** with glass‑morphism aesthetics (supporting light and dark modes), **Okta** for single sign‑on, **Microsoft Graph** for sending emails, and **SharePoint (or network storage)** for artefacts.

## Key design considerations

1. **Modern glass‑morphism UI with light/dark mode.**  Glass‑morphism creates depth by using frosted glass effects, transparency, and layered panels[3](https://www.ramotion.com/blog/what-is-glassmorphism/).  To preserve legibility and accessibility the design must maintain sufficient contrast, limit overuse of blur, and adhere to documented opacity ranges (10–40 %)[3](https://www.ramotion.com/blog/what-is-glassmorphism/).  A component library or utility framework (e.g., Tailwind CSS with custom glass‑morphism classes) should define consistent blur, opacity, borders, gradients and shadows as part of a design system[3](https://www.ramotion.com/blog/what-is-glassmorphism/).  Themes share a core palette but swap variables for light/dark modes.

2. **Role‑based access and SSO.**  Exchange of tasks and jobs will involve multiple roles (System Administrator, Group Leader, Approver, User) and require group/department scoping.  Okta provides OpenID Connect authentication; roles are mapped in Django’s database.  Permissions control viewing and editing rights for each job/task based on membership in groups, departments, or an explicit “audience only” list.

3. **File storage.**  Artefacts (schematics, PCB design files, documents) must be stored either on a secure network folder or uploaded to SharePoint via the `office365-rest-python-client` API.  This API allows uploading a file to a SharePoint folder using `target_folder.files.upload(...).execute_query()` after authenticating with client credentials.

4. **Email notifications.**  Notifications and approvals should be sent via Microsoft Graph from a dedicated address (e.g., `Ticketing_Portal@company.com`).  Graph supports sending messages “on behalf of” or “as” another mailbox; the calling user must have **Mail.Send.Shared** delegated permission and underlying Exchange *Send As* or *Send on Behalf* rights[2](https://learn.microsoft.com/en-us/graph/outlook-send-mail-from-other-user).  When sending from a non‑user object like a distribution list or mail‑enabled group, the message must include a `from` property with that address and the service account must have *SendAs* or *SendOnBehalfOf* permission[1](https://practical365.com/sendas-send-on-behalf-of-mail-objects/).  Setting `saveToSentItems=false` prevents errors if the sender has no Sent Items folder (e.g., distribution lists)[2](https://learn.microsoft.com/en-us/graph/outlook-send-mail-from-other-user).

5. **Deployment environment.**  The application runs under **Waitress**, a pure‑Python WSGI server that works on Windows and Unix and has no dependencies outside the standard library[4](https://docs.pylonsproject.org/projects/waitress/en/stable/index.html).  Development uses Django’s built‑in server; production on Windows uses Waitress, optionally wrapped by NSSM to run as a service.


## Project structure

The codebase should be organized clearly to separate back‑end, front‑end, configuration and docs.  A typical layout might look like this:

```
/DesignPortal/              # root of the git repository
├── README.md               # project overview and setup instructions
├── pyproject.toml / setup.cfg    # project metadata and dependencies
├── .env.example            # environment variables template (Okta, Graph, DB credentials)
├── manage.py               # Django management script
├── requirements.txt        # pinned Python dependencies
├── docker-compose.yml      # optional: containerize DB/reverse proxy
├── config/                 # Django settings package
│   ├── __init__.py         # loads base settings
│   ├── base.py             # common settings (INSTALLED_APPS, middleware, databases)
│   ├── dev.py              # development settings (DEBUG=True, SQLite)
│   └── prod.py             # production settings (DEBUG=False, allowed hosts, static root)
├── apps/                   # Django project applications
│   ├── accounts/           # Okta OIDC auth, role/group models, admin panel
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── forms.py
│   │   └── serializers.py  # DRF serializers for API endpoints
│   ├── jobs/               # models for Job requests
│   │   ├── models.py
│   │   ├── views.py        # user forms, list/detail views
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── api.py          # DRF viewsets for SPA usage
│   ├── tasks/              # models for Tasks (standalone or child of Job)
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── api.py      
│   │   └── admin.py
│   ├── approvals/          # approval routes and approval instance logic
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── api.py
│   │   └── admin.py
│   ├── notifications/      # e‑mail and in‑app alerts using Graph API
│   │   ├── utils.py        # send_email_via_graph(), Graph token management
│   │   ├── signals.py      # Signals to schedule notifications on job/task events
│   │   ├── tasks.py        # optional Celery tasks for async sending
│   │   └── templates/      # e‑mail templates
│   ├── dashboard/          # aggregated metrics, charts, filters
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── api.py
│   │   └── templates/
│   └── ...
├── frontend/               # front-end (React/Vue) project
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── index.jsx       # entrypoint for SPA
│   │   ├── App.jsx
│   │   ├── theme/
│   │   │   ├── variables.css       # CSS variables for light/dark mode
│   │   │   └── glass.css           # utility classes for glass‑morphism
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Card.jsx            # generic glass‑morphic container
│   │   │   ├── Charts.jsx          # wrappers around Chart.js or ECharts
│   │   │   └── ...
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── CreateJob.jsx
│   │   │   ├── CreateTask.jsx
│   │   │   ├── Manage.jsx
│   │   │   ├── Execute.jsx
│   │   │   ├── Approvals.jsx
│   │   │   ├── Release.jsx
│   │   │   ├── ViewDetail.jsx      # job/task detail with history
│   │   │   └── Settings.jsx        # default preferences (roles, flows, directories)
│   │   └── services/
│   │       ├── api.js              # Axios fetcher for DRF endpoints
│   │       └── auth.js             # Okta OIDC integration
│   └── public/
│       └── index.html
├── static/                  # compiled CSS and JS (served by Django in prod)
├── media/                   # file uploads (temporary when using local storage)
└── docs/
    └── architecture_plan.md # this document
```

### Explanation of folders

- **`config/`** holds environment‑specific settings.  `base.py` defines common settings (INSTALLED_APPS, database connections, logging, etc.), while `dev.py` and `prod.py` override them.  Keep secret keys in `.env` and load via `dotenv`.

- **`apps/`** contains Django applications.  Each app is self‑contained with models, views, templates and API endpoints.  Splitting jobs, tasks, approvals, accounts, dashboard, and notifications allows modular development.  Serializers and viewsets in each app feed a **REST API** (with Django REST Framework) consumed by the front end.

- **`frontend/`** is a full SPA built with React (or Vue) and Vite.  Use React context or a state manager (e.g., Redux) to handle global data (current user, theme).  The theme directory defines CSS variables (color palette, blur amounts) and glass‑morphism classes to ensure consistent design.  A `Settings.jsx` page allows users to pick default values (user preferences, roles, approval flows, directories).  For dark mode, toggle a `data-theme` attribute on the root element, switching CSS variables.

- **`static/` and `media/`** store compiled assets and uploaded files respectively.  In production, `static/` is served by Django or a reverse proxy.  If internal storage is used, `media/` is a network path accessible to the server.  For SharePoint, our app does not store files locally; instead, it captures metadata (file name, folder path, link) after uploading via the Graph client.

- **`docs/`** contains architecture diagrams, onboarding guides and this design document.  Use Markdown or diagrams when collaborating.

## Back‑end architecture

### Django applications

1. **accounts app:**  
   - Implements Okta OIDC authentication.  Use `mozilla-django-oidc` to integrate with Okta’s authorization code flow.  After login, map Okta groups/claims to local roles.  Provide a `User` model extending `AbstractUser` with fields for department and default preferences (e.g., view filters, default approval route).  Implement `Group`, `Department` models for scoping rules.
   - Create a management command to sync roles and departments from Okta as needed.  Consider SCIM if available.

2. **jobs app:**  
   - `Job` model stores job requests (title, description, type, status, priority, requester, department, due date, default approval route, attachments, etc.), plus `parent` (Optional[Job]) for hierarchical jobs.  Each job may have multiple tasks (through a ForeignKey in the `tasks` app).
   - Views/API provide CRUD operations for jobs with permission checks.  Use class‑based views (e.g., `ListView`, `DetailView`) for server‑rendered pages or DRF `ModelViewSet` for API.  Provide search and filter endpoints (e.g., by status, department, date, priority, custom field values, demographics).  Expose metrics API endpoints for charts.
   - Use Django signals to create history entries when a job’s status, assignee or approval state changes.

3. **tasks app:**  
   - `Task` model: a task may belong to a job but can also be standalone (job nullable).  Fields include description, status, assignee, due date, attachments, created_by, etc.  Keep a `history` relationship (many‑to‑one) to track all updates.  Provide forms/API methods to create tasks either via parent job (creating micro tasks) or directly in the Create Task page.
   - Task workflows mirror job flows but can skip triage; a Group Leader can directly assign tasks.  Optionally, tasks can go through the approval and release flow if needed.

4. **approvals app:**  
   - `ApprovalRoute` model defines the standard sequence of approvers for each approval type (release, delete, update, descope) per department or team.  Admins maintain these via the admin panel or a dedicated UI.  Each `Route` contains ordered `ApproverRole` entries.
   - `Approval` model records ongoing approval steps: job/task, approval type, assigned approver, decision (pending/approved/rejected), comment, timestamp.  When a job/task is submitted for approval, instantiate `Approval` rows according to the selected route.  If the “custom route” checkbox is ticked, allow the Group Leader to pick or reorder approvers.

5. **notifications app:**  
   - Provides a unified interface for sending notifications.  Implement a helper `GraphEmailClient` that acquires a delegated Graph token using MSAL (client ID, tenant, redirect URL, etc.) and sends messages via the `/sendMail` endpoint.  The client sets the `from` property to the configured no‑reply address and sets `saveToSentItems=false` to avoid errors when the sending address has no mailbox[2](https://learn.microsoft.com/en-us/graph/outlook-send-mail-from-other-user).  The user account used to authenticate must have **Mail.Send.Shared** and Exchange **Send As** or **Send on Behalf** permissions for the distribution list[2](https://learn.microsoft.com/en-us/graph/outlook-send-mail-from-other-user).  Optionally, support a fallback method using Python’s `smtplib` for local SMTP relay.
   - Asynchronous sending can leverage Celery + Redis (or Django channels) to avoid blocking requests.  Configure Celery to run with Django and a message broker (e.g., Redis) to send emails in the background.
   - Define `Notification` models to store the message metadata and status, and generate in‑app notifications for users.  Provide user preferences for e‑mail vs. in‑app notifications.

6. **dashboard app:**  
   - Aggregates metrics across jobs, tasks and approvals.  Use queries to compute counts (open jobs by status, tasks per assignee, average turnaround time, per‑department workloads, etc.).  Expose as DRF endpoints returning JSON for charts.  The front end visualizes this via Chart.js or ECharts.  Provide filters for date ranges, departments, roles and demographics (e.g., distribution of jobs per user group).  Because some metrics contain sensitive data (e.g., user productivity), restrict access based on roles (e.g., only Group Leaders or Admins can see certain dashboards).

### Common components

- **History tracking:**  Each `Job` and `Task` has a generic relation to `HistoryEntry` capturing who changed what and when.  Use `django-simple-history` or a custom model triggered via signals.  In the detail view, display a timeline at the bottom (e.g., vertical list or card view) showing creation, assignments, status changes, file uploads, approvals and comments.

- **File uploads:**  Use `django-storages` for storing files locally or in Azure/SharePoint.  For local or network storage, configure `MEDIA_ROOT` pointing to a share accessible to Waitress.  For SharePoint, create a foreign key `FileAttachment` with metadata fields (name, size, url, job/task reference).  When a file is uploaded, call the SharePoint API to upload and store the returned drive item link.  Use background tasks for large files.

- **Security:**  Enforce TLS via a reverse proxy (e.g., Nginx or Windows IIS).  Use `django-axes` or similar library to lock out brute force logins.  Use JWT or session cookies along with Okta’s ID tokens.  Configure 30‑minute inactivity timeouts in both Okta and Django sessions.

- **Testing & CI/CD:**  Write unit and integration tests for each app (models, views, API).  Use `pytest` or Django’s built‑in test runner.  Configure a CI pipeline (GitHub Actions/Azure Pipelines) to run tests, lint code and build the front‑end.  Deploy to staging environment automatically; manual approval triggers production deployment.  If containerizing, create a `Dockerfile` to build the Django + Waitress image, and use `docker-compose` to orchestrate DB, Redis and the application.


## Front‑end architecture

1. **Framework and build tool:**  Use **React** with Vite (or Next.js for server‑side rendering).  Define a single‑page application (SPA) that interacts with the back‑end via REST APIs.  Alternatively, use Vue 3.  Pick one based on team expertise.

2. **Theme system:**  Create a design system with glass‑morphism tokens: 
    - Define CSS variables for base colours (primary, secondary, accent), glass blur radius, opacity levels and shadow settings.  For dark mode, provide alternative values (e.g., darker background, lighter frosted panels).  Use `prefers-color-scheme` or a user toggle.
    - Build components such as `Card`, `Modal`, `Button`, and `Sidebar` that encapsulate the glass aesthetic.  Use `backdrop-filter: blur(20px)` and semi‑transparent backgrounds to create frosted panels[3](https://www.ramotion.com/blog/what-is-glassmorphism/).  Provide fallback for browsers lacking blur support.

3. **Routing and pages:**  Use a router (e.g., React Router) to map URL paths to page components.  Each page corresponds to a major step in the workflow:
   - **Dashboard** – Summary widgets and charts; filters for date, department, role; ability to toggle metrics via checkboxes; light/dark theme switcher.
   - **Create Job** – Form for job requests with fields: title, description, job type, due date, priority, attachments.  Provide a **checkbox** for approval route: default vs. custom.  On customizing, allow selection/reordering of approvers.
   - **Create Task** – Form like Create Job but for stand‑alone tasks.  If created within a job, pre‑populate job reference.
   - **Manage** – For group leaders; list of untriaged jobs/tasks.  Provide accept, reject, hold and assign actions.  Include buttons to create micro‑tasks.
   - **Execute** – For assignees; list tasks assigned to current user or their team.  Provide progress updates, file uploads, comment threads.
   - **Approvals** – For approvers; show tasks/jobs awaiting approval.  Provide options to approve/reject with comments and view attached files/history.  Support filters by approval type (release, update, delete, descope).
   - **Release** – Show tasks/jobs that passed approvals; allow group leader to finalize release (mark complete, send final notifications).
   - **ViewDetail** – Display a job or task with its fields, attachments, and history timeline.  Provide editing of fields where permitted (e.g., group leader or system admin).  Include a filter panel to change which columns/metrics appear (e.g., by user, by priority, demographics).  Provide export options (CSV/Excel) if needed.
   - **Settings** – Page for administrators to configure defaults: user roles, approval routes, default directories (network/SharePoint), default flows, group membership and view scope rules.  Provide a UI for mapping Okta groups to internal roles and for defining department boundaries.

4. **State management:**  Use context or a state library (Redux or Zustand) to manage global state (user session, theme selection, filter settings).  Persist user preferences (e.g., default filters, theme) in local storage or in the back end for cross-device consistency.

5. **Accessibility:**  Ensure adequate contrast between text and backgrounds.  Provide alt text for icons and images.  Support keyboard navigation and screen readers.  For custom components, use ARIA roles.


## Workflow and permissions

- **Create Job vs. Create Task:**  A job request flows through triage, task assignment, execution, approval and release.  A stand‑alone task bypasses the job request form and appears directly in Manage.  Both flows support attachments, comments and approvals.

- **Role assignments:**  Administrators define roles and map them to Okta groups.  Group Leaders manage job/task assignments for their department.  Approvers may be in multiple departments; the approval route ensures the correct sequence.

- **Viewing scope:**  In the View/Update module, users can browse jobs and tasks.  Filtering options include status, date, department, assignee, requester, priority, and custom tags.  Default filters are loaded from the user’s preferences.  Access is restricted: a user can view items in their groups/departments or those where they appear in the audience list.  The system uses row‑level permissions in the ORM to enforce these rules.

- **Customizable filters and demographics:**  The View/Update page includes filter panels and interactive charts.  Users can add/remove filters (e.g., by gender distribution, location) and adjust visuals (e.g., bar chart vs. pie chart).  Use Chart.js or ECharts; the back end sends aggregated counts by demographic category.

- **Approval route selection:**  On the creation form, include a checkbox labelled “Use default approval route” with a description; if unchecked, display an interface to build a custom route by selecting approvers and ordering them.  Save the resulting route to `ApprovalRoute` or a one‑off route tied to the job/task.  When a task/job is submitted for approval, instantiate `Approval` rows accordingly.


## Development & deployment instructions

1. **Set up the repository.**  
   - Install Python (≥3.11) and Node.js (≥18).  
   - Clone the repository and run `python -m venv venv` followed by `source venv/bin/activate` (Linux) or `venv\Scripts\activate` (Windows).  
   - Install back‑end requirements: `pip install -r requirements.txt`.  
   - Inside `frontend/`, run `npm install` to install front‑end dependencies.

2. **Configure environment variables.**  Copy `.env.example` to `.env` and set values for `SECRET_KEY`, `DATABASE_URL`, `OKTA_CLIENT_ID`, `OKTA_CLIENT_SECRET`, `OKTA_ISSUER`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `TENANT_ID`, `NO_REPLY_ADDRESS`, `SHAREPOINT_SITE_ID`, etc.

3. **Run development servers.**  
   - Start PostgreSQL (or rely on SQLite for development).  Run database migrations with `python manage.py migrate`.  
   - Start Django’s development server: `python manage.py runserver`.  
   - Build the front‑end: inside `frontend/`, run `npm run dev` for hot reloading.  Configure Vite proxy to forward `/api/` calls to `http://localhost:8000`.  The SPA will run at `http://localhost:5173` (or a chosen port).

4. **Set up superuser and initial data.**  
   - Run `python manage.py createsuperuser` and follow the prompts.  
   - Log in to the Django admin at `/admin/` and define initial roles, departments, and default approval routes.  
   - Optionally, seed sample data via fixtures or a custom management command.

5. **Deploy to production.**  
   - Build static assets: inside `frontend/`, run `npm run build`.  This outputs minified JS/CSS to `frontend/dist/` which Django collects to `static/` via `python manage.py collectstatic`.  
   - Use Waitress to serve Django: for example, `waitress-serve --port=8000 config.asgi:application` or deploy with Uvicorn if using async features.  Place a reverse proxy (Nginx or Windows IIS) in front to handle HTTPS and static file delivery.  
   - Configure the Windows 11 host with a static IP and add DNS entries for your domain (e.g., `designportal.company.com`).  Use `NSSM` or `PM2` to run Waitress as a service.  
   - Set up scheduled tasks (cron or Windows Task Scheduler) for periodic jobs (e.g., cleaning expired sessions, synchronizing Okta groups).


## Next steps

1. **Define detailed UI specifications.**  Identify the exact fields, controls and interactions on each page (e.g., Create Job form fields, Manage table columns, filter components).  Create wireframes or prototypes incorporating glass‑morphism and dark/light themes.

2. **Implement design system.**  Choose or build a component library with glass‑morphism tokens.  Document the usage guidelines (opacity, blur amounts, contrast) to maintain visual consistency and accessibility[3](https://www.ramotion.com/blog/what-is-glassmorphism/).

3. **Configure Okta and Graph.**  Register the application with Okta and Microsoft Entra ID (Azure AD).  Grant `openid` and `profile` scopes in Okta.  Register Graph API permissions `Mail.Send.Shared` and `Files.ReadWrite.All` (for SharePoint uploads).  Assign Exchange *SendAs* or *SendOnBehalfOf* rights for the `Ticketing_Portal@company.com` distribution list to the service account[2](https://learn.microsoft.com/en-us/graph/outlook-send-mail-from-other-user)[1](https://practical365.com/sendas-send-on-behalf-of-mail-objects/).

4. **Develop iteratively.**  Begin with the accounts and jobs apps, implement core CRUD flows and authentication, then expand to tasks, approvals, notifications and dashboard.  Use API documentation to define endpoints consumed by the SPA.

5. **Security and testing.**  Conduct security reviews: enforce strong passwords, multi‑factor via Okta, CSRF protection, and secure cookie settings.  Write unit tests for each model, view and API endpoint.  Validate Graph permissions and ensure least‑privilege principles.

By following this architecture and carefully applying glass‑morphism principles, your team can build a modern, accessible and secure design‑job portal tailored to your organization’s workflow.  The modular project structure encourages collaboration between back‑end and front‑end developers and makes it straightforward to maintain and extend the system over time.

