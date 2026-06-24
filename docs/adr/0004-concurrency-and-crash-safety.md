# 0004 - Concurrent sends, single-threaded Ledger, record-as-you-go

Status: accepted (2026-06-24)

The Batch Runner runs the slow work (live Assessment fetches and the browser Pitch sends)
in a thread pool, but every Ledger read and write happens on the calling thread only. Each
send's result is committed to the Ledger the instant that send returns (an as_completed
drain), not in a deferred batch after all sends finish. A Brand stays Queued (retryable)
on a transient failure, is marked Dead on a structurally terminal failure, and is marked
Dead after a capped number of failed attempts so a never-delivering store stops re-launching
a browser every run.

Why it is recorded here: it is hard to reverse (the Ledger is a single SQLite connection and
the whole no-double-send guarantee rests on this structure), surprising without context (the
natural code shape is "send everything, then write everything," which an adversarial review
showed creates a batch-wide double-send window - a crash after sends but before writes
re-pitches every confirmed-but-unrecorded merchant next run), and a real trade-off (recording
as-you-go and keeping all Ledger access on one thread is less obvious than sharing a connection
across workers, but it is what keeps "never pitch the same merchant twice" true under crashes).
Residual gap, noted for a follow-up: a hard kill (SIGKILL/OOM) between wire-delivery and the
single record can still re-pitch one in-flight Brand; closing that fully needs a pre-send
intent marker. This ADR stops a refactor back to deferred bulk writes or worker-thread Ledger
access.
