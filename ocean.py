from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from enum import auto
from io import StringIO
from itertools import product
from typing import assert_never
from random import Random
from typing import Any
from typing import Iterable


class Occupant(Enum):
    EMPTY = auto()
    SHARK = auto()
    FISH = auto()

    def __repr__(self) -> str:
        match self:
            case Occupant.EMPTY:
                return " " 
            case Occupant.FISH:
                return "F"
            case Occupant.SHARK:
                return "S"
            case _:
                assert_never(self)

    def __str__(self) -> str:
        match self:
            case Occupant.EMPTY:
                return "📘" 
            case Occupant.FISH:
                return "🐠"
            case Occupant.SHARK:
                return "🦈"
            case _:
                assert_never(self)


@dataclass(frozen=True, slots=True)
class Cell:
    occupant: Occupant
    feeding: int = 0

    def __post_init__(self):
        if self.feeding < 0:
            raise ValueError("feeding cannot be negative")

    def with_feeding(self, feeding: int) -> Cell:
        return Cell(self.occupant, feeding)


# useful constants
EMPTY_CELL = Cell(Occupant.EMPTY)

# type aliases
Coordinates: TypeAlias = tuple[int, int]


class OceanDict(dict[Coordinates, Cell]):
    """ Partial dict implementation that holds the Ocean """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __missing__(self, key: Coordinates) -> Cell:
        return EMPTY_CELL


class Ocean:
    def __init__(self, width: int, height: int, _buffer: StringIO | None = None):
        self._width: int = width
        self._height: int = height
        self._ocean: OceanDict = OceanDict()
        self._rand = Random()
        # text buffer
        self._buffer = _buffer or StringIO()
        self._str = None
        self._hash = None

    def __len__(self) -> int:
        return len(self._ocean)

    def __setitem__(self, coords: tuple[int, int], cell: Cell) -> None:
        self._ocean[self._wrap_coords(*coords)] = cell
        self._hash = None

    def __getitem__(self, coords: tuple[int, int]) -> Cell:
        return self._ocean[self._wrap_coords(*coords)]

    def __str__(self) -> str:
        if self._str:
            return self._str

        self._buffer.seek(0)

        for y in range(self.height):
            self._buffer.write(" ")
            for x in range(self.width):
                self._buffer.write(str(self[(x, y)].occupant))
            self._buffer.write("\n")

        self._str = self._buffer.getvalue()
        return self._str

    def __hash__(self) -> int:
        if not self._hash:
            occupants = tuple(
                self[(x, y)].occupant
                for x in range(self.width)
                for y in range(self.height)
            )
            self._hash = hash(occupants)
        return self._hash

    def random(self) -> float:
        return self._rand.random()

    def randint(self, lo: int, hi: int) -> int:
        return self._rand.randint(lo, hi)

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def _wrap_coords(self, x: int, y: int) -> tuple[int, int]:
        return x % self.width, y % self.height

    def _add(self, x: int, y: int, occupant: Occupant, feeding: int = 0) -> None:
        x, y = self._wrap_coords(x, y)
        self._ocean[(x, y)] = Cell(occupant, feeding)

    def add_fish(self, x: int, y: int) -> None:
        self._add(x, y, Occupant.FISH)

    def add_shark(self, x: int, y: int, feeding: int = 0) -> None:
        self._add(x, y, Occupant.SHARK, feeding)

    @property
    def is_dead(self) -> bool:
        return len(self) == 0

    def shark_feeding(self, x: int, y: int) -> int:
        if (cell := self[(x, y)]).occupant == Occupant.SHARK:
            return cell.feeding
        return 0
    
    def cell_contents(self, x: int, y: int) -> Occupant:
        return self[(x, y)].occupant

    def time_step(self, starve_time: int) -> "Ocean":
        # new_ocean = Ocean(self.width, self.height, self._buffer)  # share a buffer???
        new_ocean = Ocean(self.width, self.height)

        for x, y in product(range(self.width), range(self.height)):
            # life finds a way
            if (cell := self[(x, y)]) == EMPTY_CELL:
                life = self._spontaneous_life_emergence(x, y, starve_time)
                if life is not EMPTY_CELL:
                    new_ocean._ocean[(x, y)] = life
                    continue

            # apply rules
            cell = self._apply_rules(x, y, starve_time)
            if cell is not EMPTY_CELL:
                new_ocean._ocean[(x, y)] = cell

        return new_ocean

    def _spontaneous_life_emergence(self, x: int, y: int, starve_time: int) -> Cell:
        # 2% chance of spotnaeous life
        if self.random() <= 0.999:
            return EMPTY_CELL
        # 20:80 SHARK:FISH
        if self.random() <= 0.2:
            return Cell(Occupant.SHARK, starve_time)
        return Cell(Occupant.FISH)

    def _apply_rules(self, x: int, y: int, starve_time: int) -> Cell:
        cell = self._ocean[(x, y)]  # current cell

        counts = Ocean.counts(self._neighbours(x, y))
        fishes, sharks = (
            counts.get(Occupant.FISH, 0),
            counts.get(Occupant.SHARK, 0),
        )

        if cell.occupant == Occupant.SHARK:
            feeding = starve_time if fishes else cell.feeding - 1
            if feeding > 0:
                return Cell(Occupant.SHARK, feeding)
            return EMPTY_CELL

        if cell.occupant == Occupant.FISH:
            if sharks > 1:
                return Cell(Occupant.SHARK, starve_time)
            return Cell(Occupant.FISH)

        if sharks <= 1 and fishes > 1:
            return Cell(Occupant.FISH)

        if sharks > 1 and fishes > 1:
            return Cell(Occupant.SHARK, starve_time)

        return EMPTY_CELL

    def _neighbours(self, x: int, y: int) -> list[Cell]:
        return [
            # (x+i, y+j, self[(x + i, y + j)])
            self[(x + i, y + j)]
            for i in range(-1, 1 + 1)
            for j in range(-1, 1 + 1)
            if (i, j) != (0, 0)
        ]

    @staticmethod
    def counts(cells: Iterable[Cell]) -> Counter[Occupant, int]:
        return Counter(c.occupant for c in cells)
