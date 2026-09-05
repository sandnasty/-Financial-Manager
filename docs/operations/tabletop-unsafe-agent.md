# Tabletop exercise — unsafe agent after deployment

Date: 2026-09-05
Participants/roles: Owner/human, trading operator, platform operator, security operator
Scenario: A newly deployed research agent repeatedly proposes TradeIntents outside the
approved strategy and tool failures rise.

1. `AgentWorkflowFailures` fires and routes to the trading operator.
2. The operator captures build digest, alert state, correlation IDs, and audit sequence.
3. The operator disables the research agent with explicit confirmation. A new TradeIntent
   is rejected while dashboards and audit reads remain available.
4. The release operator selects the prior approved signed digest and runs the `Controlled Rollback` workflow with PROD approval.
5. Operators verify service health, telemetry, audit-chain integrity, policy version, and
   absence of duplicate brokerage effects.
6. The repaired version passes DEV and TEST. The owner explicitly approves scoped
   restoration, which is audited.
7. Evidence is exported with integrity manifest and retained for one year.

Result: The documented controls contain the unsafe action and preserve reconstruction data.

Gap: Prometheus rules define owners and runbooks, but a production notification receiver
(email/pager/chat) is not yet configured because the destination and credentials have not
been selected. Track this as a follow-on Linear issue before live trading.
