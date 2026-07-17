# Method Engine

The v1.1.0 engine executes a method snapshot rather than relying on hidden constants.

1. Validate the method snapshot.
2. Normalize the input using snapshot defaults and vocabularies.
3. Resolve each component through its named weight table.
4. Sum raw component weights.
5. Apply the versioned multiplier.
6. Round half up and clamp to the method bounds.
7. Select the matching threshold.
8. Evaluate ordered flag and action rules.
9. Store the result separately from the human decision.

Component metadata provides a rationale and remediation for every weight. The method snapshot is included in each record so later software can reconstruct the exact analytical context.
