# Canonical Narrative Risk Contract

## Identity

- Contract: `urn:catalyst:narrative-risk:contract:canonical` version `1.1.0`
- Method: `urn:catalyst:narrative-risk:method:transparent-heuristic` version `1.1.0`
- Record schema: `https://sustainablecatalyst.com/schemas/narrative-risk/record/1.1.0`
- Input schema: `https://sustainablecatalyst.com/schemas/narrative-risk/input/1.1.0`

## Layer boundaries

`normalized_input` contains only the cleaned claim and controlled analytical inputs. `calculations` contains deterministic method work. `interpretation` contains method-generated language. `human_decision` contains the accountable review disposition and is not calculated from risk.

## Default and invalid-value behavior

Omitted optional analytical fields use the defaults stored in the method snapshot. A supplied value outside its controlled vocabulary is rejected. This prevents accidental semantic replacement during normalization.

## Digests

Canonical JSON sorts object keys recursively, preserves array order and UTF-8 text, removes insignificant whitespace, and represents integer-valued numbers as integers. SHA-256 digests cover the method snapshot, normalized input, and record payload excluding the self-referential reproducibility block.
