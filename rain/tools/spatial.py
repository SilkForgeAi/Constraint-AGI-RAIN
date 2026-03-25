"""Embodied perception — spatial reasoning from text descriptions or coordinates.

Reason about layout, relative positions, distances, and spatial relationships
without requiring vision (textual or structured input).
"""

from __future__ import annotations


def spatial_reason(
    description: str,
    query: str,
    engine: object = None,
    max_tokens: int = 350,
) -> str:
    """
    Answer a spatial query given a text description of an environment or layout.
    description: e.g. "Room A is north of Room B. The desk is 2m from the window. The door is on the east wall."
    query: e.g. "Where is the desk relative to the door?" or "What is the distance from A to B?"
    """
    if not description.strip() or not query.strip():
        return "Error: Provide both description and query."

    if engine is None:
        try:
            from rain.core.engine import CoreEngine
            engine = CoreEngine()
        except Exception:
            return "Spatial reasoning: engine not available."

    prompt = f"""Spatial reasoning. Use only the given description. Do not invent facts.

Description:
{description}

Query: {query}

Answer concisely. If the description does not contain enough information, say so."""

    try:
        out = engine.complete(
            [
                {"role": "system", "content": "You reason about spatial relationships from text. Be concise and precise."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        return out.strip()
    except Exception as e:
        return f"Spatial reasoning error: {e}"


def spatial_layout_from_coords(
    points: list[dict],
    query: str,
    engine: object = None,
) -> str:
    """
    Reason about points given as list of dicts with id and x,y(,z) coordinates.
    points: e.g. [{"id": "A", "x": 0, "y": 0}, {"id": "B", "x": 3, "y": 4}]
    query: e.g. "Which point is closest to origin?" or "What is the distance between A and B?"
    """
    if not points or not query.strip():
        return "Error: Provide points and query."

    desc_lines = []
    for p in points:
        pid = p.get("id", "?")
        x, y = p.get("x", 0), p.get("y", 0)
        z = p.get("z")
        if z is not None:
            desc_lines.append(f"{pid}: ({x}, {y}, {z})")
        else:
            desc_lines.append(f"{pid}: ({x}, {y})")
    description = "\n".join(desc_lines)
    return spatial_reason(description, query, engine=engine)
