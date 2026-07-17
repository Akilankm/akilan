from akilan import BBox


def test_bbox_relations() -> None:
    left = BBox(0, 0, 10, 10)
    right = BBox(5, 5, 15, 15)

    assert left.area == 100
    assert left.intersects(right)
    assert left.intersection(right) == BBox(5, 5, 10, 10)
    assert left.overlap_ratio(right) == 0.25
    assert left.normalized(BBox(0, 0, 100, 100)) == {
        "x0": 0.0,
        "y0": 0.0,
        "x1": 0.1,
        "y1": 0.1,
    }
