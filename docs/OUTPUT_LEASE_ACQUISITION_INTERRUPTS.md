# Output lease acquisition interrupts

AKILAN treats process-control exceptions during lease acquisition as rollback events.

## Protected transition

A lease becomes active only after both operations complete:

1. the sibling lease directory is created atomically;
2. canonical `owner.json` evidence is written successfully.

If owner-evidence publication raises `KeyboardInterrupt`, `SystemExit`, or another `BaseException`, AKILAN removes the newly created empty lease directory and re-raises the original exception unchanged.

This prevents an interrupted process from leaving an ownerless lease that would block later builds while preserving normal fail-closed behavior for existing foreign leases.

## Guarantees

- the original process-control exception is not converted into an ordinary runtime error;
- no acquired state is reported before owner evidence is published;
- a subsequent writer can acquire the destination after successful rollback;
- existing leases and foreign owner evidence are never modified;
- the canonical artifact schema and runtime dependency set are unchanged.

The rollback applies only to failure before owner evidence is created. Once acquisition succeeds, normal full-owner verification governs release.
