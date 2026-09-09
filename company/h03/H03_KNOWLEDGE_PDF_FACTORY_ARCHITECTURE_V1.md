# H03 Knowledge Factory + PDF Factory Architecture v1

Status: CANONICAL BOOTSTRAP
Date: 2026-09-09
Holding: H03

## 1. Holding identity

H03 is a Knowledge / Document Product Holding. It is not a copy of the H01 Hermes + OpenCode organism and it does not own the global Mission Control, global Universal MCP, or global principal pool merely because those runtimes may later be hosted on the same Windows machine.

The default operating doctrine is:

```text
Mission Control = coordination / state / evidence / authority gates
Web AI fabric   = cognition and non-deterministic production capability
Local code      = deterministic mechanics
DIE State Manager = canonical Company Truth writer
```

Hermes and OpenCode remain optional execution backends where a workload proves unique value; they are not mandatory H03 runtime layers.

## 2. Plane separation

```text
GLOBAL CONTROL PLANE (logical global authority)
  Mission Control + Universal MCP + global principals
              |
              +-----------------------------+
                                            |
H03 DOMAIN PLANE                            |
  Knowledge Factory                         |
       |                                    |
       v                                    |
  Knowledge Package                         |
       |                                    |
       v                                    |
  Product Blueprint                         |
       |                                    |
       v                                    |
  Document AST                              |
       |                                    |
       v                                    |
  PDF Factory / renderers <-----------------+
       |
       v
  QA + rights + metadata + package manifest
```

Shared Windows capabilities remain separate services and are consumed through contracts rather than embedded into H03 product code:

- `D:\OAUTH` / web-ai-adapter: text and image web-AI capability fabric.
- `D:\MAIL`: authentication/OTP support capability, never product truth.
- `D:\imaginer`: large-scale standalone visual production capability.

## 3. Knowledge Factory responsibility

Knowledge Factory transforms governed sources into reusable structured knowledge. It owns source identity, evidence units, claim/evidence linkage, normalization, fact/consistency checks, provenance, rights/source constraints, versioning, and accepted Knowledge Package output.

Knowledge is presentation-independent. A Knowledge Package may later feed PDF, HTML, EPUB, DOCX, slides, websites, newsletters, courses, RAG systems, or another Holding where policy permits.

The minimum chain is:

```text
source packet
  -> evidence units
  -> claims linked to evidence
  -> rights/provenance validation
  -> accepted knowledge package
```

An LLM may propose or synthesize content, but it is never the provenance source by itself. Unsupported claims fail closed.

## 4. PDF Factory responsibility

PDF Factory consumes an accepted Knowledge Package plus a Product Blueprint. It owns the structured document model, layout/template selection, rendering, fonts/images, pagination, metadata, deterministic naming, technical PDF validation, visual render validation, package manifests, hashes and lineage receipts.

Initial product forms include ebook, guide, handbook, report, checklist, worksheet, workbook, template, reference sheet, playbook and research brief.

Content semantics remain separate from rendering:

```text
Knowledge Package
  -> Product Blueprint
  -> Document AST
  -> Renderer
  -> PDF
```

A renderer is replaceable. The Knowledge Package and Product Blueprint are not PDF-specific.

## 5. Rights and provenance boundary

Every source packet declares a rights state. MVP supports `INTERNAL_ORIGINAL` and the schema leaves room for later governed external-source policies. Claim records must contain at least one evidence reference resolving to an evidence unit. Output receipts retain source IDs, knowledge package ID, product ID and build job ID.

No browser/OAuth/session bytes are product data. Authentication/session state is host-local/reprovisionable capability state.

## 6. Economic instrumentation boundary

Every bounded H03 product build carries:

- `economic_trace_id`
- Work Card ID
- product ID
- Knowledge Package ID
- build job ID
- Founder active minutes
- observed compute/resource data
- cash/direct cost
- shared-cost attribution status
- artifact lineage
- future listing/order/revenue identity

Unknown values remain `UNKNOWN`, `PARTIAL`, or `UNPROVEN`; they are never coerced to zero. H03 does not append directly to `state/ECONOMICS.jsonl`. Canonical Company Truth remains owned by logical writer `die-state-manager`. Company canon now includes `ECON-002A` State Manager commit semantics and `ECON-002B` shadow admission validation; H03 may prepare `validated_not_committed` candidates, while live canonical submit authority remains separately gated.

## 7. Determinism and portability

H03 product code, schemas, tests, templates and bounded proof artifacts live in Git. Host-local virtual environments, browser profiles, secrets, OAuth state, caches and service bindings do not.

The first PDF renderer uses ReportLab invariant mode and validates the emitted file with pypdf plus a PDFium raster pass. Repeated rendering of the same Document AST must produce byte-identical PDF output for the bounded MVP.

## 8. MVP acceptance

`H03-MVP-001` is an internal-original guide proving the pipeline rather than market demand:

```text
source/evidence packet
-> knowledge package
-> blueprint
-> document AST
-> deterministic PDF
-> reopen/parse validation
-> raster visual validation
-> metadata/page-count checks
-> SHA-256 manifest + lineage/economic receipt
```

No external sale, publication, credential change, spend, DNS change, Mission Control cutover or Company economics write is part of this proof.


## 9. Production organism continuation

The post-bootstrap opportunity, worker-runtime, research, product, commerce, growth and analytics architecture is canonicalized in `company/h03/H03_PRODUCTION_ORGANISM_V1.md`; executable dependency truth remains `company/h03/task-graph-v1.json`.
