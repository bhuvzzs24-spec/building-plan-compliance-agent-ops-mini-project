"""Evidence-grounded comparisons for the historical Bangalore 2003 tables.

Only numeric cells parsed from verified retrieved passages are compared. This
module never treats the historical corpus as current law or municipal approval.
"""

from __future__ import annotations

import re
from typing import Any


_NUMBER_OR_DASH = r"(?:\d+(?:\.\d+)?|-)"
_TABLE4_BAND = (
    r"(?:Upto\s*6|Over\s*6\s*upto\s*9|Over\s*9\s*upto\s*12|"
    r"Over\s*12\s*upto\s*18|Over\s*18\s*upto\s*24|Over\s*24)"
)
_TABLE4_ROW = re.compile(
    rf"({_TABLE4_BAND})\s+((?:{_NUMBER_OR_DASH}\s+){{6}})"
    rf"({_TABLE4_BAND})\s+((?:{_NUMBER_OR_DASH}\s+){{6}})",
    re.IGNORECASE,
)
_TABLE6_AREA = re.compile(
    r"(?P<area>Upto\s*240|Over\s*240\s*Upto\s*500|"
    r"Over\s*500\s*Upto\s*750|Over\s*750\s*Upto\s*1000|Over\s*1000)",
    re.IGNORECASE,
)
_TABLE6_ROAD = re.compile(
    r"(?:Upto\s*6|Over\s*6\s*upto\s*9|Over\s*9\s*upto\s*12|"
    r"Over\s*12\s*upto\s*15|Over\s*15)",
    re.IGNORECASE,
)


def _dimension_matches(value: float, band: str) -> bool:
    normalized = re.sub(r"\s+", " ", band.strip().lower())
    up_to = re.fullmatch(r"upto\s*(\d+(?:\.\d+)?)", normalized)
    if up_to:
        return value <= float(up_to.group(1))
    over_to = re.fullmatch(
        r"over\s*(\d+(?:\.\d+)?)\s*upto\s*(\d+(?:\.\d+)?)",
        normalized,
    )
    if over_to:
        return float(over_to.group(1)) < value <= float(over_to.group(2))
    over = re.fullmatch(r"over\s*(\d+(?:\.\d+)?)", normalized)
    if over:
        return value > float(over.group(1))
    return False


def _table4_rows(text: str) -> list[dict[str, Any]]:
    if not re.search(r"\bTABLE\s*4\b", text, re.IGNORECASE):
        return []
    rows = []
    for match in _TABLE4_ROW.finditer(text):
        width_values = re.findall(_NUMBER_OR_DASH, match.group(2))
        depth_values = re.findall(_NUMBER_OR_DASH, match.group(4))
        if len(width_values) == 6 and len(depth_values) == 6:
            rows.append({
                # The printed page lays out the depth/front-rear table first
                # (left half), then the width/left-right table (right half).
                # pypdf preserves that reading order.
                "depth_band": match.group(1),
                "depth_values": width_values,
                "depth_evidence_terms": [match.group(1), *width_values],
                "width_band": match.group(3),
                "width_values": depth_values,
                "width_evidence_terms": [match.group(3), *depth_values],
            })
    return rows


def _table6_category(zone: str, development_area: str | None) -> str | None:
    if development_area in {"A", "B", "C"}:
        return development_area
    # Backward-compatible inference is intentionally strict. A bare "A" might
    # refer to another zoning scheme and is not enough to choose this table.
    folded = zone.lower()
    labels = {
        "A": "intensely developed area",
        "B": "moderately developed area",
        "C": "sparsely developed area",
    }
    matches = [code for code, phrase in labels.items() if phrase in folded]
    return matches[0] if len(matches) == 1 else None


def _table6_rows(text: str, category: str) -> list[dict[str, Any]]:
    if not re.search(r"\bTABLE\s*6\b", text, re.IGNORECASE):
        return []
    category_labels = {
        "A": r"A\s*[–—-]\s*INTENSELY\s+DEVELOPED\s+AREA",
        "B": r"B\s*[–—-]\s*MODERATELY\s+DEVELOPED\s+AREA",
        "C": r"C\s*[–—-]\s*SPARSELY\s+DEVELOPED\s+AREA",
    }
    markers = list(re.finditer(
        r"(?:A\s*[–—-]\s*INTENSELY\s+DEVELOPED\s+AREA|"
        r"B\s*[–—-]\s*MODERATELY\s+DEVELOPED\s+AREA|"
        r"C\s*[–—-]\s*SPARSELY\s+DEVELOPED\s+AREA)",
        text,
        re.IGNORECASE,
    ))
    start_match = next((
        marker for marker in markers
        if re.fullmatch(category_labels[category], marker.group(), re.IGNORECASE)
    ), None)
    if start_match is None:
        return []
    next_marker = next((marker for marker in markers if marker.start() > start_match.start()), None)
    section = text[start_match.end(): next_marker.start() if next_marker else len(text)]
    area_matches = list(_TABLE6_AREA.finditer(section))
    rows: list[dict[str, Any]] = []
    for index, match in enumerate(area_matches):
        stop = area_matches[index + 1].start() if index + 1 < len(area_matches) else len(section)
        remainder = section[match.end():stop]
        values = re.findall(r"\d+(?:\.\d+)?", remainder)
        road = _TABLE6_ROAD.search(remainder)
        if len(values) < 6 or road is None:
            continue
        area_label = re.sub(r"\s+", " ", match.group("area").strip().lower())
        area_bounds = {
            "upto 240": (0.0, 240.0),
            "over 240 upto 500": (240.0, 500.0),
            "over 500 upto 750": (500.0, 750.0),
            "over 750 upto 1000": (750.0, 1000.0),
            "over 1000": (1000.0, None),
        }.get(area_label)
        if area_bounds is None:
            continue
        rows.append({
            "area_label": match.group("area"),
            "area_bounds": area_bounds,
            "coverage_residential": float(values[0]),
            "far_residential": float(values[1]),
            "coverage_commercial": float(values[2]),
            "far_commercial": float(values[3]),
            "coverage_public": float(values[4]),
            "far_public": float(values[5]),
            "road_band": road.group(),
            "evidence_terms": [match.group("area"), *values[:6], road.group()],
        })
    return rows


def _area_matches(value: float, bounds: tuple[float, float | None]) -> bool:
    lower, upper = bounds
    if upper is None:
        return value > lower
    if lower == 0:
        return value <= upper
    return lower < value <= upper


def _evidence_for_page(
    verified_clauses: list[dict[str, Any]], page: int, table_marker: str
) -> tuple[dict[str, Any] | None, str]:
    matches = [
        clause for clause in verified_clauses
        if clause.get("page") == page
        and clause.get("source")
        and clause.get("text")
    ]
    combined = "\n".join(clause["text"] for clause in matches)
    if not re.search(table_marker, combined, re.IGNORECASE):
        return None, combined
    marker_clause = next((
        clause for clause in matches
        if re.search(table_marker, clause["text"], re.IGNORECASE)
    ), matches[0] if matches else None)
    return marker_clause, combined


def _citation(clause: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not clause:
        return []
    return [{
        "source": clause["source"],
        "page": clause["page"],
        "clause_id": clause["clause_id"],
        "excerpt": clause["text"],
    }]


def _clause_supporting_terms(
    verified_clauses: list[dict[str, Any]], page: int, terms: list[str]
) -> dict[str, Any] | None:
    required = {
        token.lower() for term in terms
        for token in re.findall(r"[a-z0-9]+", str(term).lower())
    }
    candidates = [
        clause for clause in verified_clauses
        if clause.get("page") == page and clause.get("source") and clause.get("text")
    ]
    for clause in candidates:
        tokens = set(re.findall(r"[a-z0-9]+", clause["text"].lower()))
        if required and required.issubset(tokens):
            return clause
    return None


def _finding(
    *, provision: str, rule: str, inputs: dict[str, Any], threshold: Any,
    comparison: str, status: str, justification: str,
    evidence_clause: dict[str, Any] | None,
) -> dict[str, Any]:
    citations = _citation(evidence_clause)
    return {
        "provision": provision,
        "rule": rule,
        "source": evidence_clause.get("source") if evidence_clause else None,
        "page": evidence_clause.get("page") if evidence_clause else None,
        "inputs": inputs,
        "threshold": threshold,
        "comparison": comparison,
        "status": status,
        "outcome": status,
        "justification": justification,
        "citations": citations,
        "evidence_excerpt": citations[0]["excerpt"] if citations else None,
    }


def evaluate_historical_rules(
    details: dict[str, Any], verified_clauses: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Compare submitted values to numeric cells extracted from verified pages.

    Table 4 page 22 is scoped to buildings up to 9.5m. Table 6 page 24 is
    selected only when development-area category, use, plot band, and road band
    are all supported by the submitted inputs and retrieved evidence.
    """
    findings: list[dict[str, Any]] = []
    table4_clause, table4_text = _evidence_for_page(verified_clauses, 22, r"\bTABLE\s*4\b")
    table4_rows = _table4_rows(table4_text)
    use = details.get("building_use")
    use_index = {"residential": 0, "commercial": 2}.get(use)
    if not table4_rows or not table4_clause:
        findings.append(_finding(
            provision="setbacks", rule="Historical Table 4 (Bye-law 9.2), PDF page 22",
            inputs={"site_width": details.get("site_width"), "site_depth": details.get("site_depth"), "proposed_height": details.get("proposed_height")},
            threshold="Not available from verified retrieved evidence",
            comparison="Required table evidence was not retrieved and verified.",
            status="UNRESOLVED", justification="No setback comparison is made without a verified Table 4 passage.",
            evidence_clause=None,
        ))
    elif float(details.get("proposed_height", 0)) > 9.5:
        findings.append(_finding(
            provision="setbacks", rule="Historical Table 4 (Bye-law 9.2) applies only up to 9.5m height",
            inputs={"proposed_height": details.get("proposed_height")}, threshold="Table scope: <= 9.5m",
            comparison=f"{details.get('proposed_height')}m exceeds this table's scope; no higher-height threshold was extracted.",
            status="UNRESOLVED", justification="A different historical provision must be retrieved and its applicability reviewed.",
            evidence_clause=table4_clause,
        ))
    elif details.get("site_width") is None or details.get("site_depth") is None or use_index is None:
        findings.append(_finding(
            provision="setbacks", rule="Historical Table 4 (Bye-law 9.2), PDF page 22",
            inputs={"building_use": use, "site_width": details.get("site_width"), "site_depth": details.get("site_depth")},
            threshold="Selected by site width/depth bands and building-use columns",
            comparison="A required site dimension or supported use column is missing.",
            status="UNRESOLVED", justification="The table cells cannot be selected safely from the supplied fields.",
            evidence_clause=table4_clause,
        ))
    else:
        width = float(details["site_width"])
        depth = float(details["site_depth"])
        width_row = next((row for row in table4_rows if _dimension_matches(width, row["width_band"])), None)
        depth_row = next((row for row in table4_rows if _dimension_matches(depth, row["depth_band"])), None)
        for direction, row, band_key, value_index, proposed_key in (
            ("left", width_row, "width_band", use_index, "proposed_left_setback"),
            ("right", width_row, "width_band", use_index + 1, "proposed_right_setback"),
            ("front", depth_row, "depth_band", use_index, "proposed_front_setback"),
            ("rear", depth_row, "depth_band", use_index + 1, "proposed_rear_setback"),
        ):
            band = row.get(band_key) if row else None
            cell = row["width_values" if band_key == "width_band" else "depth_values"][value_index] if row else None
            evidence_terms = row.get("width_evidence_terms" if band_key == "width_band" else "depth_evidence_terms", []) if row else []
            row_clause = _clause_supporting_terms(verified_clauses, 22, evidence_terms) if evidence_terms else None
            input_value = details.get(proposed_key)
            numeric_threshold = float(cell) if cell and cell != "-" else None
            if numeric_threshold is None or row_clause is None:
                status = "UNRESOLVED"
                threshold: Any = (
                    f"Table cell {cell!r} is not a numeric minimum" if cell
                    else "No matching table band"
                )
                comparison = "No numeric comparison is supported by a verified passage containing this table row and cell."
                reason = "The source cell is a dash, no numeric row is selected, or the exact row cell could not be tied to one retrieved passage."
            elif input_value is None:
                status = "UNRESOLVED"
                threshold = f">= {numeric_threshold:g} m"
                comparison = f"Proposed {direction} setback was not supplied; required historical minimum is {numeric_threshold:g} m."
                reason = "A comparison needs the proposed setback measurement."
            else:
                proposed = float(input_value)
                passed = proposed >= numeric_threshold
                status = "SATISFIED" if passed else "VIOLATED"
                threshold = f">= {numeric_threshold:g} m"
                comparison = f"{proposed:g} m {'>=' if passed else '<'} {numeric_threshold:g} m"
                reason = (
                    f"The submitted {direction} setback meets the historical table minimum."
                    if passed else f"The submitted {direction} setback is below the historical table minimum."
                )
            findings.append(_finding(
                provision=f"setbacks.{direction}",
                rule=f"Table 4 residential/commercial/public setback by {band_key.replace('_band', '')} band {band or 'unknown'}; proposed height is within the table's <=9.5m scope",
                inputs={"building_use": use, "site_width": width, "site_depth": depth, "proposed_height": details.get("proposed_height"), "proposed_setback": input_value},
                threshold=threshold, comparison=comparison, status=status,
                justification=f"{reason} Values are transcribed from the retrieved historical 2003 table; they are not a current approval standard.",
                evidence_clause=row_clause or table4_clause,
            ))

    table6_clause, table6_text = _evidence_for_page(verified_clauses, 24, r"\bTABLE\s*6\b")
    category = _table6_category(str(details.get("zone", "")), details.get("development_area"))
    table6_rows = _table6_rows(table6_text, category) if category else []
    if not table6_clause or not table6_rows:
        why = (
            "The historical Table 6 development-area category is not explicitly known."
            if category is None else "A verified matching Table 6 row was not retrieved."
        )
        for metric, proposal_key in (("coverage", "proposed_coverage_percent"), ("FAR", "proposed_far")):
            findings.append(_finding(
                provision=f"far_coverage.{metric.lower()}", rule="Historical Table 6 (Bye-laws 9.2 and 9.10), PDF page 24",
                inputs={"building_use": use, "plot_area": details.get("plot_area"), "road_width": details.get("road_width"), "development_area": category, "proposed_value": details.get(proposal_key)},
                threshold="Not available from a verified matching table row", comparison=why,
                status="UNRESOLVED", justification="No coverage/FAR limit is inferred from an unselected or absent row.",
                evidence_clause=table6_clause,
            ))
    else:
        column = {"residential": "residential", "commercial": "commercial", "institutional": "public"}.get(use)
        row = next((item for item in table6_rows
                    if _area_matches(float(details["plot_area"]), item["area_bounds"])
                    and _dimension_matches(float(details["road_width"]), item["road_band"])), None)
        if column is None or row is None:
            message = "No unique Table 6 row matches both the submitted plot-area and road-width bands." if row is None else "No Table 6 column supports this building-use category."
            for metric, proposal_key in (("coverage", "proposed_coverage_percent"), ("FAR", "proposed_far")):
                findings.append(_finding(
                    provision=f"far_coverage.{metric.lower()}", rule="Historical Table 6 (Bye-laws 9.2 and 9.10), PDF page 24",
                    inputs={"building_use": use, "plot_area": details.get("plot_area"), "road_width": details.get("road_width"), "development_area": category, "proposed_value": details.get(proposal_key)},
                    threshold="No matching row", comparison=message, status="UNRESOLVED",
                    justification="The numeric limit is not selected when area, road, zone category, and use do not align with one source row.",
                    evidence_clause=table6_clause,
                ))
        else:
            row_clause = _clause_supporting_terms(
                verified_clauses, 24, row["evidence_terms"]
            )
            thresholds = (
                ("coverage", "proposed_coverage_percent", row[f"coverage_{column}"], "%", "maximum plot coverage"),
                ("FAR", "proposed_far", row[f"far_{column}"], "", "maximum floor-area ratio"),
            )
            for metric, proposal_key, limit, unit, rule_name in thresholds:
                submitted = details.get(proposal_key)
                if row_clause is None:
                    status = "UNRESOLVED"
                    threshold = "Parsed row lacks a verified passage containing the exact selected values"
                    comparison = "No numeric comparison is made without an exact-row citation."
                    reason = "The selected values could not be tied to one verified retrieved passage."
                elif submitted is None:
                    status = "UNRESOLVED"
                    threshold = f"<= {limit:g}{unit}"
                    comparison = f"Proposed {metric} was not supplied; selected historical row limit is {limit:g}{unit}."
                    reason = "The maximum is sourced but the submitted value is missing."
                else:
                    value = float(submitted)
                    passed = value <= limit
                    status = "SATISFIED" if passed else "VIOLATED"
                    threshold = f"<= {limit:g}{unit}"
                    comparison = f"{value:g}{unit} {'<=' if passed else '>'} {limit:g}{unit}"
                    reason = (
                        f"The proposed {metric} is within the selected historical row."
                        if passed else f"The proposed {metric} exceeds the selected historical row."
                    )
                findings.append(_finding(
                    provision=f"far_coverage.{metric.lower()}",
                    rule=f"Table 6 {category} area, {use} use, plot {row['area_label']} m², road {row['road_band']} m: {rule_name}",
                    inputs={"building_use": use, "plot_area": details.get("plot_area"), "road_width": details.get("road_width"), "development_area": category, "proposed_value": submitted},
                    threshold=threshold, comparison=comparison, status=status,
                    justification=f"{reason} The selected row came from the retrieved historical table and does not establish current legal compliance.",
                    evidence_clause=row_clause or table6_clause,
                ))
    return findings
