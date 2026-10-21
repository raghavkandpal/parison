# Workbench stalled-client bound

Date: 21 October 2026

Status: **fix under qualification**

The Workbench host admits at most eight request handlers. When those slots are
full, it now closes an additional connection without blocking its sole accept
loop. Each accepted connection has a ten-second read timeout and an absolute
ten-second deadline for receiving headers and the declared body. A client
trickling bytes cannot keep a handler indefinitely. The deadline is removed
after a complete request is read, so a valid long-running comparison continues.

A loopback regression occupies all eight slots with incomplete requests,
checks that a ninth connection is rejected promptly, trickles bytes into the
stalled connections, then checks that the slots are released at the absolute
deadline. A second case checks that an accepted Run outlives its input deadline.
The capability, Origin,
Host, body-size and closed-route gates remain in force.
