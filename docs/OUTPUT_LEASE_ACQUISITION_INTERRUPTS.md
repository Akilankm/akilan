# Output lease acquisition interrupts

AKILAN treats process-control exceptions during lease acquisition as rollback events.

## Protected transition

A lease becomes active only after both operations complete:

1. the sibling lease directory is created atomically;
2. canonical `owner.json` evidence is written successfully.

Owner evidence is first written to a lease-token-specific staging file and then atomically promoted to `owner.json`.

If publication raises `KeyboardInterrupt`, `SystemExit`, or another `BaseException`, AKILAN removes staging evidence and the lease directory when ownership can be proven. If the canonical owner file was already promoted, it is removed only when its complete evidence exactly matches the acquiring process.

If rollback cannot prove ownership because evidence changed, AKILAN preserves the lease for investigation and raises `OutputLeaseError` chained from the original interruption.

## Guarantees

- the original process-control exception is re-raised unchanged after successful rollback;
- no acquired state is reported before owner evidence is published;
- a subsequent writer can acquire the destination after successful rollback;
- altered or foreign owner evidence is never removed speculatively;
- rollback failures retain the original interruption as their exception cause;
- the canonical artifact schema and runtime dependency set are unchanged.

Once acquisition succeeds, normal full-owner verification governs release.
