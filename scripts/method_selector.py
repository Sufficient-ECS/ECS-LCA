#!/usr/bin/env -S PYTHONPATH=${PWD} uv run

import urwid
import bw2data as bd
from src import setup_project_ei
from src.utils.utils import load_tuple_file
import os

setup_project_ei("ECS-LCA")
rows = list(bd.methods)

os.makedirs("results/", exist_ok=True)
check = set(load_tuple_file("results/method_list.txt", sep=','))

def save_tuple_set(data_set, filename, sep="|"):
    """
    Saves a set of (str, str) tuples to a file, one per line.
    """
    with open(filename, "w", encoding="utf-8") as f:
        for x in data_set:
            f.write(f"{x}\n")

def on_checkbox_change(checkbox, state, ud):
    if state:
        check.add(ud)
    else:
        check.discard(ud)

class MenuApp:
    def __init__(self):
        self.history = []

        self.placeholder = urwid.WidgetPlaceholder(
            self.build_menu([0, rows])
        )

        self.loop = urwid.MainLoop(
            self.placeholder,
            unhandled_input=self.handle_input,
        )

    def build_menu(self, data):
        n, rows = data
        
        labels = set([i[n] for i in rows])
        while len(labels) == 1 and len(rows) > 1:
            n += 1
            labels = set([i[n] for i in rows])

        widgets = []
        drawn = set()
        for x in rows:
            x = list(x)
            if len(x) > n+1:
                if x[n] in drawn:
                    continue
                drawn.add(x[n])
                button = urwid.Button(x[n])
                urwid.connect_signal(
                    button,
                    "click",
                    self.open_submenu,
                    [n+1, [list(i)  for i in rows if i[n] == x[n]]]
                )

                widgets.append(
                    urwid.AttrMap(
                        button,
                        None,
                        focus_map="reversed",
                    )
                )

            else:
                cb = urwid.CheckBox(
                    x[n],
                    state=tuple(x) in check,
                    #user_data=tuple(x)
                )
                urwid.connect_signal(cb, 'change', on_checkbox_change, user_arg=tuple(x))
                widgets.append(cb)

        return urwid.ListBox(
            urwid.SimpleFocusListWalker(widgets)
        )

    def open_submenu(self, button, submenu):
        self.history.append(
            self.placeholder.original_widget
        )

        self.placeholder.original_widget = (
            self.build_menu(submenu)
        )

    def handle_input(self, key):
        if key in ("q", "Q"):
            save_tuple_set(check, "results/method_list.txt")
            raise urwid.ExitMainLoop()

        if key == "backspace" and self.history:
            self.placeholder.original_widget = (
                self.history.pop()
            )

    def run(self):
        self.loop.run()


if __name__ == "__main__":
    MenuApp().run()