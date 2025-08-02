from ocean import Ocean, Occupant


def test_add_fish_and_shark():
    ocean = Ocean(5, 5)
    ocean.add_fish(1, 1)
    ocean.add_shark(2, 2, feeding=3)
    assert ocean.cell_contents(1, 1) == Occupant.FISH
    assert ocean.cell_contents(2, 2) == Occupant.SHARK
    # assert ocean.shark_feeding(2, 2) == 3


def test_is_dead_true():
    ocean = Ocean(3, 3)
    assert ocean.is_dead is True


def test_is_dead_false():
    ocean = Ocean(3, 3)
    ocean.add_shark(0, 0)
    assert ocean.is_dead is False
