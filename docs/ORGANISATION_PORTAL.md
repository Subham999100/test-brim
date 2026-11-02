# Organisation Portal: design and API contract

Status: implemented (2026-11-01), uncommitted. This document is the contract between the backend and the
frontend. Change it first if either side needs a different shape. See "Implementation notes" at the end for
details settled during implementation.

## Goals

* Organisations get an isolated workspace: their own member accounts, a shared knowledge hub of saved AI
  answers organised by SAP BRIM topic, likes and comments.
* Organisations are created only by a Super Admin. An organisation administrator activates the workspace
  with a Super-Admin-issued activation (referral) code that is unique, time-limited, single-use, securely
  generated and validated on the backend. There is no public self-registration path to an organisation.
* Individual users keep the existing experience (`/login`, `/app`, personal chats).
* The Super Admin dashboard has separate **Organisation Management** and **Individual User Management** sections.

## Decisions (defaults chosen where the requirements were open)

| Topic | Decision | Why |
| --- | --- | --- |
| Super Admin | Existing `users.is_admin = true` accounts (individual account type). | The admin portal and guards already exist. |
| Member credentials | Org admin creates a member; the server generates a temporary password, shown **once** in the response. The member must change it at first sign-in (`must_change_password`). | No e-mail delivery exists. Secure e-mail invitations are a later addition. |
| Code delivery | Super Admin copies the activation code from the dashboard (shown once) and sends it out of band. | No e-mail delivery exists. |
| Member chats | Private to the member, like individual chats. Only answers a member explicitly shares become visible to the organisation. | Privacy by default; matches "share useful answers". |
| Like → save | A member can share an assistant answer to the hub only after liking it (`feedback = "up"`). Sharing auto-likes it in the hub. | "Liked answers are eligible to be saved." |
| Categorisation | Deterministic keyword classifier on question + answer, no LLM call. Sharer or org admin can change the category. | Fast, private, testable; no extra provider cost. |
| Isolation | The organisation is always derived from the authenticated user, never from request input. Another organisation's IDs return 404. | Prevents cross-tenant access by ID guessing. |
| Agentic AI chatbot | Marketing section only, labelled "Coming soon". No functionality. | Not built yet. |

## Data model (Alembic revision `0006_organisations`, additive and idempotent)

`organizations`
: `id` (uuid str 36, PK), `name` (varchar 120, unique, case-insensitive check in code), `slug` (varchar 140, unique),
  `contact_name` (varchar 120, null), `contact_email` (varchar 255), `request_message` (text, null),
  `status` (varchar 20: `requested` | `pending_activation` | `active` | `suspended` | `deactivated` | `rejected`),
  `created_by` (varchar 36 FK users.id ON DELETE SET NULL, null), `activated_at` (timestamp, null),
  `created_at`, `updated_at`.

`org_activation_codes`
: `id` (PK), `organization_id` (FK organizations.id ON DELETE CASCADE, index), `code_hash` (varchar 64, unique; SHA-256 hex
  of the normalised code, the plaintext is never stored), `code_hint` (varchar 8: last 4 characters), `admin_name`
  (varchar 120), `admin_email` (varchar 255), `expires_at`, `used_at` (null), `used_by` (FK users.id SET NULL, null),
  `revoked_at` (null), `created_by` (FK users.id SET NULL), `created_at`.

`users` (new columns)
: `account_type` (varchar 20, not null, default `individual`; `individual` | `organisation`), `organization_id`
  (FK organizations.id ON DELETE SET NULL, null, index), `org_role` (varchar 20, null; `owner` | `admin` | `member`),
  `is_active` (bool, not null, default true), `must_change_password` (bool, not null, default false),
  `last_login_at` (timestamp, null).

`org_shared_answers`
: `id`, `organization_id` (FK CASCADE, index), `message_id` (FK messages.id ON DELETE SET NULL, null), `question` (text),
  `answer` (text; evidence markers stripped), `category` (varchar 64), `shared_by` (FK users.id SET NULL, null),
  `shared_by_name` (varchar 255 snapshot), `created_at`, `updated_at`.
  Unique `(organization_id, message_id)`.

`org_answer_likes`
: `id`, `shared_answer_id` (FK CASCADE), `user_id` (FK users.id CASCADE), `created_at`. Unique `(shared_answer_id, user_id)`.

`org_answer_comments`
: `id`, `shared_answer_id` (FK CASCADE, index), `user_id` (FK users.id SET NULL, null), `author_name` (varchar 255 snapshot),
  `body` (text, 1-2000 chars), `created_at`.

## Activation codes

* Format `CLY-XXXX-XXXX-XXXX-XXXX` using an unambiguous base32 alphabet (no 0/O/1/I), 80 bits from `secrets`.
* Input is normalised (uppercase, strip spaces and hyphens, re-insert the prefix) before hashing.
* TTL: `ORG_ACTIVATION_CODE_TTL_HOURS` (default 72). Issuing a new code revokes the organisation's unused codes.
* Completing activation locks the code row (`SELECT ... FOR UPDATE`), re-checks unused, unexpired and unrevoked, then
  creates the owner account and marks the code used in the same transaction.
* Verification and activation endpoints are rate-limited per IP and return one generic message for every failure
  ("This activation code is not valid. Ask your Clyptus administrator for a new code.").
* Every issue, verify failure and activation is written to the audit log; the plaintext code never is.

## Categories (key → label)

`cc` Convergent Charging (CC) · `ci` Convergent Invoicing (CI) · `som` Subscription Order Management (SOM) ·
`fica` FI-CA · `integration` SAP BRIM Integration · `troubleshooting` Troubleshooting ·
`architecture` Architecture and Configuration · `general` General SAP.

Classifier order: troubleshooting signals (error, fail, issue, not generated, dump, stuck, reprocess) → integration
(two or more components named, or integration/interface/end-to-end/RFC/IDoc/replication) → highest-scoring component
(cc, ci, som, fica) → architecture/configuration signals (configure, customizing, SPRO, architecture, design, setup) → `general`.

## Authentication and account state

* `/auth/login` is for individual accounts. If the password is correct but the account is an organisation account,
  return 403 `"This is an organisation account. Sign in through the Organisation Portal."`.
* `/org/auth/login` is for organisation accounts; the reverse applies with `"Sign in with your individual account at /login."`.
* Both reuse the existing rate limit, lockout, constant-time checks and audit log, and set `last_login_at`.
* Inactive accounts (`is_active = false`) and members of organisations whose status is not `active` cannot sign in
  (after a correct password: 403 `"This account is not active. Contact your administrator."`) and their existing tokens
  are rejected by `get_current_user`. Deactivating, suspending, resetting a password or changing a role increments
  `token_version` for the affected users.
* `must_change_password = true` users may only call `GET /auth/me`, `POST /auth/logout` and `POST /auth/change-password`
  (403 `"Password change required."` elsewhere).
* `UserResponse` gains: `account_type`, `organization_id`, `organization_name`, `org_role`, `is_active`,
  `must_change_password`.

## API (all under `/api`)

Errors use FastAPI's `{"detail": "..."}`. Times are ISO-8601 UTC.

### Public organisation endpoints (rate-limited)

| Method & path | Body | Response |
| --- | --- | --- |
| `POST /org/requests` | `{organisation_name, contact_name, contact_email, message?}` | `202 {"status": "received"}` (always the same, also for duplicates) |
| `POST /org/activation/verify` | `{code}` | `200 {organisation_name, admin_email, admin_name, expires_at}` or `400` generic |
| `POST /org/activation/complete` | `{code, name, password}` (password 12-72) | `201 Token` (owner signed in) |
| `POST /org/auth/login` | `{email, password}` | `200 Token` |

### Authenticated account endpoint

| Method & path | Body | Response |
| --- | --- | --- |
| `POST /auth/change-password` | `{current_password, new_password}` | `200 Token` (new token; old tokens revoked) |

### Organisation member endpoints (account_type organisation, org active)

| Method & path | Notes |
| --- | --- |
| `GET /org/me` | `{organisation: {id, name, status, member_count, created_at}, role, can_manage}` |
| `GET /org/knowledge/categories` | `[{key, label, count}]` (all categories, zero counts included) |
| `GET /org/knowledge?category=&q=&limit=&offset=` | `{total, items: [SharedAnswerSummary]}` newest first; `q` searches question and answer |
| `POST /org/knowledge` | `{message_id}` → `201 SharedAnswerDetail`. 400 if the message is not the caller's own assistant answer or not liked; 409 if already shared (body `{detail, id}`) |
| `GET /org/knowledge/{id}` | `SharedAnswerDetail` |
| `PATCH /org/knowledge/{id}` | `{category}`; sharer or org admin |
| `DELETE /org/knowledge/{id}` | sharer or org admin; `204` |
| `POST /org/knowledge/{id}/like` / `DELETE /org/knowledge/{id}/like` | idempotent; returns `{liked, like_count}` |
| `POST /org/knowledge/{id}/comments` | `{body}` 1-2000 chars → `201 Comment` |
| `DELETE /org/knowledge/{id}/comments/{comment_id}` | author or org admin; `204` |
| `GET /org/knowledge/shared-message-ids` | `{message_ids: [...]}` the caller's messages already in the hub (to show "Shared" in chat) |

`SharedAnswerSummary`: `{id, question, answer_preview (first 280 chars), category, category_label, shared_by_name,
created_at, like_count, comment_count, liked_by_me}`.
`SharedAnswerDetail`: summary fields plus `{answer, likers: [{name, liked_at}], comments: [Comment], can_edit}`.
`Comment`: `{id, author_name, body, created_at, can_delete}`.

### Organisation admin endpoints (org_role owner or admin)

| Method & path | Notes |
| --- | --- |
| `GET /org/admin/members` | `[{id, name, email, org_role, is_active, must_change_password, created_at, last_login_at}]` |
| `POST /org/admin/members` | `{name, email, org_role: admin|member}` → `201 {member, temporary_password}` (password shown once) |
| `PATCH /org/admin/members/{id}` | `{org_role?, is_active?}`; cannot change or deactivate yourself or the owner; only the owner can grant admin |
| `POST /org/admin/members/{id}/reset-password` | `{temporary_password}`; sets `must_change_password`, revokes sessions |
| `GET /org/admin/activity` | `{members: [{id, name, chats, questions, shared_answers, comments, likes, last_login_at}], totals: {...}}` |
| `PATCH /org/admin/organisation` | `{name?, contact_email?}` (owner/admin) |

### Super Admin endpoints (`is_admin`)

| Method & path | Notes |
| --- | --- |
| `GET /admin/organisations?status=` | `[{id, name, status, contact_name, contact_email, member_count, created_at, activated_at, request_message, active_code: {hint, expires_at, admin_email}|null}]` |
| `POST /admin/organisations` | `{name, contact_email, admin_name, admin_email}` → `201 {organisation, activation_code, expires_at}` (status `pending_activation`; code shown once) |
| `POST /admin/organisations/{id}/approve` | for `requested` orgs: `{admin_name, admin_email}` → `{organisation, activation_code, expires_at}` |
| `POST /admin/organisations/{id}/reject` | `requested` → `rejected` |
| `POST /admin/organisations/{id}/activation-codes` | re-issue for `pending_activation` orgs (revokes unused codes) → `{activation_code, expires_at}` |
| `PATCH /admin/organisations/{id}/status` | `{status: active|suspended|deactivated}`; only valid transitions; revokes member sessions when not active |
| `GET /admin/organisations/{id}` | detail: organisation, admins `[{name, email, org_role, is_active, last_login_at}]`, usage `{members, active_members, questions_30d, shared_answers, comments}` |
| `GET /admin/individual-users?search=&limit=&offset=` | `{total, users: [{id, name, email, is_admin, is_active, created_at, last_login_at, chats, questions}]}` |
| `PATCH /admin/users/{id}/status` | `{is_active}`; individual accounts only; cannot deactivate yourself or the last active admin |

## Frontend routes

| Route | Access | Purpose |
| --- | --- | --- |
| `/organisation` | public | Organisation Portal landing: benefits, how it works, knowledge hub preview, "Coming soon: Secure Agentic AI Chatbot", request form, sign-in and activation entry points |
| `/organisation/login` | public | Organisation sign-in (same layout family as `/login`) |
| `/organisation/activate` | public | Code → verify → set name and password → activated → `/app/organisation/admin` |
| `/organisation/change-password` | signed-in | Forced password change for new members and reset accounts |
| `/app/organisation` | org account | Member dashboard and Shared Knowledge Hub (topic navigation, search, likes, comments) |
| `/app/organisation/admin` | org owner/admin | Organisation Admin Dashboard: members, activity, organisation settings |
| `/admin` (new tabs) | Super Admin | "Organisations" and "Individual users" tabs, clearly separate |

Navigation: the app sidebar shows an **Organisation** item. Individual users go to `/organisation`; organisation
users go to `/app/organisation`. The login page's "Create an organisation" button goes to `/organisation`.
Chat: for organisation users, a liked assistant answer shows **Share to organisation**; already-shared answers show
**Shared**.

## Visual design

Use the landing-page system (see `PROJECT_CONTEXT.md`, "Colour system"): `#FF6600` brand ramp, slate neutrals, CSS
tokens in `index.css` (`--paper`, `--surface`, `--raised`, `--ink`, `--text`, `--muted`, `--line`, `--orange`,
`--orange-text`, `--on-orange`), charcoal text on orange buttons, dark mode as default, Manrope headings and DM Sans
body as on the landing page.

## Implementation notes (settled during implementation)

* Code: backend `app/models/organization.py`, `app/api/organisations.py`, `app/api/admin_organisations.py`,
  `app/schemas/organisation.py`, `app/security/org_access.py`, `app/services/org_{categoriser,credentials}.py`,
  `app/services/organisations.py`, migration `0006_organisations`; frontend `pages/organisation/`,
  `components/organisation/`, `components/admin/{Organisations,OrganisationDetail,IndividualUsers}*Panel.tsx`,
  `layouts/{OrgRoutes.tsx,accountRouting.ts}`, `components/chat/orgShare.ts`.
* `POST /org/admin/members/{id}/reset-password` takes no body; it returns `{"temporary_password"}` once.
* `POST /admin/organisations/{id}/activation-codes` accepts an optional `{admin_name, admin_email}` (default: the
  previous code's administrator). `POST /admin/organisations` accepts an optional `contact_name`.
* `/org/me` and `PATCH /org/admin/organisation` also return `organisation.contact_email`. Activity `totals` are
  `members, active_members, members_signed_in_30d, chats, questions, shared_answers, comments, likes`.
* Status transitions: active → suspended | deactivated; suspended → active | deactivated; deactivated → active (only
  if the organisation was ever activated); pending_activation → deactivated. Others return 409. Leaving `active`
  revokes member sessions and unused codes.
* Member management: nobody changes themselves (400) or the owner (403); only the owner grants or changes admins.
  An organisation owner cannot delete their own account (`DELETE /auth/me` → 409).
* `users.organization_id` has its foreign key in the migration only: revision 0001 builds `users` from the current
  model before `organizations` exists.
* Categoriser: the question decides troubleshooting, integration and architecture; the answer only adds weight to
  the CC/CI/SOM/FI-CA scores. Troubleshooting also matches "no … was created", "not posted", "wasn't … posted",
  "missing", "what should I check" and "how do I fix".
* Rate limits (per process unless `REDIS_URL` is set): `ORG_ACTIVATION_RATE_LIMIT_PER_MINUTE=10`,
  `ORG_REQUEST_RATE_LIMIT_PER_HOUR=5`, `ORG_MEMBER_CREATE_RATE_LIMIT_PER_HOUR=30`; code TTL
  `ORG_ACTIVATION_CODE_TTL_HOURS=72`.
