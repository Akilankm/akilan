# Output lease owner evidence size boundary

AKILAN treats `.akilan.lock/owner.json` as small coordination metadata, not as an unbounded document payload.

## Limit

Read-only inspection, competing-writer diagnostics, release verification, and interrupted-acquisition rollback accept at most **16 KiB** of owner evidence.

Before decoding UTF-8 or parsing JSON, AKILAN reads the file size from filesystem metadata. Evidence larger than the limit is rejected through the existing fail-closed `invalid_owner_evidence` contract and is never loaded into memory as JSON.

## Safety behavior

- Oversized evidence is never truncated, repaired, deleted, or rewritten.
- A competing acquisition still fails because the lease directory exists.
- Release refuses to remove oversized or otherwise unverifiable ownership evidence.
- Operators must independently determine whether a malformed lease is abandoned before manual recovery.
- Valid owner evidence produced by AKILAN is substantially smaller than the limit.

The boundary protects repeated lease inspection paths from malformed or adversarially oversized metadata while preserving the canonical lease structure, runtime dependency policy, and non-mutation guarantees.
