#!/usr/bin/env python3

"""
Markdown to HTML/PDF converter
Usage: python main.py input.md [-o output.html] [--pdf]
"""

import argparse
import sys
from pathlib import Path
import markdown
from markdown.extensions import fenced_code, tables, toc


def convert_to_html(md_content, title="Document"):
    md = markdown.Markdown(extensions=[
        'fenced_code',
        'tables',
        'toc',
        'nl2br'
    ])
    content = md.convert(md_content)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
            color: #333;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        pre code {{
            background: none;
            padding: 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f4f4f4;
        }}
        blockquote {{
            border-left: 4px solid #ddd;
            padding-left: 20px;
            margin-left: 0;
            color: #666;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
    </style>
</head>
<body>
    {content}
</body>
</html>"""
    
    return html


def convert_to_pdf(html_content, output_path):
    try:
        from xhtml2pdf import pisa
        
        with open(output_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
        
        return not pisa_status.err
    except ImportError:
        print("Error: xhtml2pdf not installed. Install with: pip install xhtml2pdf", 
                file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error creating PDF: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Convert Markdown files to HTML or PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  md2doc README.md                    # Convert to HTML (README.html)
  md2doc README.md -o docs/out.html   # Specify output path
  md2doc README.md --pdf              # Convert to PDF (README.pdf)
  md2doc README.md -o doc.pdf --pdf   # Specify PDF output path
        """
    )
    
    parser.add_argument('input', type=Path, help='Input Markdown file')
    parser.add_argument('-o', '--output', type=Path, help='Output file path')
    parser.add_argument('--pdf', action='store_true', help='Convert to PDF instead of HTML')
    parser.add_argument('-t', '--title', help='Document title (default: filename)')
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    
    if not args.input.suffix.lower() in ['.md', '.markdown']:
        print("Warning: Input file doesn't have .md extension", file=sys.stderr)
    
    try:
        md_content = args.input.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    if args.output:
        output_path = args.output
    else:
        suffix = '.pdf' if args.pdf else '.html'
        output_path = args.input.with_suffix(suffix)
    
    title = args.title or args.input.stem
    
    html_content = convert_to_html(md_content, title)
    
    if args.pdf:
        if convert_to_pdf(html_content, output_path):
            print(f"PDF saved to: {output_path}")
        else:
            sys.exit(1)
    else:
        try:
            output_path.write_text(html_content, encoding='utf-8')
            print(f"HTML saved to: {output_path}")
        except Exception as e:
            print(f"Error writing file: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()