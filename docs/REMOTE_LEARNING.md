# Remote Learning Adapter

The Automate learning store can synchronize untrusted learning artifacts from
the Chanfana durable learning ledger.

Remote access is opt-in through:

- `AUTOMATE_LEARNING_ENDPOINT`
- `AUTOMATE_LEARNING_TOKEN`

The adapter is intentionally not a second authority. It validates every
experience/lesson/evolution proposal against Automate's local contracts before
ingestion.

A network outage therefore blocks synchronization, not scientific truth or
capability certification. Remote artifacts are evidence and policy inputs only.

Future activation will synchronize recent history before strategy selection
and submit newly recorded experiences after autonomous cycles. The current
step keeps that wiring explicit so offline laboratory/development operation
remains supported.
