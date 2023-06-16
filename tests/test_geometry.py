import pytest
from numpy.testing import assert_allclose
from pydantic import ValidationError
from app.models.geometry import rect_like, Rect, UserRect


@pytest.fixture
def sample_bbox() -> rect_like:
    return (1, 2, 3, 5)


@pytest.mark.parametrize(
    "bbox, parsed_bbox, valid", [
        ((1., 2., 1.5, 2.5), (1., 2., 1.5, 2.5), True),
        ((1., -2., 3, 4), (1., 0., 3, 4), False),
        ((2., 3., 1., 4.), (2., 3., 2., 3.), False),
        ((3., 2., 4., 1.), (3., 2., 3., 2.), False)
    ]
)
def test_rect_init(
    bbox: tuple[float, float, float, float],
    parsed_bbox: rect_like,
    valid: bool
):
    assert_allclose(Rect.parse_obj(bbox).to_bbox(), parsed_bbox)
    try:
        _ = UserRect.parse_obj(bbox)
    except ValidationError:
        assert valid is False
        return

    assert valid is True


def test_rect_get_set(sample_bbox: rect_like):
    bbox = sample_bbox
    rect = UserRect.parse_obj(bbox)

    assert rect.x0 == rect[0] == bbox[0]
    assert rect.y0 == rect[1] == bbox[1]
    assert rect.x1 == rect[2] == bbox[2]
    assert rect.y1 == rect[3] == bbox[3]

    with pytest.raises(IndexError):
        _ = rect[4]

    rect.x0 = 2
    assert_allclose(rect.to_bbox(), (2, bbox[1], bbox[2], bbox[3]))
    rect.y0 = 3
    assert_allclose(rect.to_bbox(), (2, 3, bbox[2], bbox[3]))
    rect.x1 = 4
    assert_allclose(rect.to_bbox(), (2, 3, 4, bbox[3]))
    rect.y1 = 5
    assert_allclose(rect.to_bbox(), (2, 3, 4, 5))

    with pytest.raises(ValueError):
        rect[0] = 5

    with pytest.raises(ValueError):
        rect[1] = 6

    with pytest.raises(ValueError):
        rect[2] = 1

    with pytest.raises(ValueError):
        rect[3] = 2

    with pytest.raises(IndexError):
        rect[-1] = 1


@pytest.mark.parametrize(
    "bbox1, bbox2, overlap, vdist, rel_vdist", [
        ((1, 2, 3, 4), (4, 3.5, 5, 6), True, 0, 0),
        ((1, 2, 3, 4), (4, 4.5, 5, 6), False, 0.5, 0.25)
    ]
)
def test_rect_voverlap_vdist(
    bbox1: rect_like,
    bbox2: rect_like,
    overlap: bool,
    vdist: float,
    rel_vdist: float
):
    r1 = UserRect.parse_obj(bbox1)
    r2 = UserRect.parse_obj(bbox2)

    assert r1.is_voverlap(r2) == overlap
    assert_allclose(r1.vdistance(r2), vdist)
    assert_allclose(r1.relative_vdistance(r2), rel_vdist)


@pytest.mark.parametrize(
    "bbox1, bbox2, intersects", [
        ((1, 2, 3, 4), (2.9, 3.9, 3.5, 4.5), True),
        ((1, 2, 3, 4), (3.1, 3.9, 3.5, 4.5), False),
        ((1, 2, 3, 4), (2.9, 4.1, 3.5, 4.5), False),
    ]
)
def test_rect_intersects(
    bbox1: rect_like,
    bbox2: rect_like,
    intersects: bool
):
    r1 = UserRect.parse_obj(bbox1)
    r2 = UserRect.parse_obj(bbox2)
    assert r1.intersects(r2) == intersects


@pytest.mark.parametrize(
    "bbox1, bbox2, union_bbox", [
        ((1., 2., 3., 4.), (2.6, 3.5, 3.5, 4.5), (1., 2., 3.5, 4.5)),
    ]
)
def test_shallow_rect_copy(
    bbox1: rect_like,
    bbox2: rect_like,
    union_bbox: rect_like
):
    r1 = UserRect.parse_obj(bbox1)
    r2 = UserRect.parse_obj(bbox2)
    rjoin = r1.copy()
    rjoin.include(r2)

    assert_allclose(r1.to_bbox(), bbox1)
    assert_allclose(r2.to_bbox(), bbox2)
    assert_allclose(rjoin.to_bbox(), union_bbox)
