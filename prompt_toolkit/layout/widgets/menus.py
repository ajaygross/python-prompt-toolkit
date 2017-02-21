from __future__ import unicode_literals

from .base import BORDER

from prompt_toolkit.eventloop import EventLoop
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import HSplit, Window, FloatContainer, Float, ConditionalContainer
from prompt_toolkit.layout.controls import TokenListControl
from prompt_toolkit.layout.widgets import Shadow
from prompt_toolkit.token import Token
from prompt_toolkit.utils import get_cwidth

__all__ = (
    'MenuContainer',
    'MenuItem',
)


class MenuContainer(object):
    """
    :param floats: List of extra Float objects to display.
    """
    def __init__(self, body, menu_items=None, floats=None, loop=None):
        assert isinstance(menu_items, list) and \
            all(isinstance(i, MenuItem) for i in menu_items)
        assert floats is None or all(isinstance(f, Float) for f in floats)
        assert loop is None or isinstance(loop, EventLoop)

        self.body = body
        self.menu_items = menu_items
        self.selected_menu = [0]

        # Key bindings.
        kb = KeyBindings()

        @Condition
        def in_main_menu(app):
            return len(self.selected_menu) == 1

        @Condition
        def in_sub_menu(app):
            return len(self.selected_menu) > 1

        # Navigation through the main menu.

        @kb.add(Keys.Left, filter=in_main_menu)
        def _(event):
            self.selected_menu[0] = max(0, self.selected_menu[0] - 1)

        @kb.add(Keys.Right, filter=in_main_menu)
        def _(event):
            self.selected_menu[0] = min(
                len(self.menu_items) - 1, self.selected_menu[0] + 1)

        @kb.add(Keys.Down, filter=in_main_menu)
        def _(event):
            self.selected_menu.append(0)

        # Sub menu navigation.

        @kb.add(Keys.Left, filter=in_sub_menu)
        def _(event):
            " Go back to parent menu. "
            if len(self.selected_menu) > 1:
                self.selected_menu.pop()

        @kb.add(Keys.Right, filter=in_sub_menu)
        def _(event):
            " go into sub menu. "
            if self._get_menu(len(self.selected_menu) - 1).children:
                self.selected_menu.append(0)

            # If This item does not have a sub menu. Go up in the parent menu.
            elif len(self.selected_menu) == 2 and self.selected_menu[0] < len(self.menu_items) - 1:
                self.selected_menu = [min(
                    len(self.menu_items) - 1, self.selected_menu[0] + 1)]
                if self.menu_items[self.selected_menu[0]].children:
                    self.selected_menu.append(0)

        @kb.add(Keys.Up, filter=in_sub_menu)
        def _(event):
            if len(self.selected_menu) == 2 and self.selected_menu[1] == 0:
                self.selected_menu.pop()
            elif self.selected_menu[-1] > 0:
                self.selected_menu[-1] -= 1

        @kb.add(Keys.Down, filter=in_sub_menu)
        def _(event):
            if self.selected_menu[-1] < len(self._get_menu(len(self.selected_menu) - 2).children) - 1:
                self.selected_menu[-1] += 1

        @kb.add(Keys.Enter)
        def _(event):
            " Click the selected menu item. "
            item = self._get_menu(len(self.selected_menu) - 1)
            if item.handler:
                item.handler(event.app)

        # Controls.
        self.control = TokenListControl(
            self._get_menu_tokens,
            key_bindings=kb,
            focussable=True)

        self.window = Window(
            height=1,
            content=self.control,
            token=Token.MenuBar)

        submenu = self._submenu(0)
        submenu2 = self._submenu(1)
        submenu3 = self._submenu(2)

        @Condition
        def has_focus(app):
            return app.layout.current_window == self.window

        self.container = FloatContainer(
            content=HSplit([
                # The titlebar.
                self.window,

                # The 'body', like defined above.
                body,
            ]),
            floats=[
                Float(xcursor=self.window, ycursor=self.window,
                      content=ConditionalContainer(
                          content=Shadow(body=submenu),
                          filter=has_focus)),
                Float(attach_to_window=submenu,
                      xcursor=True, ycursor=True,
                      allow_cover_cursor=True,
                      content=ConditionalContainer(
                          content=Shadow(body=submenu2),
                          filter=has_focus & Condition(lambda app: len(self.selected_menu) >= 1))),
                Float(attach_to_window=submenu2,
                      xcursor=True, ycursor=True,
                      allow_cover_cursor=True,
                      content=ConditionalContainer(
                          content=Shadow(body=submenu3),
                          filter=has_focus & Condition(lambda app: len(self.selected_menu) >= 2))),

                # --
            ] + (floats or [])
        )

    def _get_menu(self, level):
        menu = self.menu_items[self.selected_menu[0]]

        for i, index in enumerate(self.selected_menu[1:]):
            if i < level:
                try:
                    menu = menu.children[index]
                except IndexError:
                    return MenuItem('debug')

        return menu

    def _get_menu_tokens(self, app):
        result = []
        focussed = (app.layout.current_window == self.window)

        for i, item in enumerate(self.menu_items):
            result.append((Token.MenuBar, ' '))
            if i == self.selected_menu[0] and focussed:
                result.append((Token.SetMenuPosition, ''))
                token = Token.MenuBar.SelectedItem
            else:
                token = Token.MenuBar
            result.append((token, item.text))
        return result

    def _submenu(self, level=0):
        def get_tokens(app):
            result = []
            if level < len(self.selected_menu):
                menu = self._get_menu(level)
                if menu.children:
                    result.append((Token.Menu, BORDER.TOP_LEFT))
                    result.append((Token.Menu, BORDER.HORIZONTAL * (menu.width + 4)))
                    result.append((Token.Menu, BORDER.TOP_RIGHT))
                    result.append((Token, '\n'))
                    try:
                        selected_item = self.selected_menu[level + 1]
                    except IndexError:
                        selected_item = -1

                    for i, item in enumerate(menu.children):
                        if i == selected_item:
                            result.append((Token.SetCursorPosition, ''))
                            token = Token.MenuBar.SelectedItem
                        else:
                            token = Token

                        result.append((Token.Menu, BORDER.VERTICAL))
                        if item.text == '-':
                            result.append((token | Token.Menu.Border, '{}'.format(BORDER.HORIZONTAL * (menu.width + 3))))
                        else:
                            result.append((token, ' {}'.format(item.text).ljust(menu.width + 3)))

                        if item.children:
                            result.append((token, '>'))
                        else:
                            result.append((token, ' '))

                        if i == selected_item:
                            result.append((Token.SetMenuPosition, ''))
                        result.append((Token.Menu, BORDER.VERTICAL))

                        result.append((Token, '\n'))

                    result.append((Token.Menu, BORDER.BOTTOM_LEFT))
                    result.append((Token.Menu, BORDER.HORIZONTAL * (menu.width + 4)))
                    result.append((Token.Menu, BORDER.BOTTOM_RIGHT))
            return result

        return Window(
                    TokenListControl(get_tokens),
                    token=Token.Menu,
                    transparent=False)

    def __pt_container__(self):
        return self.container


class MenuItem(object):
    def __init__(self, text='', handler=None, children=None, shortcut=None,
                 disabled=False):
        self.text = text
        self.handler = handler
        self.children = children or []
        self.shortcut = shortcut
        self.disabled = disabled
        self.selected_item = 0

    @property
    def width(self):
        if self.children:
            return max(get_cwidth(c.text) for c in self.children)
        else:
            return 0
