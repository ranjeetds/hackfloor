"""Renderers for scan results: a rich terminal view and a Markdown report."""

from hackfloor.report.markdown import render_markdown
from hackfloor.report.terminal import render_terminal

__all__ = ["render_markdown", "render_terminal"]
