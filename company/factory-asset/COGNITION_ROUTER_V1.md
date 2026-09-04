# Blueprint Reuse and Cognition Router v1

Task: `FA-134`
Status: PASS
Date: 2026-09-04

## Goal

Prevent Division01 and Executive from becoming per-image bottlenecks while preserving their intended cognition roles.

## Reuse-first path

Hermes reuses a fixed Blueprint with zero cognition calls only when all of the following remain true: family, product expression, provider capability, rights assumptions, quality requirements and marketplace route match; the Blueprint is fixed and not stale; and no semantic or strategic escalation signal is active. Existing Blueprints must be SHA-256 pinned.

## Division01 triggers

Division01 is invoked only for missing/not-fixed/stale/incompatible Blueprints, semantic QA defects, required family differentiation, bounded semantic questions or material product-expression change. It has semantic-author authority only and no Worker/provider authority.

## Executive triggers

Executive is invoked only for new-family promotion, material product-expression change, repeated outcome strategy challenge, material portfolio cannibalization or explicit executive escalation. It is strategic review only and does not author the Blueprint in place.

## Sequencing

Typical new-family path:

`Hermes -> Division01 AUTHOR -> Executive CHALLENGE -> Hermes routes any required revision -> Division01 final -> Hermes freezes accepted Blueprint`

A routine reusable Blueprint is simply:

`Hermes -> REUSE_FIXED_BLUEPRINT`

The router emits policy decisions only. It performs no model call, Worker spawn, provider dispatch, upload, publication or spend.