# Human actions required (audit remediation)

Items the code changes on branch `audit-fixes` cannot do, or decisions that belong to the owner.
Finding IDs refer to `AUDIT_REPORT.md`. Nothing below has been executed.

## 1. Rotate the committed secrets (F-48) — do first

The three values listed in `backend/app/config.py` `PUBLISHED_SECRETS` were committed and pushed to the
`origin` (github.com/Clyptus-Soft/SAP_BRIM_Ai) and `target` (github.com/vamshiyadav-06/SAP_chatbot) remotes.
`target` is public. The startup denylist prevents reuse in this codebase only; anyone who cloned the repo knows them.

- [ ] Generate a new `JWT_SECRET` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) in every environment.
      Rotating it signs every user out.
- [ ] Generate a new `ADMIN_API_KEY`, or leave it empty to disable key-based admin access.
- [ ] Change the password of every admin account that ever used the published admin password
      (`py -3.14 backend/scripts/set_admin_password.py`).
- [ ] Change any other account (database role, email, cloud console, personal accounts) that reused any of these values.
- [ ] Check provider dashboards (Groq, Gemini, OpenRouter, Tavily) for unexpected usage, and rotate those API keys
      if `.env` files were ever shared.

## 2. Coordinated git history rewrite and secret scan (F-48, F-01) — commands only, NOT run

Rewriting history changes every commit hash; coordinate with everyone who has a clone, and back up first.

```bash
# 0. Fresh mirror clone; never rewrite your working clone.
git clone --mirror https://github.com/vamshiyadav-06/SAP_chatbot.git SAP_chatbot-mirror.git
cd SAP_chatbot-mirror.git

# 1. Scan the full history of every ref before and after the rewrite.
gitleaks detect --source . --log-opts="--all" --report-path ../gitleaks-before.json

# 2. Replace the leaked literals everywhere in history. replacements.txt contains one line per secret:
#      <literal-secret>==>REDACTED
#    (Write the file locally; do not commit it.)
git filter-repo --replace-text ../replacements.txt

# 3. If licensed PDFs must leave history (see item 3), also:
git filter-repo --invert-paths \
  --path "knowledge_base/documents/BR234_EN_Col22_CO_A4.pdf" \
  --path "knowledge_base/documents/BR234_EN_SOM 2.pdf" \
  --path "knowledge_base/documents/BR245_EN_Col23_CO_A4.pdf" \
  --path "knowledge_base/documents/BRIM_AC240_EN_Col16.pdf" \
  --path "knowledge_base/documents/SAP BRIM Press Book 2nd Edition - Expertsoft.pdf" \
  --path "knowledge_base/documents/E_Book_ABAP_RESTful_Programming_Model_2020_Rel_NW_wwwERPExamsCom.pdf"

gitleaks detect --source . --log-opts="--all" --report-path ../gitleaks-after.json

# 4. Only after review and team agreement:
git push --force --mirror
# Repeat for https://github.com/Clyptus-Soft/SAP_BRIM_Ai. Ask GitHub support to purge cached views and
# dangling objects, and ask every collaborator to re-clone.
```

## 3. Licensing decision for the knowledge base (F-01)

Decide whether the project may store, serve to all registered users, and send to external LLM providers:
SAP Education handbooks (`BR234_*`, `BR245_*`, `BRIM_AC240_*`), `SAP BRIM Press Book 2nd Edition - Expertsoft.pdf`,
and `E_Book_ABAP_RESTful_Programming_Model_2020_Rel_NW_wwwERPExamsCom.pdf`.
If not: remove them from the served corpus (admin portal → delete) and from git history (item 2, step 3).
No file in `knowledge_base/` was deleted by this remediation.

## 4. Approved LLM providers and data-retention terms (F-05)

- Which providers may receive KB excerpts, chat history, uploaded file text and screenshots?
- Are signed zero-retention / no-training terms required (Azure OpenAI, Vertex AI, Anthropic, SAP AI Core)?
- Free-tier models (OpenRouter `:free`, free vision models) must stay disabled unless explicitly approved.

## 5. Product decisions taken with a safe default (flag)

| Decision | Flag (default) | Introduced in |
|---|---|---|
| Answer "simple" SAP questions from model memory without retrieval? Such answers are always labelled unverified. | `SIMPLE_SAP_FAST_PATH_ENABLED` (`false`) | F-04 |
| Let weak document evidence trigger the GitHub/web comparator automatically? Now requires `REPO_SOURCE_ENABLED` or `MULTI_SOURCE_COMPARE_ENABLED`. | `AUTO_MULTI_SOURCE_FALLBACK` (`true`, inert unless a source flag is on) | F-49 |
| An answer stream that ends before verification completes is no longer saved. Users re-ask instead of seeing a partial unverified answer. | — | F-03 |

<!-- Later phases append further items here: re-chunk/re-embed command, SSO/BFF migration, golden Q&A ownership, etc. -->
