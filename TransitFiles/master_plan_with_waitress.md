# Comprehensive Full‑Stack Project Structure and Setup Guide

This document delivers a **complete blueprint** for building a design‑job/task management portal that meets all requirements discussed previously.  It deliberately avoids code snippets and focuses on the **skeleton structure**, the **data model**, the **user‑experience flows**, and the **steps to get started**.  The technology stack uses **Python/Django** with Django REST Framework (DRF) for the backend, **React** for the front‑end, and **Waitress** as the WSGI server to host the Django application on a Windows 11 workstation.  

## 1. Goals and Key Features

1. **Multi‑Step Request Forms** – Break long forms into logical pages (basic details, approvals, team‑specific fields, attachments, line items, review) to reduce cognitive load and improve completion rates.  
2. **Dynamic Team‑Dependent Fields** – Each design team (PCB, Drawing, Hardware, Firmware) may require special fields.  Define these in configuration tables so the form wizard can render them dynamically without altering the database schema.  Supplementary data is stored as JSON.  
3. **Inline Editable Tables** – Provide an embedded spreadsheet‑like table for listing multiple items (such as BOM parts).  Each row is stored separately in line‑item tables.  
4. **Attachments and Artifacts** – Users must be able to upload design files (drawings, schematics, code, etc.).  Files are stored in a secure repository (SharePoint, OneDrive, or local file store) and tracked via an attachments table.  
5. **Role‑Based Approvals** – Each request goes through a defined approval route.  Approvers are selected via a directory look‑up People Picker.  Ordinary users see only pre‑configured approvers; administrators and group leaders can search the entire directory.  
6. **Default Approvers and Routes** – For efficiency and compliance, each design team and request type has default approvers and an approval route (sequence of approval steps).  Administrators manage these defaults.  
7. **Role‑Based Access Control (RBAC)** – Authentication ties into Azure AD/Okta; user roles (Admin, GroupLeader, User) and group memberships determine who can create, view, edit or approve requests.  
8. **Windows‑Friendly Deployment** – The backend runs under **Waitress**, a production‑grade WSGI server that supports Windows, while the front‑end is served via `npm start` or a static file server.  This is suitable for local development and intranet deployment on Windows 11.

## 2. High‑Level Architecture

**Backend (Django/DRF)**  
- **Django** handles routing, models and admin; **Django REST Framework** exposes API endpoints.  
- **PostgreSQL** stores core entities (users, groups, jobs, tasks, line items, attachments, approval routes, design teams, defaults).  
- **JSONField** is used to store dynamic custom fields and other flexible metadata (like approver IDs and watchers).  
- **Azure AD/Okta integration** provides authentication; user/group data is read from token claims and stored in local tables for authorization.  
- **Microsoft Graph** is called by the backend to perform directory searches for the People Picker (Admins and Group Leaders only).  
- **Waitress** hosts the Django application on Windows; the server listens on a configurable port.

**Front‑End (React)**  
- A React application with a modern **glass‑morphism** aesthetic.  
- A **FormWizard** component renders multi‑page forms based on JSON definitions from the backend.  
- A **PeoplePicker** component calls backend endpoints to fetch default approvers and, if permitted, search the directory.  
- An **EditableTable** component enables inline row editing.  
- **Authentication context** maintains user roles and tokens for conditional rendering and access control.  
- The UI communicates with the backend via HTTPS, sending and receiving JSON.  

**Configuration and Management**  
- Administrators manage design teams, form definitions, approval routes, and default approvers via an admin dashboard.  
- Only users with the right roles can modify configuration tables; changes take effect immediately without code changes.  

## 3. Database Schema Overview (No Code)

The database is normalized to ensure integrity while using JSON fields for flexibility.  Here is a summary of the tables and their relationships:

| Table | Purpose | Key Relationships |
|------|---------|------------------|
| **User** | Stores portal users with ID, Azure AD object ID, email, display name, and role (Admin, GroupLeader, User). | Belongs to one or more Groups via UserGroup membership.  Users create Jobs/Tasks and appear in approver/watch lists. |
| **Group** | Represents company departments or design teams (e.g. PCB, Hardware).  Optionally stores a corresponding Azure AD group ID. | Has many users.  Jobs belong to a Group to restrict visibility. |
| **UserGroupMembership** | Joins users and groups to reflect group membership. | Many‑to‑many link between Users and Groups. |
| **DesignTeam** | Defines each design discipline; includes a name and a **form definition JSON** for team‑specific fields; references a default approval route. | Referenced by Jobs and Tasks. |
| **ApprovalRoute** | Contains a JSON array defining the sequence of approval roles or specific user IDs.  Each route has a name and an order of steps. | Referenced by Jobs and Tasks; managed by Admins. |
| **DefaultApprover** | Stores a list of default approver IDs (Azure AD object IDs) for each design team and request type. | Used to pre‑populate the People Picker for standard users. |
| **FormDefinition** | Stores base multi‑page form definitions for each request type (e.g. “Job Request,” “Task”). Each definition lists steps, fields, labels, and validation rules. | Combined with DesignTeam.form_definition to create dynamic forms. |
| **Job** | Represents a top‑level design request. Contains ID (generated on creation), title, description, type, priority, status, due date, group, design team, approval route, and a **metadata JSON** field for custom fields, approver IDs, watchers, and other items. | Has many Tasks, Line Items, Attachments and Comments; belongs to a Group and a DesignTeam. |
| **Task** | Similar to Job but may link back to a parent Job. Contains assignee, group, design team and metadata. | Can exist independently or under a Job; has line items, attachments and approvals. |
| **JobLineItem / TaskLineItem** | Each row from the editable table is stored here with an order index and JSON data. | Belongs to a Job or Task.  Allows arbitrary columns as defined in the form. |
| **Attachment** | Holds metadata about uploaded files (file name, path, size, version, uploader).  The physical file resides on SharePoint/OneDrive or local storage. | Linked to a Job or Task. |

Using **JSON** in the metadata fields means new custom fields can be added by updating the design team’s `form_definition` without altering the database schema.  

## 4. Front‑End Structure and Flow

### 4.1 Page Hierarchy

- `/dashboard` – Main overview: charts of jobs and tasks by status, upcoming approvals, personal tasks.  
- `/jobs/new` – Wizard for creating a new Job.  
- `/jobs/{id}` – Detail page for viewing and editing a Job.  
- `/tasks/new` – Wizard for creating a new Task.  
- `/tasks/{id}` – Task detail page.  
- `/approvals` – List of approvals awaiting the user’s decision.  
- `/admin` – Admin console to manage users, groups, design teams, approval routes, default approvers and form definitions.  
- `/config` – Optional advanced configuration editor for JSON form definitions.  

### 4.2 Key Components

1. **Layout** – Provides the common header, footer, side navigation and theme switcher.  
2. **FormWizard** – High‑level component that manages the multi‑step flow.  It loads form definitions via the API, displays each step as a separate page, validates required fields before advancing, and persists form state across steps.  
3. **FieldRenderer** – Renders a field based on its type (text, textarea, number, date, select, multi-select, file, table).  Accepts a field definition and binds user input to the wizard state.  
4. **EditableTable** – Presents a table with columns defined in the form configuration.  Users can add, edit and remove rows inline.  The results map to line‑item objects saved in separate tables.  
5. **PeoplePicker** – Input component for selecting users.  For ordinary users, it displays a list of default approvers fetched from the API.  For group leaders/admins, it supports free search via a backend directory query.  Selected users appear as chips.  
6. **AttachmentUploader** – Provides drag‑and‑drop file upload with progress feedback.  Once uploaded, attachments are stored, and the component updates the state to reference the uploaded file.  
7. **RBAC Guard** – Ensures components or pages are only accessible to users with sufficient roles.  The front‑end reads token claims to decide which pages to show.  

### 4.3 User Flow for Job Creation

1. **Open the Job Wizard** – User navigates to `/jobs/new`.  The wizard fetches the base form definition from the `FormDefinition` entry for the “job” type and lists available design teams.  
2. **Step 1 – Basic Info** – Enter title, description, priority, due date and choose a design team.  
3. **Step 2 – Approvals** – The People Picker loads default approvers for the chosen team and request type.  If the user is a group leader or admin, they may search the directory to add extra approvers.  The wizard also lets users specify watchers.  
4. **Step 3 – Team‑Specific Fields** – The wizard merges the base form with fields defined in the selected design team’s `form_definition` (e.g. layer count, board size).  Required fields are marked.  
5. **Step 4 – Attachments** – Users upload design files and documents.  Files are stored and tracked.  
6. **Step 5 – Line Items** – If needed, users add rows (e.g. BOM items) via the editable table.  
7. **Step 6 – Review & Submit** – The wizard displays a summary of all entries for final confirmation.  Upon submission, the backend validates required fields, stores the job with a system‑generated ID, attaches line items and files and sets up the approval route.  
8. **Completion & Notification** – The user is redirected to the job detail page and the first approver is notified.  

## 5. Backend Project Skeleton (Django)  

- **project/ (root)**  
  - `manage.py` – Standard Django management script.  
  - **design_portal/** – Main Django project.  
    - `settings.py` – Configures database (PostgreSQL), authentication (Azure AD / Okta via `django-auth-adfs` or similar), installed apps (REST Framework, CORS, authentication), static/media directories and Waitress for production.  
    - `urls.py` – Declares API routes, static file routes and admin routes.  
    - `wsgi.py` – Entry point for Waitress; Waitress loads this module to run the Django application.  
  - **core/** – Custom application containing our business logic.  
    - `models.py` – Defines dataclasses described in section 3 (User, Group, DesignTeam, Job, Task, LineItem, Attachment, ApprovalRoute, DefaultApprover, FormDefinition).  
    - `serializers.py` – Converts model instances to/from JSON for DRF.  
    - `views.py` – DRF viewsets: JobViewSet, TaskViewSet, DesignTeamViewSet, ApprovalRouteViewSet, DefaultApproverViewSet, FormDefinitionViewSet, and endpoints for attachments.  
    - `permissions.py` – Custom DRF permission classes to enforce RBAC rules (e.g. only admins can search users).  
    - `urls.py` – API endpoints with DRF routers.  
    - `admin.py` – Registers models in Django admin for convenient management.  
    - `services/` – Contains helper modules for Graph API calls, file storage operations, and approval workflow logic.  
- **requirements.txt** – Lists dependencies: Django, django‑rest‑framework, psycopg2, celery (optional), django‑auth‑adfs, msal, Waitress, etc.  

To start development on Windows 11, set up Python and PostgreSQL, then run `python -m venv venv`, activate it, install dependencies via `pip install -r requirements.txt`, apply migrations, and start the development server with `python manage.py runserver`.  To host on Waitress for local deployment, use `waitress-serve --port=8000 design_portal.wsgi:application`.

## 6. Running the Backend with Waitress on Windows 11

1. **Install Waitress**: In your virtual environment, install Waitress: `pip install waitress`.  
2. **Ensure wsgi.py is Correct**: Django automatically creates `design_portal/wsgi.py`. Waitress references this file.  
3. **Start Waitress**: From the project root, run:  
   ```powershell
   waitress-serve --listen=*:8000 design_portal.wsgi:application
   ```
   Waitress will serve the Django application on port 8000.  You can test it by navigating to `http://localhost:8000/api/` in your browser.  
4. **Service or Task Scheduler**: For a persistent local server, create a Windows service or scheduled task that runs this command at startup.  
5. **Front‑End Access**: Ensure that your React front‑end calls the API at `http://localhost:8000` (adjust CORS settings in `settings.py`).  
6. **Static and Media Files**: For production deployment, serve static files via WhiteNoise or another mechanism. In local intranet scenarios, you can serve them directly from Django by setting `STATIC_URL` and `MEDIA_URL` and enabling `django.contrib.staticfiles`.

## 7. How to Get Started

Follow these high‑level steps to bootstrap the project:

1. **Prepare Development Environment**:  
   - Install **Python 3.10** and **Node.js 18** on your Windows machine.  
   - Install **PostgreSQL** (or use another DB; adjust `settings.py` accordingly).  
   - Verify access to Azure AD/Okta for SSO and to Microsoft Graph for directory lookup.  
2. **Version Control**: Initialize a Git repository and structure it as described above (separate frontend and backend directories).  
3. **Configure the Backend**:  
   - Set up a virtual environment: `python -m venv venv && venv\Scripts\activate`.  
   - Install dependencies: `pip install -r requirements.txt`.  
   - Configure `settings.py` for database connection, allowed hosts, CORS, authentication (Azure AD/Okta), and static file paths.  
   - Run `python manage.py migrate` to create tables.  
   - Create a superuser to access Django admin: `python manage.py createsuperuser`.  
   - Optionally load initial data for design teams, default approvers and routes.  
4. **Configure the Front‑End**:  
   - Use `npx create-react-app` or `pnpm create next-app` to scaffold the UI.  
   - Install UI libraries (e.g. Material‑UI or Chakra UI) and other dependencies (axios, msal-browser).  
   - Create the pages and components outlined in section 4.  
   - Configure the front‑end proxy or environment variables to point to the Django API.  
   - Implement authentication flow: retrieve the JWT from the backend after SSO login (or use MSAL in front‑end if performing interactive sign‑in).  
5. **Run and Test**:  
   - Start Django via `python manage.py runserver` (development) or `waitress-serve` (deployment).  
   - Run `npm start` to run the React development server.  
   - Navigate to the form pages and test the flow (creating jobs, tasks, attachments, approvals). Validate that required fields are enforced and that only authorized roles can search the directory or modify approvals.  
6. **Deployment**:  
   - For a local intranet or pre‑production environment on Windows 11, run Waitress and serve static files using WhiteNoise or Nginx for the back‑end.  
   - For wide deployment, host Django on an IIS or Docker container using Waitress as WSGI, and serve the React build (run `npm run build`) via a simple Nginx or Node static server.

## 8. Summary

This plan provides a **complete skeleton** for delivering a flexible design‑job/task portal using **Django/DRF** on the backend and **React** on the front‑end, with Waitress for hosting.  It outlines the database schema, describes each page and component of the UI, and presents the steps to initialise, configure and run the project on a Windows 11 local server.  All previously discussed requirements—multi‑step forms, dynamic team‑specific fields, editable tables, attachments, directory lookup with role‑based restrictions, default approvals and routes—are integrated into this cohesive structure without dropping into code.  Use this document as a reference to organize and launch the project with confidence.
