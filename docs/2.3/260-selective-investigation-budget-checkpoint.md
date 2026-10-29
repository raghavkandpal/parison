# Selective investigation budget checkpoint

Date: 29 October 2026
Status: feature 4 local qualification; machine-specific

Machine: Apple M1, 8 logical CPUs, 16 GiB RAM, macOS 27.0.1, Python 3.14.7. The synthetic [feature 3 reference corpus](256-partition-discovery-budget-checkpoint.md) has one integer key, one exact decimal amount, and a changed candidate amount at every 10,000th key. The reviewed plan has five ranges. This investigation selected range zero, with 5 returned items from 5 selected items. It covered 1 of 2 suspect ranges at 100k and 1 of 5 at 250k; `enumeration_complete` was true and `scope_complete` and `complete` were false. Each timing uses a fresh producer process and output path. Peak RSS was read from separate child processes with `getrusage(RUSAGE_CHILDREN)`.

| Rows per side | Producer wall seconds, three runs | Peak process RSS bytes | Peak logical staged bytes | Final evidence bytes |
| ---: | --- | ---: | ---: | ---: |
| 100,000 | 3.271, 3.271, 3.247 | 112,656,384 | 1,267,820 plus 512-byte raw recipe | 3,608 |
| 250,000 | 7.129, 7.071, 7.020 | 116,998,144 | 1,267,820 plus 512-byte raw recipe | 3,608 |

The feature 3 source-backed prerequisite reads each local input four times. Investigation adds three passes per input: identity digest, routing scan and post-comparison digest. Only selected ranges are staged; the source scan still reads all input rows. Temporary byte figures exclude filesystem allocation and interpreter overhead. The numbers do not measure a PostgreSQL source scan, end-to-end migration rehearsal, or universal capacity.
