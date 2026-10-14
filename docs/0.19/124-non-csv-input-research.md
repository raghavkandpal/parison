# Non-CSV and document input research for Parison 0.19

Date: 13 October 2026

Status: **research recommendation**

## Question and boundary

This review asks which non-CSV files Parison could compare without weakening its local-first, deterministic verification contract. It covers spreadsheet workbooks (`.xlsx`, `.xlsm`, `.xlsb`, `.xls`, and `.ods`), structured text (`.json` and `.xml`), documents and media (PDF, DOCX, images/OCR, and email), logs, and archives. Parquet, JSON Lines, SQLite, and delimited text are already supported and serve as the baseline: each has an explicit projection into typed rows before existing aggregate, keyed, or multiset semantics run.

The governing distinction is not “CSV versus non-CSV.” It is whether a file has a deterministic, bounded, reviewable projection into Parison's row model. A workbook range can have one. “The text of this PDF” generally cannot without choosing layout, reading-order, OCR, and normalization policies. PASS must continue to mean agreement under the named projection and comparison policy, not that extraction was true, complete, or fit for cutover.

All sources below are primary specifications, official project documentation, or first-party format documentation. Sources were accessed **13 October 2026**.

## Findings by format family

### Spreadsheet workbooks

| Format | Structure and hazards | Deterministic local projection | Recommendation |
|---|---|---|---|
| `.xlsx` | An Office Open XML workbook is a package of related XML parts. Cells may contain formulas, cached values, shared strings, styles, merges, hidden sheets, external links, and either the 1900 or 1904 date system. Dates have no timezone; the 1900 system deliberately carries Excel's fictitious leap day ([openpyxl dates and times](https://openpyxl.readthedocs.io/en/3.0/datetime.html)). | Yes, for one explicitly named worksheet and rectangular range or table, with an explicit header row, blank-row/blank-cell rules, formula policy, type mapping, and bounds. | Best future native-input candidate after compatibility stabilization. Start with `.xlsx`, values-only, one sheet/range per input. |
| `.xlsm` | Microsoft defines `.xlsm` as the XML-based macro-enabled workbook format and says it stores VBA or Excel 4.0 macro code; `.xlsx` cannot store those macros ([Microsoft Office format reference](https://learn.microsoft.com/office/compatibility/office-file-format-reference)). | The cell projection can be identical to `.xlsx` if Parison never executes code, never recalculates, and reports macro presence. Formula caches can still be stale. | Either accept alongside `.xlsx` under the same read-only projection with a prominent `macros_present` diagnostic, or defer it until that diagnostic is contractual. Never execute macros. |
| `.xlsb` | The format is an Open Packaging Conventions ZIP package whose parts mix XML, binary records, and byte streams; it can contain formulas, external connections, charts, images, and VBA ([Microsoft XLSB overview](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-xlsb/1a21ca23-7635-4212-9504-8759eb984b12), [Microsoft XLSB specification](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-xlsb/acc8aa92-1f02-4167-99f5-84f9f676b95a)). | Possible only through a separate binary-format implementation with its own tested type and formula behavior. Treating it as merely a faster `.xlsx` is unsafe. | Defer. It adds a new parser/dependency and compatibility corpus without improving the comparison semantics. |
| `.xls` | Legacy Excel 97–2003 workbooks use the BIFF binary format inside an OLE compound file and may depend on structures for encryption, VBA, shapes, and other Office features ([Microsoft XLS specification](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-xls/cd03cb5f-ca02-4934-a391-bb674cb8aa06), [relationship to other structures](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-xls/08a9fc1a-a2da-4fdd-af7a-98c8f2f56341)). | Possible with a legacy parser, but it is a distinct trust and type-conversion surface. | Defer; recommend exporting to `.xlsx` or an already supported format. Do not invoke Excel or LibreOffice as an implicit converter. |
| `.ods` | ODS is a ZIP/XML OpenDocument package with its own formula language. OpenFormula permits automatic or manual recalculation and does not specify one numerical implementation model ([OASIS OpenFormula 1.3](https://docs.oasis-open.org/office/OpenDocument/v1.3/OpenDocument-v1.3-part4-formula.pdf)). | A named sheet/range values projection is feasible, but formula caches and value/type conventions require an ODS-specific contract and parser. | Defer until `.xlsx` proves demand; do not claim formula-result equivalence across Excel and OpenFormula engines. |

The available Python implementation evidence reinforces the boundary. `openpyxl` supports XLSX/XLSM package types but rejects old `.xls`; `data_only` selects either formula text or the value stored when Excel last read the sheet, `keep_vba` preserves VBA but does not make it usable, and `keep_links` controls external-workbook links ([openpyxl reader](https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/reader/excel.html)). It never evaluates formulas ([openpyxl formula documentation](https://openpyxl.readthedocs.io/en/3.1.2/simple_formulae.html)). Read-only mode reduces memory use, but external links can include cached copies of linked sheets ([openpyxl performance documentation](https://openpyxl.readthedocs.io/en/stable/performance.html)). These are reasons to pin and expose a projection policy, not incidental library switches.

#### Minimum workbook projection contract

A supportable workbook reader should require or define all of the following:

1. exact worksheet identity (prefer sheet name; reject missing or duplicate selection rather than silently using the active sheet);
2. exact rectangular range, named table, or an explicit bounded used-range rule;
3. header presence and duplicate/blank-header behavior;
4. row termination, completely blank rows, blank cell versus empty string, and merged-cell behavior;
5. formula mode: **stored result only** or **formula text only**—never local recalculation—and a failure or explicit diagnostic when a stored result is absent;
6. conversion for numbers, booleans, errors, strings/rich text, dates, times, and durations, including workbook epoch;
7. treatment of hidden rows/columns/sheets, filters, and external links (recommended: physical cells are included; presentation state is ignored; external resources are never opened);
8. hard limits on compressed bytes, expanded bytes, ZIP members, sheets, rows, columns, cells, shared-string bytes, and per-cell text;
9. parser name/version and projection-policy version in evidence.

Formatting must not silently determine equality except where it is required to interpret a stored numeric serial as a date/time. Even there, the choice is delicate: the same numeric value can display as a date, duration, percentage, or ordinary number, and XLSX dates carry no timezone ([openpyxl dates and times](https://openpyxl.readthedocs.io/en/3.0/datetime.html)). Merged cells must not be filled down implicitly; in OOXML handling, non-top-left cells in a merge are removed and represented as empty merged cells ([openpyxl worksheet editing](https://openpyxl.readthedocs.io/en/stable/editing_worksheets.html)).

### JSON and XML

Whole-document JSON is structurally parseable, but it is not automatically a row set. RFC 8259 says object member names only *should* be unique; duplicate names produce unpredictable behavior across implementations, and libraries differ on whether member order is visible ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259.html)). A safe future projection would require an explicit pointer to an array of objects, reject duplicate member names and non-interoperable Unicode, preserve array order only when the selected Parison mode needs it, and map numbers without passing through binary floating point. General recursive “semantic JSON diff” would be a new comparison model and is not needed for v0.19.

XML has a standardized byte canonicalization, but canonical bytes are not the same as application semantics. Canonical XML 1.1 normalizes line feeds and attribute values, resolves entities, sorts namespaces and attributes, can include or exclude comments, and explicitly notes that application-specific equivalences may still produce different canonical forms ([W3C Canonical XML 1.1](https://www.w3.org/TR/xml-c14n11/)). XML parsing also carries entity-expansion, external-resource retrieval, large-token, and compressed-stream denial-of-service risks; Python's own documentation recommends hardened parsing for untrusted XML and notes that some APIs retrieve DTDs ([Python XML security guidance](https://docs.python.org/3.11/library/xml.html)). A future XML projection must therefore disable DTDs/entities/network access, impose depth/node/text limits, and use explicit namespaces plus a restricted record path. Generic C14N equality alone should not be marketed as data parity.

Recommendation: do not add general JSON/XML inputs in the spreadsheet release. If later demand exists, add each as an explicit record-selector contract feeding the existing row engine, not as a recursive diff feature.

### PDF and DOCX

PDF is a final-form page description, not a guaranteed logical text stream. Tagged PDF distinguishes real content from artifacts and supplies reading order through structure; page numbers and similar pagination content should be marked as artifacts rather than real content ([Tagged PDF Best Practice Guide](https://pdfa.org/download-area/publications/Tagged-PDF-Best-Practice-Guide.pdf)). Well-tagged PDF guidance also requires `ActualText` when intended text is not represented as interpretable text objects ([Well-Tagged PDF](https://pdfa.org/wp-content/uploads/2024/02/Well-Tagged-PDF-WTPDF-1.0.pdf)). Untagged PDFs, scans, positioned glyphs, ligatures, forms, annotations, optional layers, and embedded files make “extract the text” a tool- and policy-dependent assertion.

DOCX is structured, but not a uniform table. Its block content includes paragraphs, pictures, and tables; Word tables can contain merged cells, omitted cells, and recursively nested tables. Converting an arbitrary table to a matrix is explicitly an approximation ([python-docx table model](https://python-docx.readthedocs.io/en/latest/user/tables.html), [python-docx API concepts](https://python-docx.readthedocs.io/en/latest/user/api-concepts.html)). Headers, footers, footnotes, comments, tracked changes, fields, text boxes, and rendered page order introduce further projection choices.

Deterministic verification can safely compare:

- raw file bytes or digests, which proves identity only;
- user-supplied, locally extracted text/records plus a receipt binding extractor name/version, options, and source digest;
- narrowly selected DOCX tables under a future explicit grid policy, if there is demonstrated demand.

Parison should not directly claim semantic PDF or DOCX comparison in v0.19. Rendering and text extraction belong in an upstream, pinned extractor. A PASS over those extracted records means the extractor outputs agree under policy, not that the documents look the same or communicate the same meaning.

### Images and OCR

Image bytes, decoded pixels, perceptual appearance, and recognized text are four different equality claims. Metadata, color profiles, orientation, compression, resolution, alpha, and animation frames can change bytes or decoded pixels without a simple relation to human meaning. OCR is model-based extraction: Tesseract requires selected language/model data and exposes engine and page-segmentation choices ([Tesseract command-line documentation](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)); its official model families deliberately trade speed against accuracy and use different integer or floating models ([Tesseract trained-data documentation](https://tesseract-ocr.github.io/tessdoc/Data-Files.html)).

Consequently, Parison may verify a caller's OCR output and record a source digest plus pinned extractor/model digests, but it should not embed OCR, perceptual hashes, layout inference, or image similarity. Those would introduce sizeable native/model dependencies, platform variability, accuracy claims, and new tolerance semantics unrelated to deterministic row parity.

### Email

Internet messages combine unordered/reorderable headers with a line-oriented body. RFC 5322 defines header unfolding, says header fields are not guaranteed to remain in a particular order, and treats the body as uninterpreted lines ([RFC 5322](https://www.rfc-editor.org/info/rfc5322/)). MIME adds recursive multipart entities, character sets, content-transfer encodings, attachments, and comments without semantic content ([RFC 2045](https://www.rfc-editor.org/rfc/rfc2045.html)). Addresses, dates, message identifiers, duplicate headers, transfer encodings, multipart boundaries, HTML/text alternatives, signatures, and attachment filenames all need purpose-specific policy.

A deterministic email projection is feasible only for an explicitly selected field set and MIME-part traversal policy with decoded bytes retained or hashed. That is a separate domain contract, not a generic file reader. Defer direct `.eml`/`.mbox` support; accept a locally materialized JSONL/SQLite manifest of messages and attachments today.

### Logs

“Log” names no format. Plain text may contain multiline events, stack traces, locale-dependent timestamps, unstable process IDs, redaction, rotation boundaries, or interleaved writers; structured logs may be JSON Lines, XML, syslog, or vendor-specific envelopes. Parison already supports the defensible case—JSONL or delimited records after the producer or a local preprocessing step establishes event boundaries and fields. It should not infer log grammars, timestamps, continuations, or fields. Document recipes that materialize logs into supported formats with an extraction receipt rather than adding a `.log` extension heuristic.

### Archives and compressed containers

An archive is a container, not a record format. ZIP members have paths, order, timestamps, permissions, compression methods, comments, duplicates, links, and possible nested archives. Python documents CRC/password/method failures, memory or disk exhaustion from decompression bombs, incomplete extraction after interruption, and overwrite behavior on repeated extraction ([Python `zipfile` documentation](https://docs.python.org/3.12/library/zipfile.html)). Office Open XML and OpenDocument are themselves ZIP packages, so these threats apply even when the user thinks they supplied a single spreadsheet.

Do not add generic recursive archive comparison. For workbook parsing, read members in place without materializing arbitrary paths; reject encrypted packages, duplicate security-sensitive members, traversal names, links, unsupported compression, excessive nesting, and limit both declared and observed expanded resources. Archive member order and ZIP metadata must never influence the row projection.

## Canonicalization pitfalls common to all new inputs

1. **Container bytes are not content semantics.** Repacking ZIP/XML documents changes bytes, timestamps, ordering, and compression without necessarily changing selected cells or text.
2. **Presentation can carry type cues.** Spreadsheet number formats and document layout affect human interpretation, but importing all formatting would turn Parison into a renderer. Any cue used for typing must be narrow and contractual.
3. **Cached and derived values are claims.** Formula caches, external-link caches, fields, OCR output, and PDF text extraction may be stale or tool-dependent. Parison may compare the supplied claim; it must not imply it recomputed or validated the source meaning.
4. **Order differs by layer.** Sheet order, row order, JSON member order, XML document order, MIME part order, and visual reading order are not interchangeable. Existing keyed/multiset semantics should apply only after projection.
5. **Empty is not one value.** Missing cells, blank cells, empty strings, merged continuations, absent JSON members, XML empty elements, and whitespace-only text must not collapse accidentally.
6. **Unicode normalization is policy.** Escapes and encodings can represent the same code points, while canonically equivalent Unicode sequences can still be byte-distinct. Reuse Parison's explicit string-normalization policy rather than adding hidden normalization.
7. **Library behavior is part of compatibility.** A parser upgrade can change dates, formula tokens, malformed-input recovery, rich text, or dimension handling. Golden fixtures and parser/version metadata are required before promising stable evidence.

## Threat model and controls

New parsers increase attack surface even with no network and no code execution. The primary threats are:

- ZIP/XML decompression bombs, huge sparse worksheet dimensions, enormous shared-string tables, deep nesting, recursive archives, and oversized cells;
- XML external entities, DTD retrieval, entity expansion, and parser-specific recovery;
- macros, Excel 4.0 macro sheets, OLE/ActiveX objects, external links, DDE, embedded files, and formula injection being executed by an office suite or later consumer;
- encrypted/password-protected files producing partial or misleading reads;
- malformed containers that different libraries recover differently;
- path traversal, symlinks, duplicate member names, overwrite, and staging residue;
- accidental disclosure of sheet names, ranges, document text, headers, or extracted values in summary-safe output.

Controls should be fail-closed parsing, zero network, no subprocess office suite, no macro/formula/field execution, bounded streaming reads, private temporary storage only when unavoidable, cleanup on all exits, stable error codes, fuzz/adversarial fixtures, and the existing rule that safe summaries contain no source paths, keys, values, or discrepancy samples.

## Dependency consequences

The standard library has ZIP and XML primitives but no workbook semantic reader. Implementing OOXML directly would create a wide, shallow parser that Parison would have to secure and maintain. One pinned pure-Python workbook dependency is justified only if it produces a substantially deeper input module with a narrow contract. Supporting `.xlsb`, `.xls`, and `.ods` at the same time would require multiple parser stacks or an office-suite conversion dependency, multiplying behavior and cross-platform packaging work.

If v0.19 adopts `.xlsx`, use a pinned, audited OOXML library in read-only mode behind one deep projection module. Do not expose library objects or flags in recipes. Parison owns the stable projection and converts library values immediately into its existing input types. Packaging must follow the repository rule for built-wheel CI on Python 3.11–3.14, macOS, and Windows, with malformed and adversarial workbook fixtures on every platform.

## Design consequences

1. Define a **workbook projection** as a versioned input contract feeding unchanged Parison comparison modes; do not add a “spreadsheet diff” mode.
2. Keep format detection explicit in strict JSON recipes. Do not infer by extension alone, and reject a mismatch between declared format and package content.
3. Record projection identity—not sensitive selections—in full evidence: contract version, parser/version, formula mode, and source digest. Preserve summary-safe redaction rules.
4. Treat formula results as stored input values. Never calculate, refresh, open external links, invoke macros, or launch Excel/LibreOffice.
5. Preserve existing typed canonical row encoding after projection. A new source format must not fork keyed, multiset, aggregate, bundle, exit-code, or CLI JSON semantics.
6. Add format-specific preflight diagnostics and resource limits before row iteration so malformed or unsupported workbooks fail as input errors, not partial comparisons.
7. Make encrypted files, unsupported workbook features affecting the selected range, missing cached formula values, and ambiguous headers explicit errors or explicitly versioned policy outcomes—never silent coercions.
8. Describe extracted-document workflows as **upstream materialization plus receipt**. A receipt can bind source digest, extractor and version, options/model digests, and output digest without making Parison responsible for extraction truth.

## Non-goals

- rendering or visual equivalence for spreadsheets, PDF, DOCX, or images;
- evaluating formulas, refreshing pivots/queries/external links, running VBA or Excel 4.0 macros, or invoking an office application;
- editing, repairing, converting, sanitizing, or rewriting user files;
- OCR, layout analysis, table detection, semantic document diff, perceptual image similarity, or fuzzy text matching;
- password handling, decryption, digital-signature validation, malware scanning, or content-disarm/reconstruction;
- automatic schema/range/header discovery that approves comparison scope;
- recursively unpacking arbitrary archives;
- generic log parsing or email-thread reconstruction;
- claiming that equal extracted rows prove equal source documents, correct formula results, complete OCR, or equivalent visual meaning.

## Recommended future slice

After the compatibility release, consider a **reviewable spreadsheet projection** release, not a general unstructured-file release:

1. specify a versioned `.xlsx` values projection for one explicit worksheet and bounded range/table;
2. decide `.xlsm` by one crisp gate: include it only if macro presence can be detected, surfaced in full evidence, and no executable or external content is touched; otherwise reject it with a stable diagnostic;
3. require explicit stored-value versus formula-text mode, with no recalculation and fail-closed handling of missing formula caches;
4. map workbook values into the existing typed-row and canonicalization pipeline, including explicit blank, error, date/time, merge, hidden-state, and header rules;
5. enforce archive, worksheet, row, column, cell, and text bounds and add adversarial ZIP/XML/workbook fixtures;
6. prove deterministic output and identical semantics across Python 3.11–3.14, macOS, and Windows using built wheels;
7. document conversion guidance for `.xlsb`, `.xls`, and `.ods`, and a receipt pattern for PDF/DOCX/OCR/email/log extraction, without shipping those parsers.

The release completion gate should be: the same selected workbook values yield the same canonical rows and existing comparison result across the supported matrix; unsupported, active, ambiguous, stale, encrypted, or resource-exhausting inputs fail closed with stable machine-readable diagnostics; and no parser action performs network access, calculation, code execution, repair, or file conversion.
