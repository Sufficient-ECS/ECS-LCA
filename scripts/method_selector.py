#!/usr/bin/env -S PYTHONPATH=${PWD} uv run

import urwid
import bw2data as bd
import click
import os
from pathlib import Path
from src import setup_project_ei
from src.utils.utils import load_tuple_file

def save_tuple_set(data_set, filename, sep="|"):
    """
    Saves a set of (str, str) tuples to a file, one per line.
    """
    with open(filename, "w", encoding="utf-8") as f:
        for x in data_set:
            f.write(f"{x}\n")

class MenuApp:
    def __init__(self, mfile):

        setup_project_ei("ECS-LCA")
        rows = list(bd.methods)

        os.makedirs("results/", exist_ok=True)

        self.mfile = Path(mfile)
        self.mfile.parent.mkdir(parents=True, exist_ok=True)

        self.check = set(load_tuple_file(mfile, sep=','))
        self.history = []

        self.placeholder = urwid.WidgetPlaceholder(
            self.build_menu([0, rows])
        )

        self.loop = urwid.MainLoop(
            self.placeholder,
            unhandled_input=self.handle_input,
        )
    def on_checkbox_change(self, checkbox, state, ud):
        if state:
            self.check.add(ud)
        else:
            self.check.discard(ud)

    def treat_node(self, rows, x, n, prefix = ""):
        if len(x)-1 == n: # This is (not) the end            
            cb = urwid.CheckBox(
                prefix + x[n],
                state=tuple(x) in self.check,
            )
            urwid.connect_signal(cb, 'change', self.on_checkbox_change, user_arg=tuple(x))
            return cb
        else:
            next_level = [list(i)  for i in rows if i[n] == x[n]]
            
            if len(next_level) == 1:
                return self.treat_node(next_level, next_level[0], n+1, prefix = f"{prefix + x[n]} -- ")
            
            button = urwid.Button(prefix + x[n])
            urwid.connect_signal(
                button,
                "click",
                self.open_submenu,
                [n+1, next_level]
            )

            return urwid.AttrMap(
                    button,
                    None,
                    focus_map="reversed",
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
            if x[n] in drawn:
                continue
            drawn.add(x[n])
            cb = self.treat_node(rows, x, n)
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
            save_tuple_set(self.check, self.mfile)
            raise urwid.ExitMainLoop()

        if key == "backspace" and self.history:
            self.placeholder.original_widget = (
                self.history.pop()
            )

    def run(self):
        self.loop.run()

@click.command()
@click.option("-m", "--method_file", default="./results/method_list.txt", help="File of impact methods to load/store")
def main(method_file):
    app = MenuApp(method_file)
    app.run()

if __name__ == "__main__":
    main()