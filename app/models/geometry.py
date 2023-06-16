
from __future__ import annotations

from typing import SupportsIndex

from pydantic import NonNegativeFloat, validator

from app.config.logging import LoggerIndexError, LoggerValueError, get_logger
from app.models.patched import PatchedBaseModel

logger = get_logger(__name__)

point_like = tuple[float, float]
rect_like = (
    tuple[float, float, float, float]
)


class BaseRect(PatchedBaseModel):
    __root__: rect_like

    @property
    def x0(self):
        return self.__root__[0]

    @x0.setter
    def x0(self, value: NonNegativeFloat):
        x0, y0, x1, y1 = self.__root__
        if not value <= x1:
            raise LoggerValueError(logger, 'value should be <= x1.')
        self.__root__ = (value, y0, x1, y1)

    @property
    def y0(self):
        return self.__root__[1]

    @y0.setter
    def y0(self, value: NonNegativeFloat):
        x0, y0, x1, y1 = self.__root__
        if not value <= y1:
            raise LoggerValueError(logger, 'value should be <= y1.')
        self.__root__ = (x0, value, x1, y1)

    @property
    def x1(self):
        return self.__root__[2]

    @x1.setter
    def x1(self, value: NonNegativeFloat):
        x0, y0, x1, y1 = self.__root__
        if not value >= x0:
            raise LoggerValueError(logger, 'value should be >= x0.')
        self.__root__ = (x0, y0, value, y1)

    @property
    def y1(self):
        return self.__root__[3]

    @y1.setter
    def y1(self, value: NonNegativeFloat):
        x0, y0, x1, y1 = self.__root__
        if not value >= y0:
            raise LoggerValueError(logger, 'value should be >= y0.')
        self.__root__ = (x0, y0, x1, value)

    def to_bbox(self) -> rect_like:
        return (self.x0, self.y0, self.x1, self.y1)

    def __getitem__(self, idx: SupportsIndex) -> float:
        idx = int(idx)
        if not 0 <= idx <= 3:
            raise LoggerIndexError(logger, 'idx should be in [0, 1, 2, 3].')
        return {0: self.x0, 1: self.y0, 2: self.x1, 3: self.y1}[idx]

    def __setitem__(self, idx: SupportsIndex, value: float) -> None:
        idx = int(idx)
        if idx == 0:
            self.x0 = value
        elif idx == 1:
            self.y0 = value
        elif idx == 2:
            self.x1 = value
        elif idx == 3:
            self.y1 = value
        else:
            raise LoggerIndexError(logger, 'idx should be in [0, 1, 2, 3].')

    @property
    def width(self) -> float:
        return (self.x1 - self.x0)

    @property
    def height(self) -> float:
        return (self.y1 - self.y0)

    @property
    def area(self) -> float:
        return (self.width * self.height)

    def add_slack(self, rel_slack: float = 0.) -> None:
        width, height = self.width, self.height
        self.x0 = self.x0 - rel_slack * width
        self.y0 = self.y0 - rel_slack * height
        self.x1 = self.x1 + rel_slack * width
        self.y1 = self.y1 + rel_slack * height

    def is_voverlap(self, rect: BaseRect) -> bool:
        return (self.y0 <= rect.y1 and rect.y0 <= self.y1)

    def vdistance(self, rect: BaseRect) -> float:
        if self.is_voverlap(rect):
            return 0

        return min(abs(self.y0 - rect.y1), abs(self.y1 - rect.y0))

    def relative_vdistance(self, rect: BaseRect) -> float:
        """
        Return relative vertical distance of :self and :rect
        (relative to the sum of vdist and the smallest rect height).
        """
        vdist = self.vdistance(rect)
        rel_vdist = vdist / (vdist + min(self.height, rect.height))
        assert 0. <= rel_vdist <= 1., f'rel_vdist: {rel_vdist}.'

        return rel_vdist

    def relative_voverlap(self, rect: BaseRect) -> float:
        """
        Return relative vertical overlap of :self and :rect
        (relative to the smallest rect height). Full vertical overlap returns 1.
        """
        voverlap = max(min(self.y1, rect.y1) - max(self.y0, rect.y0), 0)
        rel_voverlap = voverlap / min(self.height, rect.height)
        assert 0. <= rel_voverlap <= 1., f'rel_voverlap: {rel_voverlap}.'

        return rel_voverlap

    def is_hoverlap(self, rect: BaseRect) -> bool:
        return (self.x0 <= rect.x1 and rect.x0 <= self.x1)

    def hdistance(self, rect: BaseRect) -> float:
        if self.is_hoverlap(rect):
            return 0

        return min(abs(rect.x0 - self.x1), abs(self.x0 - rect.x1))

    def relative_hdistance_page_width(self, rect: BaseRect, page_width: float):
        """
        Return the relative horizontal distance of :self and :rect
        (relative to :page_width).
        """
        hdist = self.hdistance(rect)
        rel_hdist = hdist / page_width
        assert 0. <= rel_hdist <= 1., f'rel_hdist_page_width: {rel_hdist}.'

        return rel_hdist

    def relative_hoverlap(self, rect: Rect) -> float:
        """
        Return relative horizontal overlap of :self and :rect
        (relative to the smallest rect width). Full horizontal overlap, returns 1.
        """
        hoverlap = max(min(self.x1, rect.x1) - max(self.x0, rect.x0), 0)
        rel_hoverlap = hoverlap / min(self.width, rect.width)
        assert 0. <= rel_hoverlap <= 1., f'rel_hoverlap: {rel_hoverlap}.'

        return rel_hoverlap

    def relative_ladvance(self, rect: Rect) -> float:
        """
        Return relative horizontal left advance of :self to :rect
        (relative to the width of the union of :self and :rect).
        Negative if self.x0 < rect.x0.
        """
        rjoin = self.copy()
        rjoin.include(rect)

        return ((self.x0 - rect.x0) / rjoin.width)

    def contains(self, rect: BaseRect) -> bool:
        """Return True if self contains :rect."""
        if ((self.x0 <= rect.x0 and self.y0 <= rect.y0) and
                (self.x1 >= rect.x1 and self.y1 >= rect.y1)):
            return True

        return False

    def include(self, rect: BaseRect) -> None:
        """
        Extend self with :rect.

        Can also include lines (zero-width or zero-height).
        """
        self.x0 = min(self.x0, rect.x0)
        self.y0 = min(self.y0, rect.y0)
        self.x1 = max(self.x1, rect.x1)
        self.y1 = max(self.y1, rect.y1)

    def intersects(self, rect: BaseRect) -> bool:
        """Return True if self intersects with :rect."""
        return (self.is_voverlap(rect) and self.is_hoverlap(rect))

    def intersection_over_union(self, rect: BaseRect) -> float:
        if not self.intersects(rect):
            return 0

        rjoin = self.copy()
        rjoin.include(rect)
        intersection_area = (
            (min(self.x1, rect.x1) - max(self.x0, rect.x0)) *
            (min(self.y1, rect.y1) - max(self.y0, rect.y0))
        )
        iou = intersection_area / rjoin.area
        assert 0. <= iou <= 1., f'iou: {iou}.'

        return iou

    def is_after(self, rect: BaseRect) -> bool:
        """Returns true if :self is after :rect in layout order."""
        return (
            (self.y0 > rect.y0) or (self.y0 == rect.y0 and self.x0 >= rect.x0)
        )

    @staticmethod
    def get_bbox_area(bbox: rect_like):
        return (abs(bbox[2] - bbox[0]) * abs(bbox[3] - bbox[1]))

    def __repr__(self) -> str:
        return (f'{self.__class__.__name__}' +
                '[{:.3f}, {:.3f}, {:.3f}, {:.3f}]'
                .format(self.x0, self.y0, self.x1, self.y1))


class Rect(BaseRect):

    @validator('__root__', pre=True)
    def verify_bbox(cls, value: tuple[float, float, float, float]) -> rect_like:
        x0, y0, x1, y1 = value
        x0 = x0 if x0 >= 0. else 0.  # clips x0 to 0 if x0 < 0
        y0 = y0 if y0 >= 0. else 0.  # clips y0 to 0 if y0 < 0
        if x1 < x0 or y1 < y0:
            # empty rectangle
            x1 = x0
            y1 = y0

        return (x0, y0, x1, y1)


class UserRect(BaseRect):

    @validator('__root__', pre=True)
    def verify_bbox(cls, value: tuple[float, float, float, float]) -> rect_like:
        if value[0] < 0:
            raise LoggerValueError(logger, 'bbox[0] should be >= 0.')
        if value[1] < 0:
            raise LoggerValueError(logger, 'bbox[1] should be >= 0.')
        if value[2] < value[0]:
            raise LoggerValueError(logger, 'bbox[2] should be >= bbox[0].')
        if value[3] < value[1]:
            raise LoggerValueError(logger, 'bbox[3] should be >= bbox[1].')

        return value
