"""
My attempt at Conway's Game of Life in python.
Rules:
1. Overpopulation: if a living cell is surrounded by more than three living cells, it dies.
2. Stasis: if a living cell is surrounded by two or three living cells, it survives.
3. Underpopulation: if a living cell is surrounded by fewer than two living cells, it dies.
4. Reproduction: if a dead cell is surrounded by exactly three cells, it becomes a live cell.

Things I tried to do differently:
Rather than indiscriminately creating a giant 2d array as the game's field/canvas,
I decided to use a dictionary to keep track of the coordinates of cells.
This allows me to greatly save memory and also increase access speeds.

At the same time, the game's field/canvas's state is calculated and drawn line by line using generators.
Once again, this attempts to save space and reduce blocking computation.

The canvas can dynamically grow in the positive x and y direction, but not in the negative direction. This is a
known limitation.

Overall, the rough computational complexity of this I would put it around O(n) or O(n^2). Where n = number of active
cells. It becomes worse if the cells are spaced apart. Again, this program is mainly optimised for memory efficiency.
On windows, this script should use about ~5.1MB.

The SLOC of this script is rather long due to additional checks when taking arguments from command lines.

Known potential optimisations that I have yet to do:
Parallelize the calculating of the cell rows in the game field, rather than naively looping through it.
Do not calculate for dead cells that are not within 1 square of a live cell to save computation.

"""
from sys import argv, exit
import time
import gc


try:
    import colorama
except ImportError:
    exit("Colorama is required. You can find colorama in anaconda by default, or pip install it.")


SLIDING_WINDOW_SIZE = 3


def _move_cursor(y, x):
    print("\033[%d;%dH" % (y, x))


def _reset_screen():
    """Clears the terminal, resets the cursor """
    print("\x1b[2J")
    _move_cursor(0, 0)


def _step_iterations():
    """ Helper for mainloop function. Asks user whether to continue stepping iteration"""
    while True:
        user_choice = input("Step(Continue) (T/F)?")
        if _parse_args(user_choice, bool) == "bad":
            print("Invalid Choice. Pick T/F")
        else:
            return _parse_args(user_choice, bool)


def _parse_args(arg, arg_type, is_positive=True):
    """ Helper func for validation of arguments depending on type. Returns "bad" if values are bad. Else returns arg"""
    if arg_type is bool:
        if arg.lower() == "false" or arg.lower() == "f":
            return False
        elif arg.lower() == "true" or arg.lower() == "t":
            return True
        return "bad"
    elif arg_type is float:
        try:
            rv = float(arg)
            if is_positive and rv < 0:
                raise ValueError
            return rv
        except ValueError:
            return "bad"
    elif arg_type is int:
        if not arg.isdigit():
            return "bad"
        return int(arg)


def _respond_to_args(index, arg_type, is_positive=True):
    """ Helper function to respond to bad arguments. Will exit upon bad arguments, otherwise will return good args"""
    if _parse_args(argv[index], arg_type, is_positive) == "bad":
        exit("Invalid args\n"
             "Usage: python ConwayGOL.py [number of iterations <int>] [step? <bool>] [FPS <int>] "
             "[show background? <bool>]")
    else:
        return _parse_args(argv[index], arg_type, is_positive)


def count_adjacent_cells(cells, max_x, y_val):
    """ Counts number of adjacent cells for each cell in a single line buffer (horizontal line). Returns a tuple of
    the number of adjacent cells each cell has
    Example:
    a line of OOXXXO will return (0, 1, 1, 2, 1 ,1)

    :param cells: the dictionary that contains the coordinates of the cells
    :type cells: dict
    :param max_x: maximum x coordinate of the cells
    :param y_val: the y-index to check Eg. the first row will be 0, second row will be 1, and so on.
    :return: tuple
    """
    adj_cell_count = []
    for x_val in range(0, max_x + 1): # loop through (cell) in each row
        window = [0] * SLIDING_WINDOW_SIZE ** 2  # the sliding window, like a mask
        for offset in range(0, len(window)):
            cell_offset_x = offset % SLIDING_WINDOW_SIZE - 1
            cell_offset_y = offset // SLIDING_WINDOW_SIZE - 1
            # print(cell_offset_x, cell_offset_y)
            # print("X-val: %d, Y-val: %d" % (x_val + cell_offset_x ,y_val + cell_offset_y))
            if (y_val + cell_offset_y) in cells and (x_val + cell_offset_x) in cells.get(y_val + cell_offset_y):
                window[offset] = 1
        window[4] = 0  # zero out the middle cell so it doesnt double count a live cell
        adj_cell_count.append(window.count(1))
        # print(window)
    return tuple(adj_cell_count)


def create_next_cells(cell_adjnum_pair, max_x):
    """ Creates the next iteration's cells based on how many adjacent cells a cell has. This applies the GOL rules.

    :param cell_adjnum_pair: an iterable containing the (cell, adjacent num 0f cells)
    :type cell_adjnum_pair: iterable
    :param max_x: maximum x coordinate of the cells
    :return: list which contains the next iteration of cells for that specific row/line buffer
    """
    # zeroes out buffer to fulfil these 2 rules:
    # Rule 1. Overpopulation: if a living cell is surrounded by more than three living cells, it dies.
    # 3. Underpopulation: if a living cell is surrounded by fewer than two living cells, it dies.
    line_buffer_mask = [0] * (max_x + 1)

    x_index = 0
    for cell_type, adj_cell_count in cell_adjnum_pair:
        if cell_type == 1:
            # 2. Stasis: if a living cell is surrounded by two or three living cells, it survives.
            if 2 <= adj_cell_count <= 3:
                line_buffer_mask[x_index] = 1
        else:
            # 4. Reproduction: if a dead cell is surrounded by exactly three cells, it becomes a live cell.
            if adj_cell_count == 3:
                line_buffer_mask[x_index] = 1
        x_index += 1
    return line_buffer_mask


def create_line_buffer(cells, max_y, max_x):
    """ Generator which returns a list for each row of cells. Requires the cell coordinate dictionary to work.

    :param cells: dict containing the cell coordinates
    Format is:
    cells = {
        y1: [x1. x2, x3],
        y2: [x1. x2, x3]
    }
    :type cells: dict
    :param max_y: maximum y coordinate of the cells
    :param max_x: maximum x coordinate of the cells
    :return: list
    """
    for row_num in range(0, max_y + 1):
        line_buffer = [0] * (max_x + 1)
        cell_ys = cells.get(row_num)
        if cell_ys is not None:  # if row num exists inside the dictionary of cells
            line_buffer = [1 if _ in cell_ys else 0 for _ in range(max_x + 1)]
        yield line_buffer


def _update_next_iter_cells(next_iter_cells, new_cells_hor, y_val):
    """ Updates the dictionary that contains the next iteration's cells

    :param next_iter_cells: an empty dict; the dictionary that contains the next iteration's cells
    :param new_cells_hor: a new row of cells
    :param y_val: the y-index that the row of cells belongs to
    :return: None
    """
    # adds the new cells back to the dictionary
    for x_index in range(len(new_cells_hor)):
        new_cell = new_cells_hor[x_index]
        if new_cell:  # if is a living cell in the next iteration
            # if the key does not exist ( the y coordinate does not exist), set it to empty set
            if y_val not in next_iter_cells:
                next_iter_cells[y_val] = set()  # using sets to prevent duplicate entries
            # add that living cell's coordinates to the dictionary
            next_iter_cells[y_val].add(x_index)


def operate_on_each_row(cells, max_y, max_x, background_char):
    """ Carries out the following operations on each row of cells:
    1. Print out each row.
    2. Create the next iteration's cell dictionary (same format as the original cell dictionary)
    3. Return the new iteration's dictionary that was created in 2.

    :param cells: dict containing the cell coordinates
    :param max_y: maximum y coordinate of the cells
    :param max_x: maximum x coordinate of the cells
    :param background_char: The character to use for the background
    :return: dict
    """
    y_val = 0  # the y-index to create a line buffer and print out
    next_iter_cells = dict()
    for line_buffer in create_line_buffer(cells, max_y, max_x):
        # draw row to screen
        print(*[u"\u25A0" if cell == 1 else background_char for cell in line_buffer])
        # generate next iteration of cells
        cell_adjnum_pair = zip(line_buffer, count_adjacent_cells(cells, max_x, y_val))
        new_cells_hor = create_next_cells(cell_adjnum_pair, max_x)
        _update_next_iter_cells(next_iter_cells, new_cells_hor, y_val)
        y_val += 1
    return next_iter_cells


def mainloop(cells, ntimes=1, step=True, fps=1, show_background=False):
    """ Loops and prints the game's values ntimes number of iterations.

    :param cells: dict containing the cell coordinates
    Format is:
    cells = {
        y1: [x1. x2, x3],
        y2: [x1. x2, x3]
    }
    :param ntimes: number of iterations/epochs/generations
    :param step: step mode or auto mode
    :param fps: frames(iterations per second to render)
    :param show_background: whether to print out something for the background or leave it as empty
    :return: None
    """
    background_char = ' '
    if show_background:
        background_char = u'\u00B7'  # Block character found in both DOS and Unix
    for _ in range(0, ntimes):
        start_time = time.time()  # used to time each frame/iteration
        _reset_screen()
        max_x = max(cells[max(cells, key=lambda key_y: max(cells[key_y]))]) + 1
        max_y = max(cells, key=lambda key_y: key_y) + 1
        cells = operate_on_each_row(cells, max_y, max_x, background_char).copy()
        gc.collect()
        end_time = time.time()  # used to time each frame/iteration
        if (end_time - start_time) < 1/fps:
            time.sleep(1/fps - (end_time - start_time))
        if step:
            if not _step_iterations():
                step = False


def create_predefined_structure(structure_name, y_start, x_start):
    """ Creates cells arrangements for well-known structures in GOL. Returns the cell dictionary containing that structure

    :param structure_name: the name of the structure to create
    :param y_start: starting y position of the structure
    :param x_start: starting x position of the structure
    :return: dict
    """
    if structure_name == "blinker":
        return {y_start: {x_start, x_start + 1, x_start + 2}}
    elif structure_name == "glider":
        return {
                y_start: {x_start, x_start + 2},
                y_start + 1: {x_start + 1, x_start + 2},
                y_start + 2: {x_start + 1}
                }
    elif structure_name == "pulsar":
        lid = {x_start + 2, x_start + 3, x_start + 4, x_start + 8, x_start + 9, x_start + 10}
        wall = {x_start, x_start + 5, x_start + 7, x_start + 12}
        return {
                y_start: lid,
                y_start + 2: wall,
                y_start + 3: wall,
                y_start + 4: wall,
                y_start + 5: lid,
                y_start + 7: lid,
                y_start + 8: wall,
                y_start + 9: wall,
                y_start + 10: wall,
                y_start + 12: lid,
                }


def merge_dicts(dict1, dict2):
    """ Used to two cell dictionaries together """
    dict3 = {**dict1, ** dict2}
    for key, value in dict3.items():
        if key in dict1 and key in dict2:
            dict3[key] = {*value, *dict1[key]}
    return dict3


def main():
    colorama.init()
    """
    Format is:
    cells = {
        y1: [x1. x2, x3],
        y2: [x1. x2, x3]
    }
    """
    cells = {
         4: {17, 18, 19},  # blinker uncomment this and comment out bottom blinker for interesting things to happen
    }
    cells = merge_dicts(cells, create_predefined_structure("pulsar", 3, 3))
    cells = merge_dicts(cells, create_predefined_structure("pulsar", 20, 20))
    cells = merge_dicts(cells, create_predefined_structure("glider", 20, 40))
    if len(argv) != 5:
        exit("Usage: python ConwayGOL.py [number of iterations <int>] [step? <bool>] [FPS <int>] [show background? <bool>]"
             "\n Eg. python ./conwayGOL.py 50 f 8 f")
    else:
        ntimes = _respond_to_args(1, int, is_positive=True)
        step = _respond_to_args(2, bool)
        fps = _respond_to_args(3, float, is_positive=True)
        show_background = _respond_to_args(4, bool)

        mainloop(cells, ntimes=ntimes, step=step, fps=fps, show_background=show_background)
        print("End")


if __name__ == "__main__":
    main()


