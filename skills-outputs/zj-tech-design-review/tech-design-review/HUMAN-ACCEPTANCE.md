# Human short-read acceptance

## Fixture: new-proposal.md

- Decision recovered: `defer`
- Blocking finding recovered: restart behavior; owner: Importer team
- Next validation: interrupt 30 imports, restart, and verify recovery
- Threshold: at least 99% resume successfully with no duplicate or lost files
- Owner: Importer team
- Result: PASS

## Fixture: existing-review.md — first read

- Decision recovered: `revise`
- Result: FAIL
- Correction: the blocking finding is migration rollback needing an explicit operator signal, owned by Search platform; “old store too large” is not the finding in this fixture.
- Expected next validation: migrate empty, large, corrupted, and interrupted stores, then verify equivalent results or a clean rollback.
- Threshold: at least 99.9% query-result parity on the golden corpus
- Owner: Search platform

## Fixture: existing-review.md — re-read

- Decision recovered: `revise`
- Blocking finding recovered: migration needs an explicit operator signal
- Owner: Search platform
- Next validation: migrate stores in empty, large, corrupted, and interrupted states; verify equivalent results or a clean rollback
- Threshold: at least 99.9% query-result parity on the golden corpus
- Result: PASS

## Fixture: high-risk-unknown.md — first read

- Decision recovered: `defer`
- Blocking finding recovered: sandbox escape coverage is unknown
- Result: FAIL — owner was answered as Data tools, but the security sign-off owner is Security; the fixture also omitted the owner beside the finding.
- Next validation: exercise malicious prompt, path traversal, network exfiltration, and approval cancellation scenarios; verify dangerous operations are denied or require an approval record
- Threshold: zero sandbox escapes and zero unapproved side effects

## Fixture: high-risk-unknown.md — re-read

- Decision recovered: `defer`
- Blocking finding recovered: sandbox escape coverage is unknown
- Owner: Security
- Next validation: exercise malicious prompt, path traversal, network exfiltration, and approval cancellation scenarios; verify dangerous operations are denied or require an approval record
- Threshold: zero sandbox escapes and zero unapproved side effects
- Result: PASS
