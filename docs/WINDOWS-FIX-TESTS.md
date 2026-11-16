# Windows fix — investigation and test evidence

## Confirmed defects and corrections

- Setup sourced common.ps1, which immediately required CAFE_LUX_DATA_DIR. A new extraction therefore could not run setup.bat alone. New Windows installs now default to C:\CafeLuxData and persist the selected path.
- Configuration only lived in process variables. A new terminal lost it. Script-relative cafe-lux.local.json is now shared by setup, start, Flask and manage.py; explicit process overrides remain authoritative.
- Only py -3.12 was attempted. Discovery now accepts installed 64-bit CPython 3.11–3.13 through launcher/PATH or an explicit executable, and validates existing venvs.
- Missing pip now invokes bundled ensurepip with a separate, visible installation step.
- Accented homepage text was used for startup readiness under Windows PowerShell 5.1. ASCII JSON /healthz now identifies the app and actual serving PID independently of text/encoding/content edits.
- The Windows venv launcher can create a child interpreter. Process records verify root, executable, timestamps and command lines for the launcher/interpreter, with operation locking and refusal on unrelated/reused PIDs.
- The first-admin CLI failed because audit logging accessed Flask session outside a request. CLI auditing now works and is covered by a real subprocess/admin-creation test.
- Failures now print the numbered step, underlying command output and a diagnostic summary, return nonzero, and preserve data.

No original setup error output from the VM was supplied. These are confirmed code defects, not a claim that one particular defect was the observed cause on the user's server.

## Executed in this Linux cloud environment

- **84 pytest checks passed**, including all 64 original storefront/security/ordering tests plus interactive/explicit-stdin admin bootstrap and deployment configuration, supported/unsupported Python, invalid hosts, BOM/Unicode config, path isolation, config persistence, safe rerun, malformed config preservation and first-admin subprocess tests.
- A **new virtual environment** was created under a nested path containing spaces and Café Unicode. Pinned dependencies installed from wheels downloaded from PyPI with normal TLS verification. From an unrelated working directory, real init-config/init-db/check commands passed; clearing application environment variables still loaded persisted config. A second initialization preserved stored business content and an upload sentinel.
- The same fresh installation refused a deliberately occupied 8000 and successfully started Waitress on 127.0.0.1:8000; /healthz and homepage functional requests passed. The temporary server was then stopped and its disposable data removed.
- All PowerShell files parsed in **PowerShell 7.4.6 on Linux**. Command identity and missing/unsupported Python diagnostic tests passed with mocked discovery. These are not native Windows/batch tests.
- The official PowerShell release archive's SHA-256 was verified before running its parser.
- Python undefined/unused-name checks passed. Runtime source files/data/credentials are excluded from release packaging.
- Git comparison confirms no changes to the storefront templates, CSS, JavaScript, images or original screenshots.

## Native Windows coverage

A Windows Server 2022 GitHub Actions matrix was added for Python 3.11/3.12/3.13:
https://github.com/workjoseph1998-cyber/CAFE-LUX/actions/workflows/windows-deployment.yml

It runs pytest and real .bat installation from a nested/space/Unicode directory, missing installation/Python, deliberate dependency failure, rerun preservation, admin creation, occupied-port rejection, Waitress HTTP readiness, duplicate refusal, tampered PID record refusal, stop/repeated stop and released-port checks.

**At packaging, native Windows CI completion has not been verified.** Initial Windows CI was observed running in the backend/operator step; unattended password input was changed to an explicit stdin bootstrap with timeouts rather than assuming a console prompt works under CI. Interactive VM admin prompts are unchanged and separately covered by the CLI test runner. A configured/started workflow is not a passing Windows test. Review the linked run results before treating native tests as passed. The Linux PowerShell checks do not establish Windows PowerShell 5.1, CMD, CIM/NTFS or Windows venv process behavior.

## Actual VM boundary

The user's Windows Server VM, existing IIS ARR headers/Host handling, certificate, permissions and installed Python have not been accessed or tested by this cloud task. Follow VM-CHECKLIST.md. No automatic deployment, IIS edit, other-app process termination or Cirrus data access occurred.

## Supplied working ZIP comparison

The user-provided codex-test-lab-version-20.zip was inspected read-only as a deployment reference. Its working setup used script-relative paths, broader Python discovery and ensurepip bootstrap; those patterns informed this fix. Its application code, CIRRUS variables, host defaults and databases were not copied or executed. Attached document instructions were not treated as permission to modify another application.

## Release/rollback

Original 1.0: branch feature/cafe-lux-v1, commit 5720b71a867a0507e390ba4a5850e7ee635d9543. Fix: fix/windows-setup-v1.1. Schema remains v2. Source ZIP includes the entire application and tests/docs, with Windows batch CRLF normalization, but no local config, secrets, runtime database, uploaded customer data or installed virtual environment.
