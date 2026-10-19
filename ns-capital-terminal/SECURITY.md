# Security boundaries

NS Capital is a personal trading workspace. Sites owns website authentication and audience access. Bridge tokens authorize a particular gateway; they are not multi-tenant website sessions. Keep one private gateway per account execution path. Browser code must never receive broker passwords, model API keys or MT4 publisher secrets.

Bridge, Trade and MT4 Publish tokens are distinct. Web tokens remain in memory, not exports or local storage. Read-only track-record capabilities disclose a redacted immutable snapshot, require explicit creation consent, expire, and can be revoked. They do not independently verify a broker's records.

Report issues privately through the repository owner's existing private contact or private vulnerability reporting if enabled. Do not post credentials, order IDs tied to a real account, databases, private notes or Statements in public issues. A sanitized description and reproducible fixture are preferred. This project does not provision an external security mailbox.

See the Thai manual for deployment and backup procedures. A credential leak requires rotation at its actual source, not only deletion from the latest commit.
