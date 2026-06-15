# General Tall Validation Output

Clean V1.1 validation summary regenerated after flap validator direction fix and H34 warning downgrade.

## Summary Table

| Case | Kind | Status | Expected | Can Generate | Height Diff | Invalid Boards | Main Warning | H34 Debug Notes |
|---|---|---:|---:|---:|---:|---:|---|---:|
| GT-01-standard-3-zone | MAIN | READY | READY | true | 0 | 0 |  | 6 |
| GT-02-simple-2-zone | MAIN | READY | READY | true | 0 | 0 |  | 0 |
| GT-03-top-flap-valid | MAIN | READY | READY | true | 0 | 0 |  | 0 |
| GT-04-bottom-flap-valid | MAIN | READY | READY | true | 0 | 0 |  | 5 |
| GT-05-avoidance-valid | MAIN | READY | READY | true | 0 | 0 |  | 5 |
| GT-06-narrow-width-valid | MAIN | READY | READY | true | 0 | 0 |  | 5 |
| GT-07-shallow-depth-valid | MAIN | READY | READY | true | 0 | 0 |  | 6 |
| GT-08-extra-tall-valid | MAIN | READY | READY | true | 0 | 0 |  | 6 |
| GT-09-low-cabinet-valid | MAIN | READY | READY | true | 0 | 0 |  | 0 |
| GT-10-mixed-functions-valid | MAIN | READY | READY | true | 0 | 0 |  | 6 |
| NEG-01-height-mismatch-blocked | NEG | BLOCKED | BLOCKED | false | -295 | 0 | Height mismatch: expected CH = 2000; calculated CH = 1705; difference = -295. | 6 |
| NEG-02-middle-flap-invalid | NEG | FAIL | FAIL | false | 0 | 22 | Top flap must be the highest functional zone directly below Top System. | 0 |
| NEG-03-over-height-blocked | NEG | BLOCKED | BLOCKED | false | 555 | 0 | Height mismatch: expected CH = 1200; calculated CH = 1755; difference = 555. | 0 |
| NEG-04-fill-last-zone-invalid | NEG | BLOCKED | BLOCKED | false | 240 | 0 | Height mismatch: expected CH = 900; calculated CH = 1140; difference = 240. | 0 |
| NEG-05-invalid-avoidance | NEG | FAIL | FAIL | false | 0 | 23 | Avoidance depth must be > 0; received -1. | 6 |

## Notes

- Main GT-01 through GT-10 cases are READY with Height Diff = 0, Can Generate = true, Invalid Boards = 0, and no Main Warning.
- Expected H34 clamp/no-intersection diagnostics are retained in `debug.h34Clearance` and no longer pollute validation warnings.
- Negative cases remain BLOCKED / FAIL for expected reasons.
