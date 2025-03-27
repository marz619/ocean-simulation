from collections import Counter
from collections import defaultdict
from enum import Enum
from enum import auto
from io import StringIO
from itertools import product
from random import Random
from typing import Any
from typing import Callable
from typing import Iterable


class Occupant(Enum):
    EMPTY = auto()
    SHARK = auto()
    FISH = auto()


class Cell:
    def __init__(self, occupant: Occupant, feeding: int = 0):
        self.occupant = occupant
        self.feeding = feeding

    def __str__(self) -> str:
        return f"Cell[{str(self.occupant)}, {str(self.feeding)}]"

    def __repr__(self) -> str:
        return f"Cell({str(self.occupant)}, feeding={repr(self.feeding)})"


EMPTY_CELL = Cell(Occupant.EMPTY)


class OceanDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self, key: Any, default: Any = None) -> Any:
        super().get(key, default or EMPTY_CELL)

    def __getitem__(self, key: Any) -> Any:
        if key not in self:
            return EMPTY_CELL
        return super().__getitem__(key)


class Ocean:
    def __init__(self, width: int, height: int, _buffer: StringIO = None):
        self._width: int = width
        self._height: int = height
        self._ocean: OceanDict = OceanDict()
        self._rand = Random()
        # text buffer
        self._buffer = _buffer or StringIO()
        self.__str = None

    def __len__(self) -> int:
        return len(self._ocean)

    def __setitem__(self, coords: tuple[int, int], cell: Cell) -> None:
        self._ocean[self._coords(*coords)] = cell

    def __getitem__(self, coords: tuple[int, int]) -> Cell:
        return self._ocean[self._coords(*coords)]

    def __str__(self) -> str:
        if self.__str:
            return self.__str

        self._buffer.seek(0)

        for y in range(self.height):
            self._buffer.write(" ")
            for x in range(self.width):
                # fetch the occupant
                match self[(x, y)].occupant:
                    case Occupant.SHARK:
                        self._buffer.write("🦈")
                    case Occupant.FISH:
                        self._buffer.write("🐠")
                    case _:
                        self._buffer.write("📘")
            self._buffer.write("\n")

        self.__str = self._buffer.getvalue()
        return self.__str

    def __hash__(self) -> str:
        return hash(self.__str__())

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

    def _coords(self, x: int, y: int) -> tuple[int, int]:
        return x % self.width, y % self.height

    def _add(self, x: int, y: int, occupant: Occupant, feeding: int = 0) -> None:
        x, y = self._coords(x, y)
        if self._ocean[(x, y)] == EMPTY_CELL:
            self._ocean[(x, y)] = Cell(occupant, feeding)

    def add_fish(self, x: int, y: int) -> None:
        self._add(x, y, Occupant.FISH)

    def add_shark(self, x: int, y: int, feeding: int = 0) -> None:
        self._add(x, y, Occupant.SHARK, feeding)

    def cell_contents(self, x: int, y: int) -> Occupant:
        return self[(x, y)].occupant

    @property
    def is_dead(self) -> bool:
        # return len(self) == 0
        return False

    def shark_feeding(self, x: int, y: int) -> int:
        pass

    def time_step(self, starve_time: int) -> "Ocean":
        # new_ocean = Ocean(self.width, self.height, self._buffer)  # share a buffer???
        new_ocean = Ocean(self.width, self.height)

        for x, y in product(range(self.width), range(self.height)):
            # # life finds a way
            # cell = self._spontaneous_life_emergence(x, y, starve_time)
            # if cell:
            #     new_ocean._ocean[(x, y)] = cell
            #     continue

            # apply rules
            cell = self._apply_rules(x, y, starve_time)
            if cell is not EMPTY_CELL:
                new_ocean._ocean[(x, y)] = cell

        return new_ocean

    # def _spontaneous_life_emergence(self, x: int, y: int, starve_time: int) -> Cell:
    #     if self._ocean[(x, y)] is not EMPTY_CELL:
    #         return EMPTY_CELL
    #     # 2% change
    #     if self.random() <= 0.02:
    #         return EMPTY_CELL
    #     # 20:80 SHARK:FISH
    #     if self.randint() < 2:
    #         return Cell(Occupant.SHARK, starve_time)
    #     return Cell(Occupant.FISH)

    def _apply_rules(self, x: int, y: int, starve_time: int) -> Cell:
        cell = self._ocean[(x, y)]  # current cell

        counts = Ocean.counts(self._neighbours(x, y))
        fishes, sharks = (
            counts.get(Occupant.FISH, 0),
            counts.get(Occupant.SHARK, 0),
        )

        if cell.occupant == Occupant.SHARK:
            feeding = starve_time if fishes else cell.feeding - 1
            if feeding:
                return Cell(Occupant.SHARK, feeding)

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
            self[(x + i, y + j)]
            for i in range(-1, 1 + 1)
            for j in range(-1, 1 + 1)
            if (i, j) != (0, 0)
        ]

    @staticmethod
    def counts(cells: Iterable[Cell]) -> dict[Occupant, int]:
        return Counter(c.occupant for c in cells)
