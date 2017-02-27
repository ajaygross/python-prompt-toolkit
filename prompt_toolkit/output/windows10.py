from __future__ import unicode_literals

from prompt_toolkit.renderer import Output

from .vt100 import Vt100_Output
from .win32 import Win32Output
from ctypes import windll, byref
from ctypes.wintypes import DWORD
from ..win32_types import STD_OUTPUT_HANDLE

__all__ = (
    'Windows10_Output',
)

# See: https://msdn.microsoft.com/pl-pl/library/windows/desktop/ms686033(v=vs.85).aspx
ENABLE_PROCESSED_INPUT = 0x0001
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004


class Windows10_Output(object):
    """
    Windows 10 output abstraction. This enables and uses vt100 escape sequences.
    """
    def __init__(self, stdout):
        self.win32_output = Win32Output(stdout)
        self.vt100_output = Vt100_Output(stdout, lambda: None)

        self._original_mode = DWORD(0)
        self._hconsole = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

    def start_rendering(self):
        " Called when rendering starts. "
        # Remember the previous console mode.
        windll.kernel32.GetConsoleMode(self._hconsole, byref(self._original_mode))

        # Enable processing of vt100 sequences.
        windll.kernel32.SetConsoleMode(self._hconsole, DWORD(
            ENABLE_PROCESSED_INPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING))

    def stop_rendering(self):
        " Called when rendering stops. "
        # Restore.
        windll.kernel32.SetConsoleMode(self._hconsole, self._original_mode)

    def __getattr__(self, name):
        if name in ('get_size', 'get_rows_below_cursor_position',
                    'enable_mouse_support', 'disable_mouse_support',
                    'scroll_buffer_to_prompt', 'get_win32_screen_buffer_info',
                    'enable_bracketed_paste', 'disable_bracketed_paste'):
            return getattr(self.win32_output, name)
        else:
            return getattr(self.vt100_output, name)


Output.register(Windows10_Output)
