"""
Markdown to Mobile-Friendly PDF Tool - Convert markdown files with charts and images to PDF.

Uses Playwright with Chromium for highest quality rendering.
"""

import logging
from pathlib import Path
from typing import Annotated

from deerflow.agents.thread_state import ThreadState
from langchain.tools import InjectedToolCallId, ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.typing import ContextT

logger = logging.getLogger(__name__)


def _convert_markdown_to_pdf(
        markdown_path: Path,
        output_path: Path,
        mobile_friendly: bool = True,
) -> tuple[bool, str]:
    """Convert markdown to PDF using Playwright for highest quality rendering.

    Args:
        markdown_path: Path to input markdown file
        output_path: Path to output PDF file
        mobile_friendly: Whether to use mobile-friendly layout

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        import markdown
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        return False, f"Required libraries not installed: {e}. Run: pip install markdown playwright && playwright install chromium"

    try:
        # Read markdown content
        with open(markdown_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # Convert markdown to HTML with extensions for better rendering
        html_content = markdown.markdown(
            md_content,
            extensions=[
                'extra',  # Tables, fenced code blocks, etc.
                'codehilite',  # Syntax highlighting
                'toc',  # Table of contents
                'nl2br',  # Newline to <br>
                'sane_lists',  # Better list handling
            ]
        )

        # Premium dark theme CSS with beautiful typography
        mobile_css = """
        /* ============================================================
           BEAUTIFUL MARKDOWN → PDF STYLESHEET
           Dark theme · Premium typography · Mobile-friendly
           ============================================================ */

        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&family=Lora:ital,wght@0,400;0,600;1,400&display=swap');

        /* ── Custom Properties ─────────────────────────────────────── */
        :root {
          --bg-base:        #0f0f12;
          --bg-surface:     #16161d;
          --bg-elevated:    #1e1e28;
          --bg-highlight:   #252532;

          --border-subtle:  #2a2a38;
          --border-medium:  #3a3a50;

          --text-primary:   #eeeef2;
          --text-secondary: #a0a0b8;
          --text-muted:     #666680;

          --accent-blue:    #5b8dee;
          --accent-blue-lo: #1e2d52;
          --accent-purple:  #9d7fe8;
          --accent-amber:   #f5a623;
          --accent-cyan:    #4ecdc4;
          --accent-rose:    #f06292;
          --accent-green:   #6fcf97;

          --gradient-h2:    linear-gradient(135deg, #1c2d5e 0%, #162044 100%);
          --gradient-rule:  linear-gradient(90deg, transparent 0%, #5b8dee 40%, #9d7fe8 60%, transparent 100%);
          --gradient-th:    linear-gradient(180deg, #1e2030 0%, #161622 100%);

          --radius-sm:  6px;
          --radius-md:  10px;
          --radius-lg:  14px;

          --shadow-sm:  0 1px 4px rgba(0,0,0,0.4);
          --shadow-md:  0 4px 16px rgba(0,0,0,0.5);
          --shadow-lg:  0 8px 32px rgba(0,0,0,0.6);
          --shadow-glow: 0 0 24px rgba(91,141,238,0.15);
        }

        /* ── Page Setup ────────────────────────────────────────────── */
        @page {
          size: A4;
          margin: 0;
          background: var(--bg-base);
        }

        /* ── Base ──────────────────────────────────────────────────── */
        *, *::before, *::after {
          box-sizing: border-box;
        }

        html {
          background: var(--bg-base);
        }

        body {
          font-family: 'Sora', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
          font-size: 12.5pt;
          font-weight: 400;
          line-height: 1.75;
          color: var(--text-primary);
          background: var(--bg-base);
          padding: 1.6cm 1.4cm 2cm;
          margin: 0;
          word-wrap: break-word;
          overflow-wrap: break-word;
          -webkit-print-color-adjust: exact;
          print-color-adjust: exact;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
          text-rendering: optimizeLegibility;
        }

        /* ── Headings ──────────────────────────────────────────────── */
        h1, h2, h3, h4, h5, h6 {
          font-family: 'Sora', sans-serif;
          page-break-after: avoid;
          letter-spacing: -0.02em;
        }

        h1 {
          font-size: 28pt;
          font-weight: 800;
          line-height: 1.2;
          margin: 0 0 0.15em 0;
          padding: 0;
          color: #ffffff;
          /* Subtle gradient text */
          background: linear-gradient(135deg, #ffffff 0%, #c8d8ff 60%, #9d7fe8 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        /* Decorative rule below H1 */
        h1::after {
          content: '';
          display: block;
          height: 3px;
          width: 64px;
          margin: 0.45em 0 0.6em 0;
          background: var(--gradient-rule);
          border-radius: 2px;
        }

        h2 {
          font-size: 17pt;
          font-weight: 700;
          line-height: 1.3;
          margin: 1.4em 0 0.55em 0;
          padding: 0.45em 0.85em 0.45em 1em;
          color: #ffffff;
          background: var(--gradient-h2);
          border: 1px solid var(--border-medium);
          border-left: 3px solid var(--accent-blue);
          border-radius: var(--radius-md);
          box-shadow: var(--shadow-md), var(--shadow-glow);
          position: relative;
          overflow: hidden;
        }

        /* Subtle shimmer stripe on h2 */
        h2::before {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(105deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.01) 100%);
          pointer-events: none;
        }

        h3 {
          font-size: 14.5pt;
          font-weight: 600;
          line-height: 1.35;
          margin: 1.1em 0 0.45em 0;
          color: var(--accent-blue);
          border-bottom: 1.5px solid var(--border-medium);
          padding-bottom: 0.28em;
          display: flex;
          align-items: center;
          gap: 0.4em;
        }

        h3::before {
          content: '▸';
          color: var(--accent-purple);
          font-size: 0.7em;
          flex-shrink: 0;
          opacity: 0.85;
        }

        h4 {
          font-size: 12.5pt;
          font-weight: 600;
          margin: 0.9em 0 0.35em 0;
          color: var(--accent-purple);
          letter-spacing: 0.02em;
        }

        h5 {
          font-size: 11.5pt;
          font-weight: 600;
          margin: 0.7em 0 0.3em 0;
          color: var(--text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.08em;
          font-size: 9.5pt;
        }

        h6 {
          font-size: 9pt;
          font-weight: 600;
          margin: 0.6em 0 0.25em 0;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.1em;
        }

        /* ── Paragraphs ────────────────────────────────────────────── */
        p {
          margin: 0.65em 0;
          text-align: left;
          orphans: 3;
          widows: 3;
          color: var(--text-primary);
        }

        /* ── Inline Emphasis ───────────────────────────────────────── */
        strong {
          color: var(--accent-amber);
          font-weight: 700;
        }

        em {
          color: var(--accent-purple);
          font-style: italic;
          font-family: 'Lora', Georgia, serif;
        }

        strong em, em strong {
          color: var(--accent-rose);
          font-style: italic;
        }

        /* ── Links ─────────────────────────────────────────────────── */
        a {
          color: var(--accent-blue);
          text-decoration: none;
          border-bottom: 1px solid rgba(91,141,238,0.35);
          transition: color 0.15s, border-color 0.15s;
        }

        a:hover {
          color: #a0c0ff;
          border-color: rgba(160,192,255,0.6);
        }

        /* ── Horizontal Rule ───────────────────────────────────────── */
        hr {
          border: none;
          height: 1px;
          background: var(--gradient-rule);
          margin: 2em 0;
          opacity: 0.7;
        }

        /* ── Blockquotes ───────────────────────────────────────────── */
        blockquote {
          border-left: 3px solid var(--accent-blue);
          margin: 1.2em 0;
          padding: 0.9em 1.2em 0.9em 1.4em;
          background: var(--bg-elevated);
          border-radius: 0 var(--radius-md) var(--radius-md) 0;
          color: var(--text-secondary);
          font-style: normal;
          box-shadow: var(--shadow-sm);
          position: relative;
        }

        blockquote::before {
          content: '"';
          position: absolute;
          top: -0.1em;
          left: 0.5em;
          font-family: 'Lora', Georgia, serif;
          font-size: 3em;
          color: var(--accent-blue);
          opacity: 0.2;
          line-height: 1;
          pointer-events: none;
        }

        blockquote strong {
          color: var(--accent-amber);
        }

        blockquote p {
          margin: 0.3em 0;
          color: var(--text-secondary);
        }

        /* ── Code ──────────────────────────────────────────────────── */
        code {
          font-family: 'JetBrains Mono', 'SF Mono', Monaco, 'Cascadia Code', Consolas, monospace;
          font-size: 10.5pt;
          background: var(--bg-elevated);
          color: var(--accent-cyan);
          padding: 0.15em 0.45em;
          border-radius: var(--radius-sm);
          border: 1px solid var(--border-subtle);
          font-variant-ligatures: none;
        }

        pre {
          background: var(--bg-surface);
          border: 1px solid var(--border-medium);
          border-top: 2px solid var(--accent-blue);
          border-radius: var(--radius-md);
          padding: 1.1em 1.2em;
          overflow-x: auto;
          font-size: 10pt;
          line-height: 1.65;
          page-break-inside: avoid;
          margin: 1.1em 0;
          box-shadow: var(--shadow-md);
          position: relative;
        }

        /* Faux "window dots" decoration */
        pre::before {
          content: '● ● ●';
          display: block;
          font-size: 7pt;
          color: var(--border-medium);
          letter-spacing: 0.3em;
          margin-bottom: 0.8em;
          opacity: 0.7;
        }

        pre code {
          background: transparent;
          padding: 0;
          border: none;
          color: var(--text-primary);
          font-size: inherit;
        }

        /* ── Tables ────────────────────────────────────────────────── */
        table {
          border-collapse: collapse;
          width: 100%;
          margin: 1.3em 0;
          font-size: 11pt;
          page-break-inside: avoid;
          background: var(--bg-surface);
          border: 1px solid var(--border-medium);
          border-radius: var(--radius-md);
          overflow: hidden;
          box-shadow: var(--shadow-md);
        }

        th, td {
          padding: 10px 15px;
          text-align: left;
          border: 1px solid var(--border-subtle);
        }

        th {
          background: var(--gradient-th);
          font-weight: 700;
          color: var(--accent-amber);
          text-transform: uppercase;
          font-size: 9pt;
          letter-spacing: 0.07em;
          border-bottom: 2px solid var(--accent-blue);
        }

        td {
          background: var(--bg-surface);
          color: var(--text-primary);
        }

        /* Zebra striping */
        tr:nth-child(even) td {
          background: var(--bg-elevated);
        }

        tr:hover td {
          background: var(--bg-highlight);
        }

        /* ── Lists ─────────────────────────────────────────────────── */
        ul, ol {
          margin: 0.65em 0;
          padding-left: 1.8em;
        }

        ul {
          list-style: none;
        }

        ul li {
          position: relative;
          margin: 0.4em 0;
          padding-left: 0.2em;
        }

        ul li::before {
          content: '◆';
          position: absolute;
          left: -1.3em;
          color: var(--accent-blue);
          font-size: 0.5em;
          top: 0.52em;
          opacity: 0.85;
        }

        ul ul li::before {
          content: '◇';
          color: var(--accent-purple);
          opacity: 0.7;
        }

        ul ul ul li::before {
          content: '·';
          color: var(--text-muted);
          font-size: 1em;
          top: 0.3em;
        }

        ol {
          list-style: none;
          counter-reset: ol-counter;
        }

        ol li {
          counter-increment: ol-counter;
          position: relative;
          margin: 0.4em 0;
          padding-left: 0.2em;
        }

        ol li::before {
          content: counter(ol-counter);
          position: absolute;
          left: -1.8em;
          width: 1.4em;
          text-align: center;
          background: var(--accent-blue-lo);
          color: var(--accent-blue);
          font-size: 8.5pt;
          font-weight: 700;
          font-family: 'Sora', sans-serif;
          border-radius: var(--radius-sm);
          padding: 0.05em 0;
          top: 0.22em;
          border: 1px solid rgba(91,141,238,0.25);
        }

        li > p {
          margin: 0.2em 0;
        }

        /* ── Images ────────────────────────────────────────────────── */
        img {
          max-width: 100%;
          height: auto;
          display: block;
          margin: 1.4em auto;
          page-break-inside: avoid;
          border-radius: var(--radius-md);
          box-shadow: var(--shadow-lg), 0 0 0 1px var(--border-subtle);
        }

        /* ── SVG ───────────────────────────────────────────────────── */
        svg {
          max-width: 100%;
          height: auto;
          page-break-inside: avoid;
        }

        /* ── Keyboard / Mark / Del ─────────────────────────────────── */
        kbd {
          font-family: 'JetBrains Mono', monospace;
          font-size: 9.5pt;
          background: var(--bg-elevated);
          color: var(--text-primary);
          padding: 0.1em 0.5em;
          border-radius: 4px;
          border: 1px solid var(--border-medium);
          border-bottom-width: 2px;
          box-shadow: 0 1px 0 var(--border-medium);
        }

        mark {
          background: rgba(245,166,35,0.22);
          color: var(--accent-amber);
          padding: 0.05em 0.3em;
          border-radius: 3px;
        }

        del {
          color: var(--text-muted);
          text-decoration: line-through;
          opacity: 0.6;
        }

        /* ── Print Optimizations ───────────────────────────────────── */
        @media print {
          body {
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }

          h1, h2, h3, h4, h5, h6 {
            page-break-after: avoid;
          }

          p, li {
            orphans: 3;
            widows: 3;
          }

          pre, blockquote, table, img {
            page-break-inside: avoid;
          }

          a {
            border-bottom: none;
          }

          a[href]::after {
            content: ' (' attr(href) ')';
            font-size: 9pt;
            color: var(--text-muted);
            font-style: italic;
          }

          a[href^="#"]::after,
          a[href^="javascript:"]::after {
            content: '';
          }
        }
        """

        # Wrap HTML with proper structure
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>{mobile_css}</style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert HTML to PDF using Playwright (highest quality)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Set content with proper base URL for relative image paths
            page.set_content(full_html, wait_until="networkidle")

            # Generate PDF with mobile-friendly settings
            page.pdf(
                path=str(output_path),
                format="A4",
                print_background=True,
                margin={
                    "top": "1.5cm",
                    "right": "1cm",
                    "bottom": "1.5cm",
                    "left": "1cm",
                }
            )

            browser.close()

        return True, f"Successfully converted {markdown_path.name} to {output_path.name}"

    except Exception as e:
        logger.error(f"Failed to convert markdown to PDF: {e}")
        return False, f"Conversion failed: {str(e)}"


@tool("markdown_to_pdf", parse_docstring=True)
def markdown_to_pdf_tool(
        runtime: ToolRuntime[ContextT, ThreadState],
        markdown_file: str,
        output_filename: str | None = None,
        tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """Convert a markdown file to a mobile-friendly PDF with charts and images.

    This tool takes a markdown file and converts it to a well-formatted PDF optimized
    for mobile viewing. It properly handles:
    - Images (embedded or linked)
    - Code blocks with syntax highlighting
    - Tables and charts
    - Lists, blockquotes, and formatting
    - Mobile-friendly layout (readable font sizes, proper margins)

    The output PDF will be saved to `/mnt/user-data/outputs` and automatically presented
    to the user.

    Args:
        markdown_file: Path to the markdown file to convert. Can be absolute or relative to workspace.
        output_filename: Optional custom name for the output PDF file (without extension).
                        If not provided, uses the markdown filename with .pdf extension.

    Returns:
        Command with the result message and artifact path.

    Example:
        markdown_to_pdf(
            markdown_file="/mnt/user-data/workspace/report.md",
            output_filename="mobile_report"
        )
    """
    if runtime.state is None:
        return Command(
            update={"messages": [ToolMessage("Error: Thread runtime state not available", tool_call_id=tool_call_id)]}
        )

    thread_id = runtime.context.get("thread_id") if runtime.context else None
    if not thread_id:
        return Command(
            update={"messages": [ToolMessage("Error: Thread ID not available", tool_call_id=tool_call_id)]}
        )

    thread_data = runtime.state.get("thread_data") or {}
    workspace_path = thread_data.get("workspace_path")
    outputs_path = thread_data.get("outputs_path")

    if not workspace_path or not outputs_path:
        return Command(
            update={"messages": [ToolMessage("Error: Thread paths not available", tool_call_id=tool_call_id)]}
        )

    # Resolve input markdown file path
    md_path_str = markdown_file.lstrip("/")
    if md_path_str.startswith("mnt/user-data/workspace/"):
        # Virtual path - resolve to actual path
        relative = md_path_str.replace("mnt/user-data/workspace/", "")
        md_path = Path(workspace_path) / relative
    elif md_path_str.startswith("mnt/user-data/outputs/"):
        # Virtual path - resolve to actual path
        relative = md_path_str.replace("mnt/user-data/outputs/", "")
        md_path = Path(outputs_path) / relative
    else:
        # Assume relative to workspace
        md_path = Path(workspace_path) / md_path_str

    md_path = md_path.resolve()

    # Validate input file exists
    if not md_path.exists():
        return Command(
            update={"messages": [
                ToolMessage(f"Error: Markdown file not found: {markdown_file}", tool_call_id=tool_call_id)]}
        )

    if not md_path.is_file():
        return Command(
            update={"messages": [ToolMessage(f"Error: Path is not a file: {markdown_file}", tool_call_id=tool_call_id)]}
        )

    # Determine output filename
    if output_filename:
        pdf_filename = output_filename if output_filename.endswith(".pdf") else f"{output_filename}.pdf"
    else:
        pdf_filename = md_path.stem + ".pdf"

    output_path = Path(outputs_path) / pdf_filename

    # Convert directly - Playwright works the same in local and containerized environments
    success, message = _convert_markdown_to_pdf(md_path, output_path, mobile_friendly=True)

    if not success:
        return Command(
            update={"messages": [ToolMessage(f"Error: {message}", tool_call_id=tool_call_id)]}
        )

    # Add artifact for user viewing
    virtual_path = f"/mnt/user-data/outputs/{pdf_filename}"
    return Command(
        update={
            "artifacts": [virtual_path],
            "messages": [ToolMessage(f"✓ {message}\n\nOutput: {virtual_path}", tool_call_id=tool_call_id)],
        }
    )
