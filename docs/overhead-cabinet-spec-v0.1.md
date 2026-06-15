# Overhead Cabinet Generator Spec v0.1

Status: **draft / skeleton only**  
Scope: **Overhead cabinet only** — do not inherit General Tall semantics.

## Purpose

Migrate the legacy overhead geometry rules from `fusion360-cabinet-generator/core/overhead_geometry.py`
into a standalone TypeScript generator under `modules/overheadCabinet/`, then wire it into
`fusion360-unified-cabinet-plugin/modules/overhead/`.

## Non-goals (explicit)

- No `style_1` / `style_2` top/bottom system semantics from General Tall
- No General Tall board taxonomy (`V1~V4`, `H34`, `VD`, `T4/T5`, `TH1/BH1`, etc.)
- No reuse of General Tall stacking / boundary resolver unless a shared primitive is extracted deliberately
- No Fusion body generation in v0.1 unless explicitly requested

## Legacy source of truth (reference only)

Primary reference:

- `fusion360-cabinet-generator/core/overhead_geometry.py`
- `fusion360-cabinet-generator/tests/test_overhead_geometry.py`

Key legacy constants to preserve when porting:

- divider thickness / feature groove width
- T1 / T3 / T4 dimensions and notch rules
- BP groove ranges
- divider tongue ranges
- screw hole placement rules

## Input contract (v0.1)

```ts
interface OverheadCabinetParams {
  cabinetWidth: number;
  cabinetDepth: number;
  cabinetHeight?: number;
  bottomThickness?: number;
  dividerTongueHeight?: number;
  routerDiameter?: number;
  featureWidth?: number;
  internalDividerCenterlines?: number[];
}
```

## Output contract (v0.1)

Follow the same high-level envelope as other unified-plugin generators:

```ts
interface OverheadCabinetResult {
  params: OverheadCabinetParams;
  boards: Board[];
  features: unknown[];
  validation: { errors: string[]; warnings: string[] };
  debug: Record<string, unknown>;
}
```

`Board` uses bbox + optional profile vectors. Overhead-specific feature types will be defined in
`modules/overheadCabinet/types.ts` as the port progresses.

## Implementation phases

1. **Skeleton (current)**
   - params/types/generator stub
   - node bridge script
   - overhead controller wired to bridge
   - one smoke test

2. **Geometry port**
   - port legacy Python rules to TS
   - golden tests from `test_overhead_geometry.py`

3. **Plugin integration**
   - palette inputs for overhead module
   - SVG preview
   - Fusion adapter (reuse shared `fusion/geometry_ops.py` only)

## Test plan

- `node modules/overheadCabinet/generator.test.ts`
- `node fusion360-unified-cabinet-plugin/tests/run_overhead_bridge_tests.js`
- Compare selected outputs against legacy Python tests before enabling Fusion generation

## Module boundaries

```text
modules/overheadCabinet/          # pure TS generator
fusion360-unified-cabinet-plugin/
  modules/overhead/controller.py  # UI -> bridge
  scripts/overhead_from_params.js   # node bridge
  tests/run_overhead_bridge_tests.js
```
