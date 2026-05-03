"""Clipboard helpers — a function to copy text and a drop-in copy button."""
import flet as ft


def copy_to_clipboard(page: ft.Page, text: str, toast: str = "Copied to clipboard") -> bool:
    """Copy `text` to the system clipboard and flash a brief snackbar.

    Returns False if there was nothing to copy or clipboard is unavailable.
    The toast can be turned off by passing `toast=""`.
    """
    if not text:
        return False

    try:
        # Flet uses set_clipboard() to write to clipboard
        page.set_clipboard(text)
        success = True
    except (AttributeError, TypeError):
        # Clipboard unavailable in this environment
        success = False
        if toast:
            toast = "Copy the text manually from the field"

    if toast:
        snack = ft.SnackBar(content=ft.Text(toast), duration=1500)
        page.overlay.append(snack)
        snack.open = True
        page.update()
    return success


class CopyButton(ft.IconButton):
    """An icon button that copies a fixed value to the clipboard on click."""

    def __init__(
        self,
        page: ft.Page,
        value: str,
        tooltip: str = "Copy to clipboard",
        toast: str = "Copied to clipboard",
        **kwargs,
    ):
        super().__init__(
            icon=ft.Icons.COPY,
            tooltip=tooltip,
            on_click=lambda _: copy_to_clipboard(page, value, toast),
            **kwargs,
        )
