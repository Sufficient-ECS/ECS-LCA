#!/usr/bin/env -S PYTHONPATH=${PWD} uv run

from premise.filesystem_constants import VARIABLES_DIR
import yaml
import urwid
import click
import os
from pathlib import Path
from src.utils.utils import load_tuple_file, save_tuple_set

class MenuApp:
    def __init__(self, mfile):
        with open(VARIABLES_DIR/"constants.yaml", "r") as f:
            premise_constants = yaml.safe_load(f)

        self.models = premise_constants["SUPPORTED_MODELS"]
        self.pathways = premise_constants["SUPPORTED_PATHWAYS"]
        os.makedirs("results/", exist_ok=True)
        self.check = set(load_tuple_file(mfile, sep=','))

        self.mfile = Path(mfile)
        self.mfile.parent.mkdir(parents=True, exist_ok=True)

        self.history = []

        self.placeholder = urwid.WidgetPlaceholder(
            self.build_menu([0, []])
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


    def build_menu(self, data):
        n, current = data

        widgets = []

        rows = [
            self.models,
            self.pathways,
            range(2005, 2100+1)
            ][n]

        for i in rows:
            x = current + [i]
            if n == 2:
                cb = urwid.CheckBox(
                    str(i),
                    state=tuple(x) in self.check,
                )
                urwid.connect_signal(cb, 'change', self.on_checkbox_change, user_arg=tuple(x))
            else:
                button = urwid.Button(i)
                urwid.connect_signal(
                    button,
                    "click",
                    self.open_submenu,
                    [n+1, x]
                )

                cb = urwid.AttrMap(
                        button,
                        None,
                        focus_map="reversed",
                    )
        
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
@click.argument("scenarios_file", default="./results/scenarios_list.txt")
def main(scenarios_file):
    app = MenuApp(scenarios_file)
    app.run()

if __name__ == "__main__":
    main()