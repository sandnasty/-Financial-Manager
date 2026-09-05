# Financial Manager operational runbooks

Every incident record includes trigger time, owner, affected environment and build digest,
correlation/trace IDs, decisions, validation evidence, escalation, recovery, and closure.
Use the Grafana platform and agent dashboards, Prometheus alerts, immutable audit events,
and MS-69 emergency controls. Never export credentials, tokens, account numbers, or
unredacted financial data.

| Scenario | Trigger | Owner | Immediate action | Validate and close |
|---|---|---|---|---|
| Service outage | ServiceDown alert | Platform operator | Preserve evidence; stop unsafe actions | Health, error rate, audit and telemetry normal |
| Agent/tool failure | AgentWorkflowFailures | Trading operator | Disable affected agent; prevent duplicate effect | Correlated trace reconstructed; safe test passes |
| Audit loss | AuditIngestionBlindSpot | Security operator | Block new TradeIntent; protect database | Append/read/hash chain verified |
| Telemetry loss | TelemetryIngestionBlindSpot | Platform operator | Preserve local logs; restore collector | Targets and dashboards current |
| Critical vulnerability | Security gate failure/advisory | Security owner | Stop promotion; assess exposure | Fixed signed digest passes gates |
| Credential compromise | Suspected disclosure | Security owner | Disable identity; rotate/revoke credential | Old credential rejected; audit complete |
| Bad deployment | Health/policy regression | Release operator | Disable actions; run signed-digest rollback | Previous digest healthy in DEV/TEST/PROD |
| Unsafe agent | Policy breach | Trading operator | Global/scoped kill control | Root cause fixed; explicit re-enable approval |

Critical incidents escalate immediately to the owner/human and security owner. High incidents
escalate if not contained within 30 minutes. Closure requires an immutable audit event and
links to retained evidence.
