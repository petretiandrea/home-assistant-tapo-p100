# Button event polling

S200B/S200D event logs use a shared timer per child device, independent of routine
device-info refreshes. The timer uses the existing adaptive utilization budget
(300 ms to 5 s) and accounts for request duration when scheduling the next poll.
Device information uses the configured normal scan interval instead of the fast
event interval.

This avoids feeding subsecond intervals into Home Assistant's coarse coordinator
scheduler and removes device-info requests from the event polling critical path.
Button, dial, and diagnostic entities share one event-log request. Removing the
last listener cancels the timer and any pending request. Failed requests back off,
requests have a ten-second timeout, and a failing listener does not prevent other
listeners from receiving events. Automatic polling disablement is honored.

The interval controls event detection cadence. It does not measure or eliminate
the hub's event creation latency or the latency of downstream light commands.
