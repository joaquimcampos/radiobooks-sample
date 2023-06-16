from app.models.geometry import Rect, point_like


def get_sorting_tuple(rect: Rect) -> point_like:
    return (rect.y0, rect.x0)
