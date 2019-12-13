# Python Section
## Conway's Game of Life
<em><strong>Requires Python 3 and colorama module.</strong></em>
```
Usage: 
python ConwayGOL.py [number of iterations <int>] [step? <bool>] [FPS <int>] [show background? <bool>]
```
```
Example:
python ./conwayGOL.py 50 f 8 f
```
### Description
My attempt at Conway's Game of Life in python. <br>
#### Rules:
1. Overpopulation: if a living cell is surrounded by more than three living cells, it dies. 
2. Stasis: if a living cell is surrounded by two or three living cells, it survives. 
3. Underpopulation: if a living cell is surrounded by fewer than two living cells, it dies. 
4. Reproduction: if a dead cell is surrounded by exactly three cells, it becomes a live cell. 

#### Things I tried to do differently: <br>
Rather than indiscriminately creating a giant 2d array as the game's field/canvas,
I decided to use a dictionary to keep track of the coordinates of cells. This allows me to greatly save memory and also increase access speeds. 

At the same time, the game's field/canvas's state is calculated and drawn line by line using generators. 
Once again, this attempts to save space and reduce blocking computation.

The canvas can dynamically grow in the positive x and y direction, but not in the negative direction. This is a
known limitation. 

Overall, the rough computational complexity of this I would put it around O(n) or O(n^2). Where n = number of active <br>
cells. It becomes worse if the cells are spaced apart. Again, this program is mainly optimised for memory efficiency.
On windows, this script should use about ~5.1MB.

The SLOC of this script is rather long due to additional checks when taking arguments from command lines.

#### Known potential optimisations that I have yet to do: 
- Parallelize the calculating of the cell rows in the game field, rather than naively looping through it. <br>
- Do not calculate for dead cells that are not within 1 square of a live cell to save computation. <br>
