# CompatIQ Extra Features

This document covers the additional frontend and security-intelligence features added to CompatIQ.

## 1. Landing Page and Dashboard Routing

The public landing page is available at `/`. Dashboard workflows now use dedicated paths:

| Page | Route |
| --- | --- |
| Dashboard overview | `/dashboard` |
| Documents | `/dashboard/documents` |
| Inventory | `/dashboard/inventory` |
| Compliance | `/dashboard/compliance` |
| Analysis | `/dashboard/analysis` |
| Assistant | `/dashboard/assistant` |
| Compatibility Rulebook | `/dashboard/rulebook` |
| Audit Log | `/dashboard/audit-log` |

Unauthenticated attempts to open a dashboard route are redirected to `/login`.

## 2. Firebase Authentication

CompatIQ supports email/password signup, login, persistent sessions, welcome messages, and sign out.

Routes:

- `/login`
- `/signup`

Firebase Console requirements:

1. Open **Authentication > Sign-in method**.
2. Enable **Email/Password**.
3. Add local and deployed hosts under **Authorized domains**.

The Firebase web configuration is defined in `client/src/lib/firebase.js`. Firebase web API keys identify the Firebase project; access control must still be enforced through Firebase Authentication and Firebase security rules.

## 3. Live CVE Risk Enrichment

Rule candidates now include a **Security Impact** tab. CompatIQ extracts product and version terms from the selected rule and calls:

```text
POST /api/security/cve-enrichment
```

The backend queries the NVD CVE API and returns:

- CVE identifier and description
- CVSS score, severity, vector, and metric version
- Published and last-modified dates
- Affected CPE/product identifiers
- Known Exploited Vulnerability status and remediation metadata
- NVD references

Responses are cached in backend memory for 15 minutes to reduce rate-limit pressure. CVE data is not written to the CompatIQ knowledge base.

Environment configuration:

```env
NVD_API_KEY=replace_with_a_valid_nvd_key
NVD_TIMEOUT_SECONDS=45
```

The backend checks `.env` in both the repository directory and its parent workspace directory. A repository-level value takes precedence.

### Using Security Impact

1. Upload and process a compatibility document.
2. Open the rule review queue.
3. Select a rule candidate mentioning an OS, product, firmware, BIOS, driver, package, or version.
4. Open **Security Impact**.
5. Review CVE severity, CPE applicability, publication date, and KEV status.
6. Confirm the exact model and version against the vendor advisory before changing the rule.

An NVD match is an investigation lead, not proof that the selected asset is vulnerable.

### NVD Troubleshooting

- **Invalid apiKey**: reissue or copy the key from the NVD developer portal and restart the backend.
- **429/rate limit**: wait before retrying; keep the API key configured.
- **No matching CVEs**: use a product-specific name or CPE rather than a generic component term.
- **Backend offline**: verify FastAPI is running at the URL configured by `VITE_API_BASE_URL`.

## 4. Compatibility Rulebook

The **Rulebook** sidebar item opens `/dashboard/rulebook`. It is a built-in, searchable reference and does not require Google, an LLM API, or the project knowledge base.

Current coverage includes:

- Windows 11 and Windows Server
- Ubuntu LTS, RHEL, SLES, and Debian
- macOS and Apple silicon considerations
- VMware ESXi and Hyper-V
- Docker and Kubernetes
- NVIDIA drivers and CUDA
- BIOS, UEFI, BMC, storage, and platform firmware

Each reference contains:

- Version or support boundary
- Minimum compatibility checks
- Platform verification commands
- Search tags and platform category
- Link to the official vendor source

Search matches titles, descriptions, versions, requirements, tags, and commands. The best matching reference is summarized above the result list. Category tabs narrow results without making an external request.

The rulebook is an operational baseline. Vendor support windows and compatibility matrices change, so final production decisions must be checked against the linked official source.

## 5. Local Setup

Backend:

```powershell
cd C:\SideQuest\KnowledgeBase\Compact-IQ
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd C:\SideQuest\KnowledgeBase\Compact-IQ\client
npm install
npm run dev
```

Frontend URL: `http://127.0.0.1:5173/`

API documentation: `http://127.0.0.1:8000/docs`

For production hosting, configure an SPA rewrite so dashboard routes resolve to `client/index.html`.
