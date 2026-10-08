# Publication failure handling

Date: 8 October 2026

Parison builds each evidence bundle in a private sibling staging directory and exposes the final run directory only after all artifacts and the manifest are complete.

Filesystem failures while creating the staging directory, writing artifacts or replacing the final directory are reported as ordinary Parison operational errors. A failed publication removes its partial staging directory when one was created. The requested final directory is not left behind as a partial success.

This behavior covers surfaced Python I/O failures. It does not claim crash durability under power loss or operating-system termination, and Parison does not reserve disk space in advance.
