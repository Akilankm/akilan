"""Geometry primitives and deterministic spatial relations."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Iterable, Sequence

import pymupdf


@dataclass(frozen=True, slots=True)
class BBox:
    """Immutable axis-aligned rectangle in PDF points."""

    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_value(cls, value: Sequence[float] | pymupdf.Rect) -> "BBox":
        rect = pymupdf.Rect(value)
        return cls(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x0 + self.x1) / 2.0, (self.y0 + self.y1) / 2.0)

    def to_list(self, precision: int = 4) -> list[float]:
        return [round(v, precision) for v in (self.x0, self.y0, self.x1, self.y1)]

    def to_dict(self, precision: int = 4) -> dict[str, float]:
        return {
            "x0": round(self.x0, precision),
            "y0": round(self.y0, precision),
            "x1": round(self.x1, precision),
            "y1": round(self.y1, precision),
            "width": round(self.width, precision),
            "height": round(self.height, precision),
        }

    def normalized(self, page: "BBox", precision: int = 6) -> dict[str, float]:
        width = page.width or 1.0
        height = page.height or 1.0
        return {
            "x0": round((self.x0 - page.x0) / width, precision),
            "y0": round((self.y0 - page.y0) / height, precision),
            "x1": round((self.x1 - page.x0) / width, precision),
            "y1": round((self.y1 - page.y0) / height, precision),
        }

    def intersects(self, other: "BBox") -> bool:
        return not (
            self.x1 <= other.x0
            or other.x1 <= self.x0
            or self.y1 <= other.y0
            or other.y1 <= self.y0
        )

    def intersection(self, other: "BBox") -> "BBox | None":
        if not self.intersects(other):
            return None
        return BBox(
            max(self.x0, other.x0),
            max(self.y0, other.y0),
            min(self.x1, other.x1),
            min(self.y1, other.y1),
        )

    def overlap_ratio(self, other: "BBox", denominator: str = "self") -> float:
        intersection = self.intersection(other)
        if intersection is None:
            return 0.0
        if denominator == "self":
            base = self.area
        elif denominator == "other":
            base = other.area
        elif denominator == "min":
            base = min(self.area, other.area)
        elif denominator == "union":
            base = self.area + other.area - intersection.area
        else:
            raise ValueError(f"Unsupported denominator: {denominator}")
        return intersection.area / base if base > 0 else 0.0

    def contains(self, other: "BBox", tolerance: float = 0.0) -> bool:
        return (
            self.x0 - tolerance <= other.x0
            and self.y0 - tolerance <= other.y0
            and self.x1 + tolerance >= other.x1
            and self.y1 + tolerance >= other.y1
        )

    def distance_to(self, other: "BBox") -> float:
        ax, ay = self.center
        bx, by = other.center
        return hypot(ax - bx, ay - by)

    def expand(self, margin: float) -> "BBox":
        return BBox(self.x0 - margin, self.y0 - margin, self.x1 + margin, self.y1 + margin)


def union_bbox(boxes: Iterable[BBox]) -> BBox | None:
    values = list(boxes)
    if not values:
        return None
    return BBox(
        min(box.x0 for box in values),
        min(box.y0 for box in values),
        max(box.x1 for box in values),
        max(box.y1 for box in values),
    )
