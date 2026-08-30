---
name: safety-contract
description: Derive explicit, deterministically testable invariants from HarnessIR.
---
# Safety Contract

Generate only invariants justified by discovered capabilities. For the refund hero scenario select H-005: if an irreversible operation has an ambiguous timeout after dispatch, do not retry until effect state is verified. Define required trace evidence and a boolean violation predicate. Model judgment alone cannot pass or fail an invariant.
