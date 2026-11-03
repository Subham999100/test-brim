# Application and Code Changes

**Date:** 3 November 2026

**Scope:** Changes made during this conversation, including environment setup and updates pulled from GitHub.

**Delivery branch:** `updated_admin_dashboard`, based on `main` commit `9dcae91`.

## 1. Sidebar navigation

- Removed the bottom-left **Organisation** shortcut from the chat workspace.
- Kept the organisation module, routes and administrator features available.
- Enlarged the sidebar Clyptus logo using the existing `xl` preset: 48px on small screens and 56px on desktop.

**Main file:** `frontend/src/layouts/AppLayout.tsx`

## 2. Chats dropdown

- Added an expand/collapse control above the date-grouped chat history.
- Chats starts collapsed unless that profile previously chose to expand it.
- Saved the choice separately for each account.
- Returning from the admin dashboard or refreshing preserves the chosen state.
- Retained existing conversation links, pinning and deletion actions.
- Added mouse, keyboard, focus and chevron behaviour.

**Files:** `frontend/src/layouts/AppLayout.tsx`, `frontend/src/index.css`

## 3. Projects dropdown

- Added a separate expand/collapse control for Projects.
- Projects starts collapsed unless that profile previously expanded it.
- Saved its state independently of Chats and independently for each account.
- Preserved the state across admin-dashboard navigation and refresh.
- Kept the **+ Create project** button accessible while Projects is collapsed.
- Retained project navigation and pin controls.

**Files:** `frontend/src/layouts/AppLayout.tsx`, `frontend/src/index.css`

## 4. Profile-specific projects and pinned items

- Removed the automatically generated, pre-pinned **SAP BRIM Architecture** sample that appeared in every profile.
- Hid untouched saved copies of that sample while preserving customised copies and user-created projects.
- Retained account-specific storage for projects and pinned chats.
- Made the workspace remount when the account changes, discarding the previous account's displayed projects, pins and pending chat-list results.
- Verified that two accounts cannot see each other's projects or pins, or open each other's project URLs.

**Files:** `frontend/src/services/projectService.ts`, `frontend/src/layouts/AppLayout.tsx`

**Existing limitation:** Projects and pins use browser storage rather than server persistence. Existing logout/session-cleanup behaviour still clears the applicable browser data.

## 5. Light theme throughout the application

- Changed the HTML shell, startup theme script, workspace and Appearance settings to default to Light.
- Changed the default browser theme colour to white.
- Added a one-time switch to Light for browsers with older saved preferences. Users can select Dark or System afterward.
- Added light colours to previously fixed-dark admin screens, including the dashboard, sign-in, loading and access-denied screens.
- Updated the guide, retrieval inspector, sharing dialog and grounding tooltip for light mode.
- Fixed the nested Accounts panels: Organisations and Individual users now inherit light backgrounds, text, search fields, table headers and status colours.
- Preserved the original dark variants as an optional theme.

**Files:**

- `frontend/index.html`
- `frontend/public/theme-init.js`
- `frontend/src/layouts/AppLayout.tsx`
- `frontend/src/layouts/AdminProtectedRoute.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/pages/admin/AdminDashboard.tsx`
- `frontend/src/pages/admin/AdminLoginPage.tsx`
- `frontend/src/components/organisation/organisation.css`
- `frontend/src/components/ui/AssistantGuideModal.tsx`
- `frontend/src/components/chat/RAGInspectorPanel.tsx`
- `frontend/src/components/chat/ShareModal.tsx`
- `frontend/src/components/chat/GroundingScoreBadge.tsx`

## 6. Local startup and configuration

- Started the backend with the repository virtual environment on port 8000 and the frontend on port 5173.
- Reused the existing PostgreSQL container on port 5435 after Compose reported a container-name conflict. No database volume was removed or recreated.
- Applied `DEBUG=false` to the backend process to override an incompatible inherited value.
- Copied the supplied super-admin settings from the template into the active, git-ignored root `.env` and created the missing admin account through the existing provisioning function.
- Created a separate standard local account when direct-login credentials were requested.
- Copied the configured Groq key into the active `.env`, restarted the backend and verified live Sprint generation.

Credentials, API keys and access tokens are intentionally excluded from this report. The pre-existing owner edits in `.env.example` were preserved.

## 7. Updates pulled from GitHub

Pulled `origin/main` from `6226994` to `9dcae91`. These changes came from the remote repository:

- Scholar generation and web-fallback changes, including partial/unverified answer handling.
- Provider cooldown handling after rejected credentials.
- Admin **Accounts** and **Knowledge base** navigation toggles.
- Document Manager checkboxes and confirmed bulk deletion using the existing document-deletion endpoint.
- Associated tests, documentation and public-copy updates.

Local edits were stashed before pulling, restored afterward, and kept unstaged. The handover-note conflict was resolved by retaining both sets of notes. The backup stash was retained.

## 8. Tests and verification

Added or updated regression coverage in:

- `frontend/src/layouts/AppLayout.test.tsx`
- `frontend/src/services/userStorage.test.ts`
- `frontend/src/pages/admin/AdminDashboard.test.tsx`
- `frontend/src/pages/theme.test.tsx` — new
- `frontend/src/pages/lightSurfaces.test.tsx` — new
- `frontend/src/components/organisation/organisationTheme.test.ts` — new

Completed checks:

| Check | Result and scope |
| --- | --- |
| Full frontend suite | Final pre-publication run: 120 tests passed across 18 files, including all logo/dropdown changes. |
| Latest focused sidebar suite | 10 tests passed after the Projects dropdown change. |
| Latest TypeScript check | Passed as part of the final production build. |
| Production builds | Final `npm run build` passed after all application changes. |
| Browser checks | Verified admin and public light surfaces, nested Accounts panels, two-account isolation, dropdown mouse/keyboard behaviour, admin return navigation, refresh persistence and the create-project control. |
| Backend checks | Health endpoint reported a connected database; admin sign-in and live Sprint generation succeeded during setup. |
| Diff checks | `git diff --check` passed throughout the changes. |

No full backend regression suite was run during this conversation.

## 9. Documentation

Updated the engineering handover, changelog and project context under `docs/engineering-memory/`. Application changes and this report are grouped on `updated_admin_dashboard` for the requested GitHub publication. Credential-bearing local `.env.example` edits are excluded; the active `.env` remains ignored.
