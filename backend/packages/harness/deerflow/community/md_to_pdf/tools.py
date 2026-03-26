"""
Markdown to Mobile-Friendly PDF Tool - Convert markdown files with charts and images to PDF.

Uses Playwright with Chromium for highest quality rendering.
"""

import logging
from pathlib import Path
from typing import Annotated

from langchain.tools import InjectedToolCallId, ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.typing import ContextT

from deerflow.agents.thread_state import ThreadState

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

        # Mobile-friendly CSS styling with print optimizations
        mobile_css = """
        @page {
            size: A4;
            margin: 1.5cm 1cm;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            font-size: 14pt;
            line-height: 1.6;
            color: #333;
            max-width: 100%;
            margin: 0 auto;
            word-wrap: break-word;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }
        h1 {
            font-size: 24pt;
            font-weight: 600;
            margin: 0.8em 0 0.5em 0;
            page-break-after: avoid;
            color: #1a1a1a;
        }
        h2 {
            font-size: 20pt;
            font-weight: 600;
            margin: 0.8em 0 0.4em 0;
            page-break-after: avoid;
            color: #2a2a2a;
        }
        h3 {
            font-size: 16pt;
            font-weight: 600;
            margin: 0.6em 0 0.3em 0;
            page-break-after: avoid;
            color: #3a3a3a;
        }
        h4, h5, h6 {
            font-size: 14pt;
            font-weight: 600;
            margin: 0.5em 0 0.2em 0;
            page-break-after: avoid;
        }
        p {
            margin: 0.5em 0;
            text-align: left;
            orphans: 3;
            widows: 3;
        }
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em auto;
            page-break-inside: avoid;
        }
        pre {
            background-color: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
            font-size: 11pt;
            line-height: 1.45;
            page-break-inside: avoid;
            margin: 1em 0;
        }
        code {
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            font-size: 85%;
            background-color: rgba(175,184,193,0.2);
            padding: 0.2em 0.4em;
            border-radius: 3px;
        }
        pre code {
            background-color: transparent;
            padding: 0;
            font-size: 11pt;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
            font-size: 12pt;
            page-break-inside: avoid;
        }
        th, td {
            border: 1px solid #d0d7de;
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background-color: #f6f8fa;
            font-weight: 600;
            color: #24292f;
        }
        tr:nth-child(even) {
            background-color: #f6f8fa;
        }
        ul, ol {
            margin: 0.5em 0;
            padding-left: 2em;
        }
        li {
            margin: 0.3em 0;
        }
        blockquote {
            border-left: 4px solid #d0d7de;
            margin: 1em 0;
            padding: 0 1em;
            color: #57606a;
        }
        a {
            color: #0969da;
            text-decoration: none;
        }
        hr {
            border: none;
            border-top: 1px solid #d0d7de;
            margin: 1.5em 0;
        }
        /* Chart and SVG support */
        svg {
            max-width: 100%;
            height: auto;
            page-break-inside: avoid;
        }
        /* Print optimizations */
        @media print {
            body {
                background: white;
            }
            a {
                text-decoration: underline;
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

    sandbox = runtime.state.get("sandbox")
    if not sandbox:
        return Command(
            update={"messages": [ToolMessage("Error: Sandbox not available", tool_call_id=tool_call_id)]}
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
            update={"messages": [ToolMessage(f"Error: Markdown file not found: {markdown_file}", tool_call_id=tool_call_id)]}
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
