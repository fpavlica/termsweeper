from textual.app import App, ComposeResult
from textual.containers import Grid, HorizontalGroup
from textual.widgets import Button, Static, Footer, Digits
from textual.events import MouseEvent
from textual.message import Message
from textual import on
from typing import NamedTuple
from enum import Enum
import random

# standard minesweeper constants
GRID_WIDTH = 16 # 9 16 30
GRID_HEIGHT = 16 # 9 16 16
MINES_AMOUNT = 40 # 10 40 99

class Position(NamedTuple):
    row: int
    col: int

class SelectAction(Enum):
    OPEN=1
    FLAG=2

class MineButton(Button):
    # key bindings for actions
    BINDINGS = [
        ("m,x", "flag_selected", "Flag"),
        ("space", "open_selected", "Open"),
    ]

    CHAR_UNOPENED = "·"
    CHAR_EMPTY = " "
    CHAR_FLAGGED = "⚑"
    CHAR_MINE = "✷"
    NUMBER_COLORS = ["black", "blue", "green", "red", "darkblue", "darkred", "darkcyan", "white", "grey", "deeppink"]

    def __init__(self, position: Position, label = None, variant = "default", *, name = None, id = None, 
                 classes = None, disabled = False, tooltip = None, action = None):
        super().__init__(label, variant, name=name, id=id, classes=classes, disabled=disabled, tooltip=tooltip, 
                         action=action)
        
        self.position = position
        self.reset()

        #override button default sizings to make a grid
        self.styles.min_width=3
        self.styles.min_height=1
        self.styles.width= 3
        self.styles.height= 1
        self.styles.border_top = ("hidden", "white")
        self.styles.border_bottom = ("hidden", "white") 

    def toggle_flagged(self):
        self.flagged = not self.flagged
        self.label = self.CHAR_FLAGGED if self.flagged else self.CHAR_UNOPENED

    def set_number(self, value:int):
        self.label = str(value)
        self.styles.color = self.NUMBER_COLORS[value]

    def explode(self):
        self.label = self.CHAR_MINE
        self.styles.color  = "deeppink"

    class Selected(Message):
        def __init__(self, button, action: SelectAction):
            self.action = action
            self.button = button
            super().__init__()

    def on_click(self, event: MouseEvent):
        self.post_message(self.Selected(self, SelectAction.OPEN if event.button==1 else SelectAction.FLAG))

    def action_flag_selected(self):
        self.post_message(self.Selected(self, SelectAction.FLAG))
    def action_open_selected(self):
        self.post_message(self.Selected(self, SelectAction.OPEN))

    def reset(self):
        """Reset to default values"""
        self.disabled = False
        self.explored = False
        self.flagged = False
        self.can_focus = False
        self.label = self.CHAR_UNOPENED
        self.styles.color= "white"
        self.mines_flagged = 0

class MineGrid(Static):
    BINDINGS = [
        ("up,w", "move_cell_focus('up')", " "),
        ("left,a", "move_cell_focus('left')", " "),
        ("down,s", "move_cell_focus('down')", " "),
        ("right,d", "move_cell_focus('right')", " "),
    ]
    
    total_explored = 0
    mines_flagged = 0
    _current_cell = Position(0,0)
    buttons = [[MineButton(Position(row,col)) for col in range(GRID_WIDTH)]for row in range(GRID_HEIGHT)]

    def __init__(self, content = "", *, expand = False, shrink = False, markup = True, name = None, id = None, 
                 classes = None, disabled = False):
        super().__init__(content, expand=expand, shrink=shrink, markup=markup, name=name, id=id, classes=classes, 
                         disabled=disabled)
        self.mines = self.generate_mines(MINES_AMOUNT)

    def on_mount(self):
        self.set_current_cell(Position(0,0))
        
    def generate_mines(self,amount: int) ->set:
        """Generate a random set of unique points on a grid"""
        return set(
            Position(int(x/GRID_WIDTH), x%GRID_WIDTH ) for x in random.sample(range(GRID_HEIGHT*GRID_WIDTH), amount))

    def button_at(self, position: Position) -> MineButton:
        return self.buttons[position.row][position.col]

    # function to render the widget (name specified by the Textual library)
    def compose(self) -> ComposeResult:
        grid = Grid(*(button for row in self.buttons for button in row))
        grid.styles.grid_size_rows = GRID_HEIGHT
        grid.styles.grid_size_columns = GRID_WIDTH
        grid.styles.width = 3* GRID_WIDTH
        grid.styles.height = "auto"
        yield grid

    @on(MineButton.Selected)
    def handle_selected(self, event: MineButton.Selected):
        # update position marker in case it was reached by mouse click rather than keyboard
        if event.button.position != self._current_cell:
            self.set_current_cell(event.button.position) 
        
        if event.action == SelectAction.OPEN and event.button.flagged is False:
                self.open_cell(event.button)
        elif event.action == SelectAction.FLAG and event.button.explored is False:
                self.flag_cell(event.button)
        pass

    def open_cell(self, button: MineButton):
        """Count the number of neighbouring mines. If this is 0, also open all adjacent cells.
           If the chosen cell contained a mine, explode and end the game with a loss."""
        if button.explored:
            return #don't explore already explored cells
        button.explored = True
        self.total_explored += 1
        pos = button.position
        if pos in self.mines:
            # stepped on a mine
            button.label = MineButton.CHAR_MINE
            button.styles.color = MineButton.NUMBER_COLORS[9]
            self.post_message(self.GameEnd(win=False))
            return

        mines_nearby = self.count_mines_near(pos)
        if mines_nearby == 0:
            button.label = MineButton.CHAR_EMPTY
            # open all adjacent cells if the mine count is 0 (all adjacent cells are safe)
            for i in range(max(0,pos.row-1), min(GRID_HEIGHT,pos.row+1+1)):
                for j in range(max(0,pos.col-1), min(GRID_WIDTH,pos.col+1+1)):
                    button = self.button_at(Position(i,j))
                    self.open_cell(button)
        else:
            button.set_number(mines_nearby)
        # win condition is if all explorable cells have been explored without stepping on a mine
        if self.total_explored >= GRID_HEIGHT * GRID_WIDTH - MINES_AMOUNT:
            self.post_message(self.GameEnd(win=True))

    def flag_cell(self, button: MineButton):
        self.mines_flagged += 1 if not button.flagged else -1
        button.toggle_flagged()

    class GameEnd(Message):
        def __init__(self, win: bool):
            super().__init__()
            self.win = win

    @on(GameEnd)
    def end_game(self, event: GameEnd):
        self.disabled = True
        self.reveal_mines(event.win)

    def reveal_mines(self, won=False):
        for mine in self.mines:
            if won:
                # show mines as flags if game won without them already being flagged
                if not self.button_at(mine).flagged:
                    self.button_at(mine).toggle_flagged()
            else:
                # in case of a loss, just explode all mines (most recent one will stay highlighted)
                self.button_at(mine).explode()


    def set_current_cell(self, value):
        """Update the current cell while also making it the only tab-focusable cell in the grid."""
        self.button_at(self._current_cell).can_focus = False

        self._current_cell = value
        
        self.button_at(self._current_cell).can_focus = True
        self.button_at(self._current_cell).focus()

    def count_mines_near(self,pos: Position):
        count = 0
        for i in range(pos.row-1, pos.row+1+1):
            for j in range(pos.col-1, pos.col+1+1):
                if Position(i,j) in self.mines:
                    count +=1
        return count


    def action_move_cell_focus(self, dir):
        
        match dir:
            case "left": 
                self.set_current_cell(Position(self._current_cell.row, max(0,self._current_cell.col -1)))
            case "right": 
                self.set_current_cell(Position(self._current_cell.row, min(GRID_WIDTH-1, self._current_cell.col+1)))
            case "up": 
                self.set_current_cell(Position(max(0,self._current_cell.row -1), self._current_cell.col))
            case "down": 
                self.set_current_cell(Position(min(GRID_HEIGHT-1, self._current_cell.row+1), self._current_cell.col))

    def reset(self):
        self.total_explored = 0
        self.mines_flagged = 0
        for row in self.buttons:
            for button in row:
                button.reset()
        self.set_current_cell(Position(0,0))
        self.mines = self.generate_mines(MINES_AMOUNT)
        self.disabled = False


class InfoBar(HorizontalGroup):
    """Top bar containing the number of mines remaining, a status indicator, and a timer"""

    timer_value = 0
    timer_widget = Digits("000")
    timer_widget.styles.text_align = "right"

    restart_button = Button("🙂")
    mine_counter = Digits(f"{MINES_AMOUNT:0>3}")
    def compose(self) -> ComposeResult:
        yield self.mine_counter
        yield self.restart_button
        yield self.timer_widget

    def on_mount(self):
        self.timer_interval = self.set_interval(1,self.update_timer)

    def update_timer(self):
        self.timer_value += 1
        self.timer_widget.update(f"{self.timer_value:0>3}")
    def on_button_pressed(self, event):
        self.post_message(Reset())

    def reset(self):
        self.timer_value = 0
        self.timer_widget.update("000")
        self.timer_interval.reset()
        self.timer_interval.resume()
        self.restart_button.label= "🙂"
        self.mine_counter.update(f"{MINES_AMOUNT:0>3}")
    pass

class Reset(Message):
    pass # child class of a message so it's easier to identify it

class TermSweeperApp(App):
    info_bar = InfoBar()
    mine_grid = MineGrid()
    def compose(self) -> ComposeResult:
        yield self.info_bar
        yield self.mine_grid
        yield Footer()
    
    @on(Reset)
    def reset(self):
        self.mine_grid.reset()
        self.info_bar.reset()
        
    @on(MineGrid.GameEnd) 
    #ideally this would be in InfoBar, but the GameEnd event doesn't seem to get propagated back down to siblings
    def handle_game_end(self, event: MineGrid.GameEnd):
        self.info_bar.restart_button.label = "😎" if event.win else "😵"
        self.info_bar.timer_interval.pause()

    @on(MineButton.Selected)
    def flag_update(self, event: MineButton.Selected):
        if event.action == SelectAction.FLAG:
            self.info_bar.mine_counter.update(f"{(MINES_AMOUNT-self.mine_grid.mines_flagged):0>3}")

if __name__ == "__main__":
    app = TermSweeperApp()
    app.run()