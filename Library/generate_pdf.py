#!/usr/bin/env python3
"""Generate PDF from markdown documentation files."""

import os
from pathlib import Path
from datetime import datetime

def collect_markdown_files(base_dir: Path) -> list[Path]:
    """Collect all markdown files in order."""
    md_files = []
    
    # Order matters for compilation
    priority_order = [
        "00-master-index.md",
        "architecture/00-index.md",
        "architecture/00-system-overview.md",
        "backend/api/00-api-overview.md",
        "flows/data/00-data-pipeline.md",
        "research/00-optimization-research.md",
    ]
    
    # Add priority files first
    for priority_file in priority_order:
        file_path = base_dir / priority_file
        if file_path.exists():
            md_files.append(file_path)
    
    # Add remaining files by directory
    for subdir in ["architecture", "backend", "frontend", "infrastructure", "flows", "specifications", "research", "inventions", "mdos", "best-practices"]:
        dir_path = base_dir / subdir
        if dir_path.exists():
            for md_file in sorted(dir_path.rglob("*.md")):
                if md_file not in md_files:
                    md_files.append(md_file)
    
    return md_files

def create_compiled_markdown(md_files: list[Path], output_path: Path):
    """Compile all markdown files into one with page breaks."""
    with open(output_path, 'w') as out_f:
        out_f.write("# Momento Core - Complete Documentation Library\n\n")
        out_f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        out_f.write("---\n\n")
        out_f.write("\\newpage\n\n")
        
        for md_file in md_files:
            try:
                with open(md_file, 'r') as in_f:
                    content = in_f.read()
                    # Add relative path as comment for reference
                    rel_path = md_file.relative_to(output_path.parent)
                    out_f.write(f"\n<!-- Source: {rel_path} -->\n\n")
                    out_f.write(content)
                    out_f.write("\n\n\\newpage\n\n")
            except Exception as e:
                print(f"Warning: Could not read {md_file}: {e}")
    
    print(f"Compiled {len(md_files)} files into {output_path}")

def main():
    library_dir = Path(__file__).parent
    compiled_md = library_dir / "complete_documentation.md"
    
    md_files = collect_markdown_files(library_dir)
    print(f"Found {len(md_files)} markdown files to compile")
    
    create_compiled_markdown(md_files, compiled_md)
    
    print("\n=== Compilation Complete ===")
    print(f"Output: {compiled_md}")
    print("\nTo convert to PDF, use one of these methods:")
    print("1. pandoc complete_documentation.md -o momento_documentation.pdf --pdf-engine=xelatex --toc")
    print("2. Use online converter: https://markdowntopdf.com")
    print("3. Print to PDF from browser: Open .md file in browser, print to PDF")
    print("\nFile size:", compiled_md.stat().st_size / 1024 / 1024, "MB")

if __name__ == "__main__":
    main()
