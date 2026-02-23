# Expanded Full‑Stack Architecture Plan with Directory Lookup and Default Approval Mapping

This document updates the multi‑page architecture plan by adding **directory lookup** (People Picker) and **default approval/approver mapping**.  These additions allow users to select approvers from Azure AD/Okta while restricting “who can search whom” based on role.  The design also clarifies where default approvers and approval routes are stored and how they are applied when a user submits a job or task.

## 1. Rationale

In design‑workflow systems, users often need to designate reviewers and approvers; requesting them manually can be error‑prone.  Integrating with the corporate directory (Azure AD via Microsoft Graph) ensures that emails and names are accurate and up‑to‑date.  By storing **default approvers** and **approval routes** in a configuration table, the portal can automatically propose the correct sequence of reviewers for each design team or request type.  Combining these with role‑based access controls—where only certain roles can override defaults—streamlines the user experience while keeping control in the hands of admins and group leaders.

## 2. Multi‑Page Form Flow with People Picker

The job and task request forms remain **multi‑step** as described previously.  The typical sequence now looks like this:

1. **Basic Info** – Title, description, request type, design team, priority and due date.
2. **Stakeholders and Approval** – Choose (or accept defaults) for approvers, watchers and group memberships.  This step includes the **People Picker** component.
3. **Design‑Team‑Specific Fields** – Supplemental fields defined by the selected design team’s schema (e.g. board dimensions for PCB, MCU type for firmware).
4. **Attachments & Artifacts** – Upload relevant files and add versioning details.
5. **Line‑Items & Custom Table** – Optional editable table for list‑style data (e.g. bill of materials) stored in `JobLineItem` or `TaskLineItem`.
6. **Review & Submit** – Summarize the data; perform final validation; submit.

The **People Picker** appears in step 2.  Its behaviour depends on the current user’s roles:

- **Administrators and Group Leaders** can search the entire corporate directory via Microsoft Graph (e.g. `/v1.0/users?filter=startswith(displayName,'…')`).  They can add anyone as an approver or watcher, beyond the preselected defaults.
- **Standard Users** see only a pre‑populated list of approvers (the default list) and cannot free‑search the directory.  The list is retrieved from the configuration’s default approvers for the selected design team or request type.  Users pick or remove names from this list only.

All selected approvers are stored as **Azure AD object IDs** in the `metadata` JSON for each job or task, preserving referential integrity even if a user’s UPN changes.

## 3. Data Model Updates

Below is an updated relational schema with additions for default approvers and approval routes.  Only the new or modified tables are described; existing tables (User, Group/Department, Job, Task, LineItem, Attachment) remain as previously documented but now include relationships to the new tables.

### 3.1 Configuration and Defaults

| Table | Key fields | Purpose |
|---|---|---|
| **DesignTeam** | `id`, `name`, `form_definition JSON`, `default_route_id` | Stores design team names (PCB, Hardware, Firmware, Drawing), the JSON schema for team‑specific fields, and a pointer to the default **ApprovalRoute** for that team. |
| **ApprovalRoute** | `id`, `name`, `route JSON` | Stores ordered lists of approver steps.  Each step references a role or specific user(s) through object IDs.  Routes can be assigned to a design team or request type. |
| **DefaultApprover** | `id`, `design_team_id`, `request_type`, `approver_ids ARRAY` | Stores arrays of AD object IDs representing the default approvers for a particular design team and request type combination.  When a new job or task is created, this list is loaded and presented to the user. |
| **FormDefinition** | `id`, `request_type`, `steps JSON` | Defines the multi‑page form configuration (step titles, fields, validation rules) for each type of request.  The `steps` JSON includes references to design‑team specific fields. |

### 3.2 Job/Task Metadata

The `metadata` JSON column in the `Job` and `Task` tables stores additional fields as key–value pairs, including:

- `approver_ids`: ordered list of selected approver AD object IDs.
- `watcher_ids`: list of selected watcher AD object IDs.
- `stage`: track the current approval stage.  Each stage corresponds to a step in the `ApprovalRoute`.
- `custom_fields`: all supplemental fields from the design‑team schema.

### 3.3 Example relationships

- **DesignTeam** → **DefaultApprover** (one‑to‑many): each design team can have different default approvers for various request types.
- **DesignTeam** → **ApprovalRoute** (many‑to‑one): the default route for a team is stored here; jobs/tasks reference the route via `default_route_id` and can override it only if the user has admin/group leader permissions.

### 3.4 Directory Entities

Although **User** and **Group** data are derived from Azure AD or Okta, the portal maintains tables for local metadata and role assignment:

| Table | Purpose |
|---|---|
| **User** | Stores the AD object ID, UPN/email, display name and role (Admin, GroupLeader, User).  The object ID ensures persistent references to AD. |
| **Group/Department** | Maps to AD security groups or distribution lists.  Each group may correspond to a design team or department.  Used for scoping job/task visibility. |
| **UserGroupMap** | Many‑to‑many mapping between users and groups.  Contains membership data from AD plus additional application roles (e.g. design team membership). |

## 4. Backend API and Access Control

### 4.1 Directory Lookup API

- **`GET /api/users/search?q=…`** – Searches the directory for users whose display name or email starts with the query string.  Only accessible to admins and group leaders.  The server uses MSAL to obtain an access token and calls Microsoft Graph (e.g. `/v1.0/users?$filter=startswith(displayName,'q') or startswith(mail,'q')`).  Results include the user’s display name, email, job title and object ID.  Requests are rate‑limited and results cached.
- **`GET /api/users/default-approvers?designTeamId=…&requestType=…`** – Returns the default approver list for the specified design team and request type.  Accessible to all authenticated users.  The server fetches IDs from the `DefaultApprover` table and looks up additional details from AD.

### 4.2 Job/Task Creation Flow (server)

1. **Validate input**: Check required fields and verify that user input for approvers belongs to either the default list (for standard users) or any valid AD users (for admins/group leaders).  If an invalid selection is found, return `403`.  
2. **Assign approvers and approval route**: If the request includes no approvers, load the defaults from `DefaultApprover`.  If the user is an admin/group leader and provides a custom list, override the defaults.  Assign the default route from `DesignTeam` unless a specific route is specified (also restricted by role).  
3. **Insert job/task**: Create the record with system‑generated ID (as described previously).  Save approver IDs and other custom fields into `metadata`.  
4. **Kick off approval**: If an approval route exists, send notifications to the first stage’s approvers and set `stage` to `1`.  
5. **Return result**: Respond with the new job/task ID and any computed fields (e.g. formatted date).  The front‑end redirects accordingly.

### 4.3 Edit & Update Logic

- Standard users can edit only non‑restricted fields (metadata and attachments) until the job enters an approval stage (> 1).  
- Admins and group leaders can modify approver lists and approval routes, but changes require re‑validation.  The server ensures that only authorized roles can call the unrestricted `/api/users/search` endpoint; attempts by standard users result in `403`.  
- When recording comments, uploads or status changes, the server uses the user’s AD object ID for the audit log.

## 5. Front‑End Integration

### 5.1 People Picker Component

- **UI**: A search box that displays a list of user suggestions.  When a user types a query, the component either fetches **default approvers** (for standard users) or calls the **search API** (for admins/group leaders).  Selected users appear as tags/pills beneath the input and can be removed by clicking an ‘x’.  
- **Permissions**: The component queries the user’s role from `AuthContext`.  If the user is not an admin/group leader, the search box is read‑only and pre‑populated with default approvers.  
- **Caching**: Use local caching for previously searched terms and store the default approver list in memory for each design team to reduce API calls.
- **Persist**: On final submission, convert selected user objects to their AD object IDs and store them in the job/task’s metadata.  Also store watchers as a separate list.

### 5.2 Form Wizard Integration

- The multi‑step `FormWizard` now includes the *Approvals* step, which houses the People Picker along with visible information about the selected approval route (e.g. ordinal list of roles or users).  The user can view who is on the route and, if authorized, adjust the sequence by selecting a different route or editing the approver list.  
- **Validation**: The `Next` button remains disabled until required fields (including at least one approver) are selected.  Server‑side validation ensures that the final selection adheres to the user’s permissions.  If the server rejects the selection with a `403` or `400`, the UI displays an error indicating invalid or forbidden assignee.

## 6. Role‑Based Access and Workflow Guards

- **User Roles**: Roles (Admin, GroupLeader, User) are encoded in the JWT token obtained from your identity provider.  These roles determine whether a user can access the unrestricted search API and override default approvers.  They also affect UI elements (hide the free‑form search bar for standard users).  
- **Department Scoping**: The portal queries the user’s group membership from the Graph token.  When filtering job or task lists or when selecting default approvers, only those associated with the same design team or department are included unless the user’s role grants cross‑department access.  
- **Audit Trail**: All actions on approver lists (add, remove, reorder) and route selections are logged with the acting user’s object ID and timestamp for compliance and traceability.  These logs are accessible through the Admin page for authorized users.

## 7. Summary & Benefits

By introducing a **directory lookup component** (People Picker) and a **DefaultApprover** mapping, the system provides a streamlined experience for selecting approvers while maintaining strict permission control.  Default approval routes and approvers ensure that standard users follow department policies and cannot circumvent mandatory review, while administrators and group leaders retain the ability to override defaults when necessary.  The data model and API changes are integrated cleanly into the existing multi‑page form architecture, preserving modularity and scalability.

