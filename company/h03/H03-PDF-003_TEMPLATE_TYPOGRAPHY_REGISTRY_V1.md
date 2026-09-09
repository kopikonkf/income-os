# H03-PDF-003 - Reusable Template + Typography Registry v1

Status: DONE / PASS
Date: 2026-09-09

Layout is a renderer concern, not Knowledge Package truth. One Document AST can be rendered through multiple named templates. Template selection changes margins, spacing and typography roles without rewriting claims, Knowledge Packages, Product Blueprints or AST blocks.

V1 registry ships `guide.clean.v1`, `report.compact.v1`, and `worksheet.spacious.v1`. Typography uses PDF Core 14 Helvetica/Helvetica-Bold only, deliberately avoiding machine-local font files and font-license migration cargo.

Backward determinism is an acceptance gate: rendering the MVP AST with default `guide.clean.v1` must retain canonical SHA-256 `8199048f4a9ee0f70a4e0b62c07c7617ab61b9077cf6700311192617c7eb20ee`.
