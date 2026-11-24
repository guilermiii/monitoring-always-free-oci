# Security Policy

## Supported Versions

Security updates and critical patches are actively supported on the following branches:

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| `1.0.x` | :white_check_mark: |
| `< 1.0` | :x:                |

---

## Reporting a Vulnerability

We prioritize the security and integrity of the **OCI Always Free Monitor** and take all security vulnerabilities seriously.

If you believe you have discovered a vulnerability, please do **NOT** open a public issue. Instead, please follow this disclosure process:

1. **Private Reporting:** 
   - Report the vulnerability privately via [GitHub Private Vulnerability Reporting](https://github.com/guilermiii/monitoring-always-free-oci/security/advisories/new) or by sending an email directly to **guisouzaskill@gmail.com**.
2. **Details to Include:**
   - A clear description of the issue and potential security impact.
   - Exact steps or proof-of-concept (PoC) scripts to reproduce the vulnerability safely.
   - Any proposed remediation or patch.
3. **Response SLAs:**
   - **Initial Triage:** Within **48 hours** acknowledging receipt of the report.
   - **Patch Delivery:** Typically within **7 business days** for critical issues, followed by an advisory publication and release.

---

## Security Architectural Guarantees

* **Non-Root Pod Execution:** Container images run with non-privileged UID/GID (`1000:1000`), complying with the *Kubernetes Pod Security Standard (Restricted)*.
* **Least-Privilege Cloud Access:** The backend requires only read-only OCI API access for resource inspections; no modification or write permissions are required.
* **Privacy & Portfolio Mode:** Data masking active by default (`PORTFOLIO_MODE=true`), anonymizing tenancy names, OCIDs, and IP addresses for public exposition.
* **HttpOnly Session Cookies:** Administrative authentication relies on JWT encrypted sessions delivered over `SameSite=Lax` and `HttpOnly; Secure` cookies.
* **Rate Limiting & Metric Shielding:** Sensitive endpoints (`/metrics`, `/livez`) and brute-force targets (`/api/v1/auth/login`) are protected with strict rate limiting and reverse-proxy firewalls.
