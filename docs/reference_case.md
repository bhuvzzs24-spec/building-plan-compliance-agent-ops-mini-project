# Reference case: small residential plot beside a narrow road

## Purpose

This case tests whether retrieval finds separate setback and road-width-dependent FAR/coverage provisions. These values are from the historical local PDF (2003) and are for retrieval-path verification only. They are not a current legal answer. Currentness, jurisdiction, zoning, and later amendments remain unverified.

## Proposal values

- Building use: residential
- Plot area: 200 m²
- Site width: 10 m
- Site depth: 20 m
- Abutting road width: 6 m
- Proposed height: 9 m
- Historical development-area assumption for Table 6: A, intensely developed

## Corpus passages to show

- Table 4, PDF page 22 (bye-law 9.2): setbacks for residential buildings up to 9.5 m in height. For the supplied 10 m site width and 20 m site depth, historical table cells are 1.5 m left and right, 4.0 m front, and 3.0 m rear.
- Table 6, PDF page 24 (bye-laws 9.2 and 9.10): coverage and FAR depend on plot area, road width, use, and area category. For the historical A-area residential row, plot up to 240 m² and road up to 6 m, the table states maximum plot coverage 65% and maximum FAR 0.75.

The example shows why the setback table alone is insufficient: separate Table 6 evidence binds the same proposal through its road-width and plot-area columns.

## Expected system behavior

1. Search setback and road-width/FAR provisions as separate obligations.
2. Return both exact source/page citations and retrieved text.
3. Do not claim the proposal passes or fails a current regulation. The example lacks a validated current source set and authority confirmation.
4. Route to specialist-review and explain that evidence is historical and the area-category assumption must be confirmed.

## Source

data/bye_laws/Bangalore-Building-Byelaws.pdf; the official BBMP URL is recorded in docs/regulation_sources.md. PDF page numbering is the page number shown by a PDF reader.
