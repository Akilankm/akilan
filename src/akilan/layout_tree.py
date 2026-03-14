from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import (
    AbsolutePositionCoarse,
    BBox,
    DynamicPosition,
    GroupChunk,
    NormalizedPosition,
    NormalizedSize,
    PageChunk,
    RelativePosition,
)


@dataclass
class SplitDecision:
    axis: str  # "vertical" means left/right split, "horizontal" means top/bottom split
    cut_start: float
    cut_end: float
    score: float


class LayoutTreeBuilder:
    """
    Recursive region partitioning using whitespace splits.
    Only outputs:
    - text
    - image
    - table
    - group(horizontal)
    - group(vertical)
    """

    def __init__(self, page_number: int, page_width: float, page_height: float):
        self.page_number = page_number
        self.page_width = page_width
        self.page_height = page_height

    # ----------------------------
    # Utilities
    # ----------------------------

    def _merge_bboxes(self, boxes: list[BBox]) -> BBox:
        if not boxes:
            raise ValueError("boxes must not be empty")
        merged = boxes[0]
        for box in boxes[1:]:
            merged = merged.union(box)
        return merged

    def _group_bbox(self, chunks: list[PageChunk]) -> BBox:
        return self._merge_bboxes([chunk.bbox for chunk in chunks])

    def _sort_reading_order(self, chunks: list[PageChunk]) -> list[PageChunk]:
        return sorted(chunks, key=lambda c: (c.bbox.y0, c.bbox.x0))

    def _coarse_position(self, bbox: BBox) -> AbsolutePositionCoarse:
        if bbox.cx < self.page_width * 0.33:
            x_bucket = "LEFT"
        elif bbox.cx < self.page_width * 0.66:
            x_bucket = "CENTER"
        else:
            x_bucket = "RIGHT"

        if bbox.cy < self.page_height * 0.33:
            y_bucket = "TOP"
        elif bbox.cy < self.page_height * 0.66:
            y_bucket = "MIDDLE"
        else:
            y_bucket = "BOTTOM"

        return f"{y_bucket}_{x_bucket}"  # type: ignore[return-value]

    def _normalized_position(self, bbox: BBox) -> NormalizedPosition:
        return NormalizedPosition(
            x=0.0 if self.page_width <= 0 else bbox.cx / self.page_width,
            y=0.0 if self.page_height <= 0 else bbox.cy / self.page_height,
        )

    def _normalized_size(self, bbox: BBox) -> NormalizedSize:
        return NormalizedSize(
            w=0.0 if self.page_width <= 0 else bbox.width / self.page_width,
            h=0.0 if self.page_height <= 0 else bbox.height / self.page_height,
        )

    def _relative_position(self, idx: int, count: int, layout: str) -> RelativePosition:
        if layout == "horizontal":
            if count <= 1:
                return "CENTER"
            if count == 2:
                return "LEFT" if idx == 0 else "RIGHT"
            if idx == 0:
                return "LEFT"
            if idx == count - 1:
                return "RIGHT"
            return "CENTER"

        if count <= 1:
            return "MIDDLE"
        if count == 2:
            return "TOP" if idx == 0 else "BOTTOM"
        if idx == 0:
            return "TOP"
        if idx == count - 1:
            return "BOTTOM"
        return "MIDDLE"

    def _clear_relative_positions_recursive(self, node: PageChunk) -> None:
        node.relative_position = None
        if node.type == "group":
            for child in node.children:
                self._clear_relative_positions_recursive(child)

    def _refresh_geometry_recursive(self, node: PageChunk) -> None:
        node.position_normalized = self._normalized_position(node.bbox)
        node.size_normalized = self._normalized_size(node.bbox)
        node.absolute_position_coarse = self._coarse_position(node.bbox)
        if node.type == "group":
            for child in node.children:
                self._refresh_geometry_recursive(child)

    def _assign_indexes_recursive(self, chunks: list[PageChunk]) -> None:
        counter = 0

        def walk(node: PageChunk):
            nonlocal counter
            node.chunk_index = counter
            counter += 1
            if node.type == "group":
                for child in node.children:
                    walk(child)

        for chunk in chunks:
            walk(chunk)

    def _chunks_in_region(self, chunks: list[PageChunk], region: BBox) -> list[PageChunk]:
        selected: list[PageChunk] = []

        for chunk in chunks:
            inter = chunk.bbox.intersection(region)
            if not inter:
                continue

            overlap_ratio = inter.area / max(chunk.bbox.area, 1e-6)
            if overlap_ratio >= 0.80:
                selected.append(chunk)

        return selected

    # ----------------------------
    # Projection analysis
    # ----------------------------

    def _occupied_intervals(self, chunks: list[PageChunk], region: BBox, axis: str) -> list[tuple[float, float]]:
        intervals = []

        for chunk in chunks:
            if axis == "x":
                start = max(region.x0, chunk.bbox.x0)
                end = min(region.x1, chunk.bbox.x1)
            else:
                start = max(region.y0, chunk.bbox.y0)
                end = min(region.y1, chunk.bbox.y1)

            if end > start:
                intervals.append((start, end))

        if not intervals:
            return []

        intervals.sort(key=lambda x: x[0])

        merged = [intervals[0]]
        for start, end in intervals[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))

        return merged

    def _find_gaps(self, chunks: list[PageChunk], region: BBox, axis: str) -> list[tuple[float, float, float]]:
        occupied = self._occupied_intervals(chunks, region, axis)
        if not occupied:
            return []

        region_start = region.x0 if axis == "x" else region.y0
        region_end = region.x1 if axis == "x" else region.y1

        gaps: list[tuple[float, float, float]] = []
        prev_end = region_start

        for start, end in occupied:
            if start > prev_end:
                gaps.append((prev_end, start, start - prev_end))
            prev_end = max(prev_end, end)

        if prev_end < region_end:
            gaps.append((prev_end, region_end, region_end - prev_end))

        return gaps

    def _split_chunks_by_axis(
        self,
        chunks: list[PageChunk],
        axis: str,
        cut_mid: float,
    ) -> tuple[list[PageChunk], list[PageChunk]]:
        first: list[PageChunk] = []
        second: list[PageChunk] = []

        if axis == "vertical":
            for chunk in chunks:
                if chunk.bbox.cx <= cut_mid:
                    first.append(chunk)
                else:
                    second.append(chunk)
        else:
            for chunk in chunks:
                if chunk.bbox.cy <= cut_mid:
                    first.append(chunk)
                else:
                    second.append(chunk)

        return first, second

    def _evaluate_split(
        self,
        chunks: list[PageChunk],
        region: BBox,
        axis: str,
    ) -> Optional[SplitDecision]:
        gaps = self._find_gaps(chunks, region, axis="x" if axis == "vertical" else "y")
        if not gaps:
            return None

        extent = region.width if axis == "vertical" else region.height
        if extent <= 0:
            return None

        best: Optional[SplitDecision] = None

        for start, end, size in gaps:
            relative_gap = size / extent
            min_gap_ratio = 0.04 if axis == "vertical" else 0.03

            if relative_gap < min_gap_ratio:
                continue

            cut_mid = (start + end) / 2.0
            first, second = self._split_chunks_by_axis(chunks, axis, cut_mid)

            if not first or not second:
                continue

            balance = min(len(first), len(second)) / max(len(first), len(second))
            score = (relative_gap * 0.7) + (balance * 0.3)

            decision = SplitDecision(
                axis=axis,
                cut_start=start,
                cut_end=end,
                score=score,
            )

            if best is None or decision.score > best.score:
                best = decision

        return best

    def _choose_best_split(
        self,
        chunks: list[PageChunk],
        region: BBox,
    ) -> Optional[SplitDecision]:
        vertical = self._evaluate_split(chunks, region, axis="vertical")
        horizontal = self._evaluate_split(chunks, region, axis="horizontal")

        if vertical and horizontal:
            return vertical if vertical.score >= horizontal.score else horizontal
        return vertical or horizontal

    # ----------------------------
    # Dynamic zones
    # ----------------------------

    def _cluster_axis_values(self, values: list[float], min_gap: float = 0.08) -> list[list[float]]:
        """
        Gap-based clustering on normalized centers.
        """
        if not values:
            return []

        values = sorted(values)
        clusters: list[list[float]] = [[values[0]]]

        for value in values[1:]:
            if value - clusters[-1][-1] >= min_gap:
                clusters.append([value])
            else:
                clusters[-1].append(value)

        return clusters

    def _build_zone_boundaries(self, values: list[float], axis: str) -> list[tuple[float, float]]:
        clusters = self._cluster_axis_values(
            values,
            min_gap=0.08 if axis == "x" else 0.07,
        )
        if not clusters:
            return [(0.0, 1.0)]

        mins = [min(cluster) for cluster in clusters]
        maxs = [max(cluster) for cluster in clusters]

        boundaries: list[tuple[float, float]] = []
        for i in range(len(clusters)):
            if i == 0:
                start = 0.0
            else:
                start = (maxs[i - 1] + mins[i]) / 2.0

            if i == len(clusters) - 1:
                end = 1.0
            else:
                end = (maxs[i] + mins[i + 1]) / 2.0

            boundaries.append((start, end))

        return boundaries

    def _zone_index(self, value: float, boundaries: list[tuple[float, float]]) -> int:
        for idx, (start, end) in enumerate(boundaries):
            if idx == len(boundaries) - 1:
                if start <= value <= end:
                    return idx
            if start <= value < end:
                return idx
        return max(0, len(boundaries) - 1)

    def _assign_dynamic_positions(self, roots: list[PageChunk]) -> None:
        all_nodes: list[PageChunk] = []

        def walk(node: PageChunk):
            all_nodes.append(node)
            if node.type == "group":
                for child in node.children:
                    walk(child)

        for root in roots:
            walk(root)

        x_values = []
        y_values = []

        for node in all_nodes:
            if node.position_normalized is None:
                continue
            x_values.append(node.position_normalized.x)
            y_values.append(node.position_normalized.y)

        if not x_values or not y_values:
            return

        x_boundaries = self._build_zone_boundaries(x_values, axis="x")
        y_boundaries = self._build_zone_boundaries(y_values, axis="y")

        for node in all_nodes:
            if node.position_normalized is None:
                continue

            x_zone = self._zone_index(node.position_normalized.x, x_boundaries)
            y_zone = self._zone_index(node.position_normalized.y, y_boundaries)

            node.absolute_position_dynamic = DynamicPosition(
                x_zone=x_zone,
                x_zone_count=len(x_boundaries),
                y_zone=y_zone,
                y_zone_count=len(y_boundaries),
            )

    # ----------------------------
    # Recursive build
    # ----------------------------

    def _make_group(
        self,
        layout: str,
        children: list[PageChunk],
    ) -> GroupChunk:
        bbox = self._group_bbox(children)
        return GroupChunk(
            chunk_index=-1,
            page_number=self.page_number,
            type="group",
            layout=layout,
            bbox=bbox,
            children=children,
            position_normalized=self._normalized_position(bbox),
            size_normalized=self._normalized_size(bbox),
            absolute_position_coarse=self._coarse_position(bbox),
            absolute_position_dynamic=None,
            relative_position=None,
        )

    def _make_fallback_flow(self, chunks: list[PageChunk]) -> list[PageChunk]:
        chunks = self._sort_reading_order(chunks)
        if len(chunks) <= 1:
            return chunks
        return [self._make_group("vertical", chunks)]

    def _build_region(
        self,
        chunks: list[PageChunk],
        region: BBox,
        depth: int = 0,
    ) -> list[PageChunk]:
        if not chunks:
            return []

        if len(chunks) == 1:
            return chunks

        if depth > 12:
            return self._make_fallback_flow(chunks)

        decision = self._choose_best_split(chunks, region)
        if not decision:
            return self._make_fallback_flow(chunks)

        child_regions: list[BBox] = []

        if decision.axis == "vertical":
            left_region = BBox(region.x0, region.y0, decision.cut_start, region.y1)
            right_region = BBox(decision.cut_end, region.y0, region.x1, region.y1)

            if left_region.width > 1:
                child_regions.append(left_region)
            if right_region.width > 1:
                child_regions.append(right_region)

            layout = "horizontal"
        else:
            top_region = BBox(region.x0, region.y0, region.x1, decision.cut_start)
            bottom_region = BBox(region.x0, decision.cut_end, region.x1, region.y1)

            if top_region.height > 1:
                child_regions.append(top_region)
            if bottom_region.height > 1:
                child_regions.append(bottom_region)

            layout = "vertical"

        built_children: list[PageChunk] = []

        for child_region in child_regions:
            child_chunks = self._chunks_in_region(chunks, child_region)
            if not child_chunks:
                continue

            built = self._build_region(child_chunks, child_region, depth + 1)

            if len(built) == 1:
                built_children.append(built[0])
            elif built:
                built_children.append(self._make_group("vertical", built))

        if len(built_children) <= 1:
            return self._make_fallback_flow(chunks)

        if layout == "horizontal":
            built_children.sort(key=lambda c: c.bbox.x0)
        else:
            built_children.sort(key=lambda c: c.bbox.y0)

        for idx, child in enumerate(built_children):
            child.relative_position = self._relative_position(idx, len(built_children), layout)

        return [self._make_group(layout, built_children)]

    def build(self, chunks: list[PageChunk], page_bbox: BBox) -> list[PageChunk]:
        chunks = self._sort_reading_order(chunks)
        built = self._build_region(chunks, page_bbox, depth=0)

        for node in built:
            self._clear_relative_positions_recursive(node)
            self._refresh_geometry_recursive(node)

        def reassign(node: PageChunk):
            if node.type == "group":
                ordered = sorted(
                    node.children,
                    key=lambda c: c.bbox.x0 if node.layout == "horizontal" else c.bbox.y0,
                )
                for idx, child in enumerate(ordered):
                    child.relative_position = self._relative_position(idx, len(ordered), node.layout)
                    reassign(child)

        for node in built:
            reassign(node)

        self._assign_dynamic_positions(built)
        self._assign_indexes_recursive(built)
        return built
