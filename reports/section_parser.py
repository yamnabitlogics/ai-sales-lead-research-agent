"""
reports/section_parser.py
─────────────────────────
Shared parsing for crew output — used by Flask UI and PDF generator.
"""

from __future__ import annotations

import json
import re
from typing import Any


SECTION_MARKERS = {
    "tech_stack": [
        r"tech(?:nology)?\s*stack",
        r"infrastructure",
        r"detected\s*technolog",
    ],
    "decision_makers": [
        r"decision\s*maker",
        r"key\s*(?:decision|contact|people|leadership)",
        r"leadership\s*team",
        r"contacts?",
    ],
    "opportunities": [
        r"business\s*opportunit",
        r"sales\s*opportunit",
        r"opportunit(?:y|ies)",
        r"pain\s*point",
    ],
    "email": [
        r"outreach\s*email",
        r"cold[\s-]*outreach",
        r"personalized\s*email",
        r"subject\s*line",
        r"^subject:",
    ],
}

OVERVIEW_MARKERS = [
    r"company\s*overview",
    r"executive\s*summary",
    r"about\s*(?:the\s*)?company",
    r"research\s*summary",
]


def _clean_markdown(text: str) -> str:
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1 (\2)", text)
    text = re.sub(r"---+", "", text)
    return text.strip()


def _is_heading(line: str) -> bool:
    """
    Decide whether a line LOOKS like a section heading, before we even
    bother checking its text against the section keyword patterns.

    This is the guard that was missing: previously every line in the
    raw output was checked against the section keywords, so an ordinary
    sentence that happened to contain a word like "opportunity" or
    "contacts" would silently start a brand-new section mid-paragraph.
    """
    stripped = line.strip()
    if not stripped:
        return False

    # Markdown heading: "## Key Decision Makers"
    if re.match(r"^#{1,6}\s+\S", stripped):
        return True

    # Numbered heading: "3. Key Decision Makers"
    if re.match(r"^\d+\.\s+[A-Z]", stripped):
        return True

    # Fully bolded line used as a heading: "**Key Decision Makers**"
    if re.match(r"^\*\*[^*]+\*\*:?$", stripped):
        return True

    # Short, title-case-ish line with no terminal punctuation and no
    # mid-sentence markers (colons in the middle, commas, periods).
    # Real prose sentences are almost always longer than this or end
    # in a period, so this stays safe while still catching plain-text
    # headings like "Key Decision Makers" or "Business Opportunities".
    if (
        len(stripped) <= 60
        and stripped[0].isupper()
        and not stripped.endswith((".", ",", ";", ")"))
        and not re.search(r"https?://", stripped)
        and stripped.count(":") == 0
    ):
        return True

    return False


def _heading_matches(line: str, patterns: list[str]) -> bool:
    lower = _clean_markdown(line).lower()
    return any(re.search(p, lower) for p in patterns)


def _detect_section(line: str) -> str | None:
    if _heading_matches(line, SECTION_MARKERS["email"]):
        return "email"
    if _heading_matches(line, SECTION_MARKERS["opportunities"]):
        return "opportunities"
    if _heading_matches(line, SECTION_MARKERS["decision_makers"]):
        return "decision_makers"
    if _heading_matches(line, SECTION_MARKERS["tech_stack"]):
        return "tech_stack"
    if _heading_matches(line, OVERVIEW_MARKERS):
        return "overview"
    return None


def parse_sections(raw_output: str) -> dict[str, str]:
    sections = {
        "overview": "",
        "tech_stack": "",
        "decision_makers": "",
        "opportunities": "",
        "email": "",
    }
    current = "overview"

    for line in raw_output.split("\n"):
        # Only lines that actually look like a heading are allowed to
        # switch the current section. This is what stops a normal
        # sentence mentioning "opportunity" or "contacts" from hijacking
        # the parser mid-paragraph.
        if _is_heading(line):
            detected = _detect_section(line)
            if detected:
                current = detected
                continue
        sections[current] += line + "\n"

    return sections


def _relaxed_json_parse(blob: str) -> dict | None:
    """
    Best-effort repair for the almost-JSON the model sometimes emits
    (missing opening quotes on keys, missing commas between array
    items). Returns None if it still can't be parsed - callers should
    treat that as "no usable JSON" rather than crashing.
    """
    text = blob
    # Missing opening quote on a key: `frontend": [` -> `"frontend": [`
    text = re.sub(r'(?<=[{,\s])(\w[\w_]*)"\s*:', r'"\1":', text)
    # Missing commas between adjacent quoted array items on separate lines
    text = re.sub(r'"\s*\n\s*"', '",\n"', text)
    text = re.sub(r'\]\s*\n\s*"', '],\n"', text)
    text = re.sub(r'"\s*\n\s*\}', '"\n}', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


_CONJUNCTION_START = re.compile(
    r"^(and|or|the|for|with|to|of|in|that|which|from|by)\b", re.I
)
_NOISE_VALUES = {"none detected", "none", "n/a", "unknown"}


def _is_plausible_tech_name(part: str) -> bool:
    """
    Reject fragments left over from splitting a descriptive sentence at
    commas - e.g. "and insights", "and redundancy", "manage content".
    Real technology/tool names are short and don't start mid-clause.
    """
    part = part.strip()
    if not part or len(part) > 45:
        return False
    if part.lower() in _NOISE_VALUES:
        return False
    if _CONJUNCTION_START.match(part):
        return False
    if len(part.split()) > 6:
        return False
    return True


def parse_tech_stack(section_text: str) -> list[str]:
    items: list[str] = []

    json_match = re.search(r"\{[\s\S]*\}", section_text)
    remainder = section_text

    if json_match:
        data = None
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            data = _relaxed_json_parse(json_match.group())

        if isinstance(data, dict):
            for key in ("frontend", "backend", "cloud", "databases", "third_party_apis"):
                val = data.get(key, [])
                if isinstance(val, list):
                    items.extend(str(v).strip() for v in val if v)
                elif isinstance(val, str) and val:
                    items.append(val.strip())

        # Whether or not it parsed, strip the JSON block out before we
        # fall through to line-based parsing below - otherwise its raw
        # syntax (braces, bare keys, brackets) gets treated as text and
        # pollutes the tag list with garbage fragments.
        remainder = section_text[: json_match.start()] + section_text[json_match.end():]

    for line in remainder.split("\n"):
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        clean = _clean_markdown(line)
        if not clean or re.match(r"^(frontend|backend|cloud|databases|third)", clean, re.I):
            continue

        # Lines like "React - Core JavaScript framework for building..."
        # only the name before the dash is a usable tag; the rest is a
        # description and shouldn't become part of the tag text.
        name_match = re.match(r"^([\w][\w\s/\.\+\-]{1,40}?)\s+[-–—]\s+\S", clean)
        if name_match:
            items.append(name_match.group(1).strip())
            continue

        if clean.startswith(("-", "*", "•")):
            clean = clean.lstrip("-*• ").strip()

        # A genuine comma-separated list of short tech names ("React,
        # TypeScript, HTML5") is fine to split. A prose sentence that
        # happens to contain commas ("...supports analytics and
        # insights, Stories and Push Notifications, photo optimization
        # and media transformation services...") is NOT a tag list and
        # must not be exploded into fragments. Only split when the
        # whole line is short and doesn't read like a sentence.
        if "," in clean and len(clean) < 150 and not clean.endswith((".", "!")):
            for part in re.split(r"[,;|]", clean):
                part = part.strip().strip("\"'")
                if _is_plausible_tech_name(part):
                    items.append(part)
            continue

        if _is_plausible_tech_name(clean):
            items.append(clean)

    return list(dict.fromkeys(items))[:30]


def parse_decision_makers(section_text: str) -> list[dict[str, str]]:
    makers: list[dict[str, str]] = []

    for line in section_text.split("\n"):
        if "|" not in line or "---" in line:
            continue
        cols = [c.strip() for c in line.split("|") if c.strip()]
        if len(cols) >= 2 and cols[0].lower() not in {"name", "full name", "contact"}:
            makers.append({
                "name": _clean_markdown(cols[0]),
                "title": _clean_markdown(cols[1]),
                "linkedin": _clean_markdown(cols[2]) if len(cols) > 2 else "",
                "email": _clean_markdown(cols[3]) if len(cols) > 3 else "",
                "background": "",
            })

    if not makers:
        block_re = re.compile(
            r"(?:^|\n)\s*(?:[-*•]|\d+\.)\s*\*?\*?(.+?)\*?\*?\s*[-–—]\s*(.+?)(?:\s*[-–—]\s*(https?://\S+))?",
            re.MULTILINE,
        )
        for match in block_re.finditer(section_text):
            makers.append({
                "name": _clean_markdown(match.group(1)),
                "title": _clean_markdown(match.group(2)),
                "linkedin": match.group(3) or "",
                "email": "",
                "background": "",
            })

    return makers[:5]


def _extract_field(text: str, label: str) -> str:
    pattern = rf"\*?\*?{label}\*?\*?\s*:?\s*(.+?)(?=\n\s*\*?\*?(?:Pain Point|Proposed Solution|Business Impact|Opportunity)\*?\*?\s*:|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return _clean_markdown(match.group(1)).strip() if match else ""


def _is_opportunity_heading(line: str) -> bool:
    """
    True only for lines that look like a genuine "Opportunity N" or
    numbered heading - short, and not a full sentence. Without this
    guard, ANY numbered item inside a sentence (e.g. "...vendors: 1.
    AWS, 2. Azure, 3. Google Cloud Storage for temporary media
    staging...") gets mistaken for a new opportunity's title.
    """
    stripped = line.strip()
    if not stripped:
        return False
    match = re.match(
        r"^(?:#{1,3}\s*)?(?:\*\*)?(?:Opportunity\s*)?(\d+)[.:)\s-]+(.*)$",
        stripped,
        re.IGNORECASE,
    )
    if not match:
        return False
    rest = match.group(2).strip().rstrip("*").strip()
    if len(rest) > 80:
        return False
    if rest.endswith((".", "!")) and len(rest) > 50:
        return False
    return True


def parse_opportunities(section_text: str) -> list[dict[str, str]]:
    opportunities: list[dict[str, str]] = []

    lines = section_text.split("\n")
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if _is_opportunity_heading(line) and current:
            blocks.append("\n".join(current))
            current = [line]
        elif _is_opportunity_heading(line):
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        first_line = block.split("\n", 1)[0].strip()
        title_match = re.match(
            r"^(?:#{1,3}\s*)?(?:\*\*)?(?:Opportunity\s*)?(\d+)[.:)\s-]+(.*)$",
            first_line,
            re.IGNORECASE,
        )
        title = ""
        if title_match:
            title = _clean_markdown(title_match.group(2)).strip().rstrip("*").lstrip(",;:-").strip()

        # Reject anything that still looks like a stray fragment rather
        # than a clean title (too long, empty, or accidentally starts
        # mid-field like "Pain: ...").
        if not title or len(title) > 80 or re.match(r"^(pain|solution|impact)\b", title, re.I):
            title = ""

        pain = _extract_field(block, "Pain Point")
        solution = _extract_field(block, "Proposed Solution")
        impact = _extract_field(block, "Business Impact")

        if pain or solution or impact:
            opportunities.append({
                "title": title or f"Opportunity {len(opportunities) + 1}",
                "pain_point": pain,
                "solution": solution,
                "impact": impact,
                "summary": "",
            })
        elif re.match(r"^\d+\.", block.strip()):
            opportunities.append({
                "title": f"Opportunity {len(opportunities) + 1}",
                "pain_point": "",
                "solution": "",
                "impact": "",
                "summary": _clean_markdown(block),
            })

    if not opportunities:
        for line in section_text.split("\n"):
            clean = _clean_markdown(line).strip()
            if not clean:
                continue
            if re.match(r"^\d+\.", clean) or clean.startswith(("-", "*", "•")):
                opportunities.append({
                    "title": f"Opportunity {len(opportunities) + 1}",
                    "pain_point": "",
                    "solution": "",
                    "impact": "",
                    "summary": clean.lstrip("-*• ").strip(),
                })

    return opportunities[:3]


def parse_email(section_text: str) -> dict[str, str]:
    text = _clean_markdown(section_text).strip()
    subject = ""
    body = text

    subject_match = re.search(r"subject\s*:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if subject_match:
        subject = subject_match.group(1).strip()
        body = text[subject_match.end():].strip()

    return {"subject": subject, "body": body, "full": text}


def structure_results(raw_output: str) -> dict[str, Any]:
    if not raw_output or not raw_output.strip():
        return {
            "overview": "",
            "tech_stack": [],
            "decision_makers": [],
            "opportunities": [],
            "email": "",
            "email_subject": "",
        }

    sections = parse_sections(raw_output)
    email_data = parse_email(sections["email"])

    return {
        "overview": _clean_markdown(sections["overview"]).strip(),
        "tech_stack": parse_tech_stack(sections["tech_stack"]),
        "decision_makers": parse_decision_makers(sections["decision_makers"]),
        "opportunities": parse_opportunities(sections["opportunities"]),
        "email": email_data["full"],
        "email_subject": email_data["subject"],
    }


def validate_structured_results(structured: dict[str, Any]) -> None:
    """Raise if the pipeline produced essentially empty output."""
    has_content = any([
        structured.get("overview"),
        structured.get("tech_stack"),
        structured.get("decision_makers"),
        structured.get("opportunities"),
        structured.get("email"),
    ])
    if not has_content:
        from utils.errors import EmptyResultError
        raise EmptyResultError()