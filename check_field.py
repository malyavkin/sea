from collections import Counter
from itertools import product
from typing import List, Optional, Tuple, Dict, Any

import pydash as py_

from Coord import Coord
from config import CellState, SHIP_CONFIG, FIELD_DIMENSIONS
from helpers import group_by_keys, orthogonal, adjacent_square
from my_types.matrix_int import MatrixInt
from ship import Ship


def get_available_cells(field: MatrixInt, dimensions: Coord) -> List[Coord]:
    checked = find_checked_cells(field)
    all_cells = [Coord(tup) for tup in product(range(dimensions.i), range(dimensions.j))]
    nearby = py_.flat_map(checked, lambda cell: find_adjacent_cells(cell, all_cells))
    return list(set(all_cells) - set(nearby) - set(checked))


def find_straight_segments(cells: List[Coord], vertical: bool = False) -> List[List[Coord]]:
    groups = []
    sorted_cells = sorted(cells)
    increment = Coord((1, 0)) if vertical else Coord((0, 1))
    while sorted_cells:
        group = []
        cell = sorted_cells[0]

        while cell in sorted_cells:
            sorted_cells.remove(cell)
            group.append(cell)
            cell += increment

        groups.append(group)
    return groups


def find_checked_cells(field: MatrixInt) -> List[Coord]:
    return [
        Coord((i, j))
        for i, row in enumerate(field)
        for j, cell in enumerate(row)
        if cell in [CellState.CELL_DECK.value, CellState.CELL_DECK_DEAD.value]
    ]


def find_adjacent_cells(origin: Coord, cells: List[Coord], only_orthogonal: bool = False) -> List[Coord]:
    """
    Находит соседние клетки от origin среди cells
    :param only_orthogonal:
    :param origin:
    :param cells:
    :return:
    """
    chosen_nearness = orthogonal if only_orthogonal else adjacent_square
    diffs = py_.map_(cells, lambda other: other-origin)
    adjacent = py_.filter_(
        py_.zip_(cells, diffs),
        lambda pair: pair[1] in chosen_nearness,
    )

    return py_.map_(adjacent, 0)


def find_adjacent_cells_recursive(origin: Coord, cells: List[Coord]) -> List[Coord]:
    selected = [origin]
    while True:
        current_selected = []
        for cell in selected:
            current_selected += find_adjacent_cells(cell, cells)

        current_selected = filter(lambda sel: sel not in selected, current_selected)
        current_selected = list(set(current_selected))
        if not current_selected:
            break

        selected += current_selected

    return sorted(selected)


def find_ships(field: MatrixInt) -> List[Ship]:
    found_ships = []
    cells = find_checked_cells(field)
    while cells:
        adjacent_group = find_adjacent_cells_recursive(cells[0], cells)
        cells = [
            coord for coord in cells if coord not in adjacent_group
        ]
        found_ships.append(Ship(adjacent_group))
    return found_ships


def check_ship_shape(ship: Ship):
    """
    Проверяет форму корабля
    :param ship: Список клеток корабля
    :return: True/False
    """
    if len(ship) == 1:
        return True
    ship = Ship(sorted(ship.cells))
    increments = map(
        lambda pair: pair[1] - pair[0],
        zip(ship.cells, ship.cells[1:]))
    common_increment = list(set(increments))
    return len(common_increment) == 1 and common_increment[0] in [Coord((0, 1)), Coord((1, 0))]


def check_fleet_config(fleet: Any, is_setup_stage=False) -> Tuple[bool, Optional[Dict[int, int]]]:
    """
    Проверяет конфигурацию флота (1 4палубный, 2 3палубных итд)
    :param fleet: список кораблей
    :param is_setup_stage: Если True, то отключает проверку на недостающие корабли (считается, что поле находится в
    процессе заполнения и игрок еще не выставил все корабли)
    :return: (bool, [dict])
    Если флот собран корректно, возвращает True, None
    Если есть лишние корабли, возвращает False, None
    Если кораблей не хватает, возвращает True или False (в зависимости от is_setup_stage) и список слотов
    """
    lengths = map(len, fleet)
    config = Counter(lengths)

    if config == SHIP_CONFIG:
        return True, None

    # Checking for extra ships
    configs = group_by_keys((config, SHIP_CONFIG), 0)
    diff = py_.map_values(configs, lambda counts: counts[1] - counts[0])
    extra_ships = any(py_.map_(list(diff.values()), lambda x: x < 0))
    if extra_ships:
        return False, None

    missing_ships = {k: v for k, v in diff.items() if v > 0}
    if missing_ships:
        return is_setup_stage, missing_ships


def check_ship_bounds(ship: Ship):
    """
    Проверяет, что корабль внутри поля
    :param ship: Список клеток корабля
    :return: True/False
    """
    return all(
        0 <= cell.i < FIELD_DIMENSIONS.i and 0 <= cell.j < FIELD_DIMENSIONS.j
        for cell in ship.cells
    )


def validate_field(field: MatrixInt, is_setup_stage: bool = False):
    """
    Проверяет поле на ошибки
    :param field: 2d список клеток
    :param is_setup_stage: Если True, то отключает проверку на недостающие корабли (считается, что поле находится в
    процессе заполнения и пользователь еще не выставил все корабли)
    :return:
    """
    ships = find_ships(field)
    config_correct, diff = check_fleet_config(ships, is_setup_stage)
    assert config_correct, "Fleet config is invalid (ships are touching or extra/missing ship)"
    for ship in ships:
        assert check_ship_shape(ship), "There is a deformed ship somewhere on the field ({})".format(ship)
        assert check_ship_bounds(ship), "Ship outside bounds ({})".format(ship)
    return True
