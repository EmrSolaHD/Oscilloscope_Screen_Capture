# Complete Full-Stack Architecture Plan and Project Setup Guide

This document provides a **comprehensive blueprint and project setup guide** for building a dynamic design‑job/task management portal. It consolidates earlier discussions and adds missing detail about how to bootstrap the project, structure the codebase, design the database, implement multi‑page request forms and People Picker, and support role‑based approvals. The plan is intended for an engineering team familiar with web development but needing clear guidance to get started and ensure all features are captured.

---

## 1. Overview and Objectives

The goal is to develop a modern web portal that allows users to request design work (PCB, Drawing, Hardware, Firmware, etc.), create tasks, manage approvals, attach artifacts, and track work progress. The portal should support:

- **Multi‑page forms** for complex requests.
- **Dynamic fields** based on selected design team or request type.
- **Inline editable tables** for line‑item data.
- **Attachments** with version control.
- **Role‑based approval workflows** with default routes.
- **People Picker** integrated with Azure AD/Okta for selecting approvers/watchers.
- **Role-based access control** (Admin, Group Leader, User) to restrict features.

The system uses a **React/Next.js** front end, **Node.js/Express (or NestJS)** back end, **PostgreSQL** database via **Prisma** ORM, and integrates with **Azure AD (Microsoft Graph API)** for identity and user lookup. It adheres to glass‑morphism UI design with light/dark modes.

---

## 2. Project Bootstrap Instructions

These steps guide you through setting up the repository, installing dependencies, configuring environment variables, and scaffolding the front‑end and back‑end code.

### 2.1 Repository Layout

We use a monorepo structure with separate `frontend` and `backend` directories:

```
root/
├─ README.md
├─ .env.example              # Template environment variables
├─ frontend/                 # Next.js app
│  ├─ package.json
│  ├─ next.config.js
│  ├─ tsconfig.json
│  ├─ public/
│  ├─ pages/
│  ├─ components/
│  ├─ contexts/
│  ├─ services/
│  ├─ styles/
│  └─ utils/
├─ backend/                  # Node.js API server
│  ├─ package.json
│  ├─ tsconfig.json
│  ├─ src/
│  │  ├─ index.ts            # entry point
│  │  ├─ controllers/
│  │  ├─ routes.ts
│  │  ├─ middleware/
│  │  ├─ models/
│  │  ├─ prisma/
│  │  │  └─ schema.prisma
│  │  └─ utils/
│  └─ migrations/
├─ docker-compose.yml (optional)
└─ docker/ (optional)
```

### 2.2 Environment Variables

Create a `.env` file at the project root (and separate files in `frontend/` and `backend/` if you wish). Example variables:

- **Back end**:
  - `DATABASE_URL`: connection string for PostgreSQL (e.g., `postgresql://user:password@localhost:5432/design_portal`)
  - `GOOGLE_CLIENT_ID` / `OKTA_CLIENT_ID` / `MICROSOFT_CLIENT_ID`: credentials for OAuth if integrating with Okta or Azure AD.
  - `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `GRAPH_TENANT_ID`: app registration for Microsoft Graph.
  - `JWT_SECRET`: secret used to sign/verify JWT tokens if issuing your own tokens.

- **Front end**:
  - `NEXT_PUBLIC_API_URL`: base API URL (e.g., `http://localhost:4000/api`).
  - `NEXT_PUBLIC_GRAPH_SCOPE`: Graph scopes (e.g., `User.ReadBasic.All`).

**Note**: Use `dotenv` or your deployment environment's secret service to inject these variables securely.

### 2.3 Installing Dependencies

Install dependencies for both projects:

```bash
# Clone repository
git clone <repo-url>
cd root

# Install backend dependencies
cd backend
npm install

# Install frontend dependencies
cd ../frontend
npm install
```

Recommended versions:

- Node.js 20.
- Next.js 14 or higher.
- Prisma 5.
- Express or NestJS for the API.
- React 18.

### 2.4 Running Locally

```bash
# Start PostgreSQL (if you haven't already). you can use docker-compose:
# docker-compose up -d postgres

# Apply database migrations
cd backend
npx prisma migrate dev --name init

# Seed initial data (optional script for design teams, default tables)
npx ts-node src/utils/seed.ts

# Start backend server (development mode)
npm run dev

# Start frontend
cd ../frontend
npm run dev

# Access the portal at http://localhost:3000
```

### 2.5 Deploying to Production

Deploy the front end to Vercel, Netlify or Azure Static Web Apps. Deploy the back end to Azure App Service or AWS ECS. Use Azure Database for PostgreSQL or Cloud SQL for production. Set environment variables in the hosting environment and set up a CI/CD workflow via GitHub Actions.

---

## 3. Detailed Folder Structure

### 3.1 Front End

- **pages/** – Contains page components following Next.js file routing.  Examples:
  - `pages/index.tsx` – Redirects to `/dashboard`.
  - `pages/dashboard.tsx` – Displays metrics and charts.
  - `pages/jobs/new.tsx` – Multi‑step form for creating a job.
  - `pages/jobs/[id].tsx` – View/edit job details.
  - `pages/tasks/new.tsx`, `pages/tasks/[id].tsx` – For tasks.
  - `pages/approvals.tsx`, `pages/management.tsx`, `pages/admin/*.tsx`, etc.

- **components/** – Reusable UI components:
  - `Layout.tsx` – Contains the glass‑morphism header, collapsible sidebar, and footer.
  - `FormWizard.tsx` – Implements multi‑step forms.
  - `FieldRenderer.tsx` – Renders form fields dynamically from JSON definitions.
  - `EditableTable.tsx` – Inline editable table for line items.
  - `PeoplePicker.tsx` – People Picker integrated with Microsoft Graph.
  - `ChartWidgets/` – Charts for dashboards.

- **contexts/** – React contexts for authentication, theme and form state persistence.

- **services/** – API wrapper using Axios or Fetch, plus Graph API integration.

- **styles/** – Global CSS, variables for light/dark themes, glass‑morphism tokens.

### 3.2 Back End

- **src/index.ts** – Sets up the Express server (or NestJS `main.ts`), configures middleware, routes and error handling.

- **controllers/** – Contains business logic for jobs, tasks, approvals and admin endpoints. Each file handles request validation, calls service functions, interacts with Prisma models, and sends responses.

- **routes.ts** – Maps API endpoints to controllers.

- **middleware/** – Includes authentication middleware (reads JWT/OAuth claims), RBAC middleware, validation helpers and error handling.

- **models/** – Contains Prisma models if using a service layer, or separate classes if necessary.

- **prisma/schema.prisma** – Defines the database schema (see Section 4). Also includes relations, enumerations, indexes and JSON fields.

- **utils/** – Helper functions (e.g. Graph API client, file upload to SharePoint, seed scripts).

---

## 4. Database Design & Entities

### 4.1 Core Schema

Below is a high‑level view of the key tables and relations (written in Prisma schema format). Comments explain major fields:

```prisma
// prisma/schema.prisma

model User {
  id         String   @id @default(uuid())
  aadObjectId String   @unique  // Azure AD object ID
  email       String   @unique
  displayName String
  role        Role
  groups      UserGroupMap[]
  jobs        Job[]     @relation("UserJobs", references: [id])
  tasks       Task[]    @relation("UserTasks", references: [id])
  createdAt   DateTime @default(now())

  // Additional user preferences or metadata can be stored here.
}

enum Role {
  ADMIN
  GROUP_LEADER
  USER
}

model Group {
  id           String   @id @default(uuid())
  name         String
  aadGroupId   String?  @unique // optional AD group mapping
  users        UserGroupMap[]
  designTeam   DesignTeam[]
}

model UserGroupMap {
  id       String  @id @default(uuid())
  userId   String
  groupId  String
  user     User    @relation(fields: [userId], references: [id])
  group    Group   @relation(fields: [groupId], references: [id])
}

model Job {
  id          String     @id @default(uuid())
  title       String
  description String
  type        String      // e.g. 'New Design', 'Update', 'Delete'
  priority    String
  status      String
  dueDate     DateTime?
  createdById String
  createdBy   User       @relation("UserJobs", fields: [createdById], references: [id])
  groupId     String?
  group       Group?     @relation(fields: [groupId], references: [id])
  designTeamId String?   // the design team ID from DesignTeam table
  designTeam  DesignTeam? @relation(fields: [designTeamId], references: [id])
  approvalRouteId String?
  approvalRoute ApprovalRoute? @relation(fields: [approvalRouteId], references: [id])
  metadata    Json
  lineItems   JobLineItem[]
  attachments Attachment[]
  tasks       Task[]     // tasks under this job
  createdAt   DateTime   @default(now())
  updatedAt   DateTime   @updatedAt
}

model Task {
  id            String   @id @default(uuid())
  parentJobId   String?
  parentJob     Job?     @relation(fields: [parentJobId], references: [id])
  title         String
  description   String
  priority      String
  status        String
  dueDate       DateTime?
  assigneeId    String?
  assignee      User?    @relation(fields: [assigneeId], references: [id])
  groupId       String?
  group         Group?   @relation(fields: [groupId], references: [id])
  designTeamId  String?
  designTeam    DesignTeam? @relation(fields: [designTeamId], references: [id])
  approvalRouteId String?
  approvalRoute ApprovalRoute? @relation(fields: [approvalRouteId], references: [id])
  metadata      Json
  lineItems     TaskLineItem[]
  attachments   Attachment[]
  createdAt     DateTime   @default(now())
  updatedAt     DateTime   @updatedAt
}

model JobLineItem {
  id       String   @id @default(uuid())
  jobId    String
  job      Job     @relation(fields: [jobId], references: [id])
  orderIndex Int
  data     Json
  createdAt DateTime @default(now())
}

model TaskLineItem {
  id       String   @id @default(uuid())
  taskId   String
  task     Task    @relation(fields: [taskId], references: [id])
  orderIndex Int
  data     Json
  createdAt DateTime @default(now())
}

model Attachment {
  id          String   @id @default(uuid())
  parentId    String   // ID of job or task
  parentType  ParentType
  fileName    String
  filePath    String
  mimeType    String
  size        Int
  version     Int      @default(1)
  uploadedById String
  uploadedBy   User    @relation(fields: [uploadedById], references: [id])
  createdAt   DateTime @default(now())

  @@index([parentId, parentType])
}

enum ParentType {
  JOB
  TASK
}

model DesignTeam {
  id           String    @id @default(uuid())
  name         String
  groupId      String
  group        Group      @relation(fields: [groupId], references: [id])
  formDefinition Json     // JSON describing additional fields for this team
  defaultRouteId String?
  defaultRoute   ApprovalRoute? @relation(fields: [defaultRouteId], references: [id])
  jobs          Job[]
  tasks         Task[]
}

model ApprovalRoute {
  id          String    @id @default(uuid())
  name        String
  routeSteps  Json      // JSON structure representing ordered approver stages
  jobs        Job[]
  tasks       Task[]
}

model DefaultApprover {
  id           String   @id @default(uuid())
  designTeamId String
  requestType  String
  approverIds  Json     // Array of AD object IDs of default approvers
  designTeam   DesignTeam @relation(fields: [designTeamId], references: [id])
}

model FormDefinition {
  id          String   @id @default(uuid())
  requestType String   @unique  // e.g. 'job', 'task'
  definition  Json     // Stored multi-page form definition
}
```

### 4.2 Data Model Explanation

- **User**: Each user corresponds to an Azure AD identity. Store only minimal profile and role; identity details remain in AD. The `role` column determines access (Admin = full access; Group Leader = manage within group; User = limited).  `groups` is a many‑to‑many relationship linking to the `Group` table.
- **Group**: Represents departments or design teams.  Each group is optionally connected to an AD group via `aadGroupId`.  Groups also link to `DesignTeam` entries.
- **Job & Task**: Core work items.  Both contain a `metadata` JSON field for dynamic attributes (custom fields, selected approver IDs, watchers, etc.) and references to design team, approval route, group and user relationships.  Tasks may reference a parent job or stand alone.
- **LineItems**: Store rows created via the editable table.  Each row is a JSON object representing dynamic columns.
- **Attachment**: Records metadata about uploaded files.  Actual file storage is external (SharePoint/OneDrive).  `parentType` can be JOB or TASK, and `parentId` points to the corresponding entity.
- **DesignTeam**: Stores design disciplines (PCB, Drawing, Hardware, Firmware).  Each team has a `formDefinition` JSON for custom fields and a reference to an `ApprovalRoute` (default) and a `Group` (for access).
- **ApprovalRoute**: Contains a JSON array describing the sequence of approver steps.  Each step might specify a role (GroupLeader, Admin) or user IDs.  Jobs and tasks reference approval routes.
- **DefaultApprover**: Stores default approver IDs per design team and request type.  Used to pre‑populate People Picker for ordinary users.
- **FormDefinition**: Holds multi‑page form definitions for each request type (e.g. `job`, `task`).  Each definition includes steps, fields, and conditional visibility rules.

This relational model normalizes data while allowing extension via JSON fields (and JSON arrays for dynamic fields).  Relationships enforce referential integrity and allow join queries for RBAC and approvals.

---

## 5. Multi‑Step Form Implementation

### 5.1 Form Definition Structure

Form definitions are stored in the **FormDefinition** table.  For example, a `job` form might have five steps:

```json
{
  "steps": [
    {
      "title": "Basic Info",
      "description": "General request details",
      "fields": [
        { "id": "title", "label": "Title", "type": "text", "required": true },
        { "id": "description", "label": "Description", "type": "textarea", "required": true },
        { "id": "type", "label": "Request Type", "type": "select", "options": ["New Design", "Update", "Delete"], "required": true },
        { "id": "designTeam", "label": "Design Team", "type": "select", "options": ["PCB", "Drawing", "Hardware", "Firmware"], "required": true }
      ]
    },
    {
      "title": "Stakeholders & Approvals",
      "description": "Add watchers and specify approvers",
      "fields": [
        { "id": "watchers", "label": "Watchers", "type": "peoplepicker", "allowSearch": true, "allowFreeSearchByRole": ["ADMIN", "GROUP_LEADER"], "defaultProvider": "/api/users/default-watchers" },
        { "id": "approvers", "label": "Approvers", "type": "peoplepicker", "required": true, "allowSearch": false, "allowFreeSearchByRole": ["ADMIN", "GROUP_LEADER"], "defaultProvider": "/api/users/default-approvers" }
      ]
    },
    {
      "title": "Custom Fields",
      "description": "Fields specific to the selected design team",
      "fields": [ { "reference": "DesignTeam" } ]
    },
    {
      "title": "Attachments",
      "description": "Upload related files",
      "fields": [
        { "id": "files", "label": "Upload Files", "type": "file", "multiple": true, "required": false }
      ]
    },
    {
      "title": "Line Items",
      "description": "Additional details (e.g. BOM)",
      "fields": [
        { "id": "lineItems", "label": "Line Items", "type": "table", "columns": [ { "id": "partNumber", "label": "Part Number", "type": "text", "required": true }, { "id": "quantity", "label": "Quantity", "type": "number", "required": true }, { "id": "unitPrice", "label": "Unit Price", "type": "number", "required": false } ] }
      ]
    },
    {
      "title": "Review & Submit",
      "description": "Confirm details before submitting",
      "fields": []
    }
  ]
}
```

The `reference: "DesignTeam"` instructs the form engine to pull supplemental fields from the selected `DesignTeam.formDefinition`.  `peoplepicker` field types specify whether free search is allowed and which roles can use it.  The `defaultProvider` property points to API endpoints that return default approvers or watchers based on the current user’s group and request type.

### 5.2 Form Wizard Behavior

- The wizard receives a `FormDefinition` from the API and parses its steps.  It displays step indicators and uses state to store field values.
- It includes a **Next** and **Back** button.  **Next** is disabled until all fields on the current step marked as `required` are filled.  Client‑side validation leverages the HTML `required` attribute and custom functions to check numeric ranges and patterns.
- If a step uses a `reference` to design team fields, the wizard dynamically inserts those fields after the user selects a design team.  It merges the design team’s `formDefinition` JSON with the base definition.
- On each step, the wizard can autosave progress to local storage or to a `Drafts` table via API calls.
- The final step displays a read‑only summary of all entered data (including line items and attachments) and the **Submit** button.

### 5.3 People Picker Integration

- The People Picker is a reusable component that renders either a “native” multi‑select from defaults or a search-enabled typeahead.  It uses the roles available in the user’s JWT to determine whether free search is allowed.
- When free search is triggered (Admin, Group Leader), it calls `GET /api/users/search?q=<term>` which invokes the Microsoft Graph API to find matching users.  Only minimal data (UPN, display name, object ID) is returned.
- For standard users, the People Picker calls `GET /api/users/default-approvers?designTeamId=...&requestType=...` or `GET /api/users/default-watchers` to load the default lists.  They can remove or reorder these but cannot add random names.
- Selected names are stored in `metadata.approverIds` and `metadata.watcherIds` in the final payload.  The back-end validates that non-admins did not add names outside of their defaults.

### 5.4 Attachments & Editable Tables

- The attachments field uses a drag‑and‑drop zone.  Files are uploaded to `/api/jobs/{id}/attachments` or `/api/tasks/{id}/attachments`.  The API uses MS Graph or SharePoint APIs to store the file and returns a path and version number.
- The inline table uses the `EditableTable` component.  It displays columns as defined in the form definition and allows adding/removing rows.  It validates each row and tracks `orderIndex` to preserve sorting.  On submit, it calls a dedicated API to insert `JobLineItem` or `TaskLineItem` records.

---

## 6. API Design & RBAC

### 6.1 Authentication & Middleware

- Use **passport.js** or **passport‑azure‑ad** to integrate with Azure AD or Okta.  The middleware extracts JWT claims, validates them and populates `req.user` with `aadObjectId`, `email`, `role`, and `groups`.
- The **RBAC** middleware checks `req.user.role` and ensures the user has necessary permissions for each endpoint (e.g. only Admin/Group Leader can call user search).  RBAC also filters returned records by group membership (e.g. only show jobs in the same group).

### 6.2 Key Endpoints

| Endpoint | Description | Access |
|----------|-------------|---------|
| **`GET /api/form-definitions?type=job`** | Returns the base multi‑page form definition for jobs. | All roles |
| **`GET /api/design-teams`** | Lists all design teams with names and IDs. | All roles |
| **`GET /api/design-teams/{id}/fields`** | Returns the design team’s supplemental form fields. | All roles |
| **`GET /api/users/default-approvers?designTeamId=...&requestType=...`** | Returns default approver IDs (and names) for the given team and request type. | All roles |
| **`GET /api/users/search?q=...`** | Searches the directory for users matching the query. | Admin and Group Leader only |
| **`POST /api/jobs`** | Creates a job.  Validates required fields, merges default approvers, assigns approval route and writes attachments. Returns job with generated ID. | All roles |
| **`GET /api/jobs`** | Lists jobs accessible to current user.  Supports filters: `status`, `type`, `groupId`, `search`. | All roles |
| **`GET /api/jobs/{id}`** | Retrieves detailed job information (metadata, attachments, line items, approval status). | Must have view permissions |
| **`PUT /api/jobs/{id}`** | Updates job fields.  Allowed fields depend on approval status and user role. | Creator or relevant role |
| **`POST /api/jobs/{id}/attachments`** | Uploads attachments for a job. | Same as job edit |
| **`POST /api/jobs/{id}/approve`** | Approver posts a decision.  Moves the job along its approval route. | Only approvers |
| Similar endpoints for **tasks**. |

### 6.3 Approval Workflow

- An approval route (JSON) defines an ordered array of steps.  Each step includes:
  - `order`: sequence index.
  - `approverType`: could be `ROLE:GROUP_LEADER`, `ROLE:ADMIN`, `USER_LIST` (IDs), or `GROUP`.  The back end resolves these to actual user IDs at runtime.
  - `minVotes`: number of approvals needed to move to next step (optional).
- When a job is created, the back-end fetches the default route for its design team and request type from the **DesignTeam** table (via `defaultRouteId`) or from the explicit `approvalRouteId` selected in the form.  It then builds an `approvalStatus` structure in `metadata`, indicating current stage and pending approvers.
- Approvers receive notifications via email or Teams.  When they approve or reject, the API updates the `metadata.approvalStatus`, logs the decision, and, if all required votes are collected, advances the route or finalises the job.

### 6.4 Error Handling and Validation

- All API endpoints validate payloads using a schema validator (e.g. `zod` or `Joi`).  Validation ensures required fields are present, user IDs exist, and dynamic fields match the design team’s definition.
- Client‑side validation uses the `required` attribute and custom functions to highlight errors before submission.  The server replicates these checks to guard against manipulated payloads.
- The API returns meaningful error codes (400 for validation errors, 403 for authorization errors, 404 for not found, 500 for unexpected errors).

---

## 7. Starting Development: Step‑By‑Step

1. **Initialize Git repository and install prerequisites** (Node.js, yarn or npm, Docker if using containers).
2. **Create the folder structure** as described in Section 3 and initialise `package.json` files for both backend and frontend:

   ```bash
   mkdir -p root/backend/src root/frontend/pages root/frontend/components ...
   cd backend && npm init -y && npm install express prisma @prisma/client jsonwebtoken cors ...
   cd ../frontend && npm init -y && npm install next react react-dom @emotion/react axios ...
   ```

3. **Define the Prisma schema** in `backend/prisma/schema.prisma`, run `npx prisma generate` and then create migrations with `npx prisma migrate dev`.  Create seed data for design teams, roles and admin users.

4. **Implement authentication** using Microsoft identity or Okta.  Set up an app registration and configure the redirect URIs.  Integrate MSAL on the front end to sign in and use `passport-azure-ad` or equivalent on the back end to verify tokens.

5. **Implement the API** by creating routes and controllers.  Start with basic CRUD operations for jobs and tasks, then add endpoints for People Picker and approvals.

6. **Build the front end**:
   - Implement `Layout` with collapsible sidebar, header and footer.
   - Implement `FormWizard` to fetch form definitions and update state across steps.
   - Build `FieldRenderer` to handle each field type: text, number, date, select, file, table, people picker.
   - Build the People Picker component integrated with the directory lookup endpoints.
   - Build the multi‑page request page and the view/edit pages.
   - Implement the dashboard with chart widgets.

7. **Test**: Write unit tests for components and API.  Use Jest or React Testing Library for front end tests; use Supertest for API endpoints.  Write end‑to‑end tests with Cypress.

8. **Deploy**: Prepare container configurations or select hosting providers.  Set environment variables and secrets.  Use a CI/CD workflow to automatically build and deploy after tests pass.

9. **Iterate**: Refine the UI, adjust the schema for new dynamic fields, tweak the approval route logic and People Picker behaviour, and add features such as workflow analytics, dashboards and reporting.

---

## 8. Conclusion

This comprehensive plan provides all the elements you need to begin building the design‑job/task management portal: guidelines for project structure, environment setup, database design, multi‑step forms, People Picker integration and approvals. The relational schema uses normalized tables combined with JSONB fields for flexibility, and the People Picker ensures accurate identity selection via Microsoft Graph while restricting search scope based on roles. The multi‑step form engine uses dynamic form definitions stored in the database, enabling the portal to evolve without frequent code changes.

By following the step‑by‑step setup instructions and the specified technology stack, you can bootstrap the project, implement the core features, and iterate toward a fully functional system. If you have further questions or need sample code, do not hesitate to ask.

