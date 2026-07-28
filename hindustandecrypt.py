import os
import re
import base64
import zlib
import gzip
import urllib.parse
from pathlib import Path
from time import sleep

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box
from rich.text import Text
import pyfiglet

console = Console()
OUTPUT_PREFIX = "unprotected_"

def decode_hex_and_unicode(text: str) -> str:
    """Decodes \\xXX hex escapes and \\uXXXX unicode escapes."""
    def replace_hex(match):
        try:
            return bytes.fromhex(match.group(1)).decode('utf-8', errors='ignore')
        except Exception:
            return match.group(0)

    def replace_unicode(match):
        try:
            return chr(int(match.group(1), 16))
        except Exception:
            return match.group(0)

    text = re.sub(r'\\x([0-9a-fA-F]{2})', replace_hex, text)
    text = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
    return text

def decode_url_encoding(text: str) -> str:
    """Decodes %XX URL-encoded strings."""
    try:
        return urllib.parse.unquote(text)
    except Exception:
        return text

def extract_and_decode_payloads(content: str) -> tuple[str, bool]:
    """
    Extracts and recursively decodes Base64, Zlib, Deflate, Gzip, Hex, and URL payloads.
    """
    modified = False
    current_content = content

    # 1. Base64 + Compression Payload Detection
    b64_matches = re.findall(r'["\']([A-Za-z0-9+/=]{32,})["\']', current_content)
    for match in b64_matches:
        try:
            raw_bytes = base64.b64decode(match)
            
            # Try Zlib Decompression
            try:
                decompressed = zlib.decompress(raw_bytes).decode('utf-8', errors='ignore')
                if len(decompressed) > 10:
                    current_content = current_content.replace(match, decompressed)
                    modified = True
                    continue
            except Exception:
                pass

            # Try Raw Deflate (-15 wbits)
            try:
                decompressed = zlib.decompress(raw_bytes, -zlib.MAX_WBITS).decode('utf-8', errors='ignore')
                if len(decompressed) > 10:
                    current_content = current_content.replace(match, decompressed)
                    modified = True
                    continue
            except Exception:
                pass

            # Try Gzip Decompression
            try:
                decompressed = gzip.decompress(raw_bytes).decode('utf-8', errors='ignore')
                if len(decompressed) > 10:
                    current_content = current_content.replace(match, decompressed)
                    modified = True
                    continue
            except Exception:
                pass

            # Direct Base64 Plaintext String
            if len(raw_bytes) > 15 and all(32 <= b <= 126 or b in (9, 10, 13) for b in raw_bytes):
                plain_str = raw_bytes.decode('utf-8', errors='ignore')
                if any(k in plain_str for k in ["<", "function", "var ", "const ", "class ", "import ", "<?php"]):
                    current_content = current_content.replace(match, plain_str)
                    modified = True

        except Exception:
            pass

    # 2. Hex and Unicode Escapes
    new_content = decode_hex_and_unicode(current_content)
    if new_content != current_content:
        current_content = new_content
        modified = True

    # 3. URL Encoding Pass
    if "%" in current_content:
        new_content = decode_url_encoding(current_content)
        if new_content != current_content:
            current_content = new_content
            modified = True

    return current_content, modified

def universal_deobfuscator(content: str) -> str:
    """
    Multi-pass recursive engine that strips wrapper protections and unpacks source code.
    """
    max_passes = 15
    current_code = content

    for _ in range(max_passes):
        current_code, is_modified = extract_and_decode_payloads(current_code)
        if not is_modified:
            break

    # If full HTML was embedded inside JS wrappers, extract the core document
    if "document.write" in content or "document.open" in content:
        html_doc = re.search(r'(<!DOCTYPE html>.*?</html>|<html.*?>.*?</html>)', current_code, re.DOTALL | re.IGNORECASE)
        if html_doc:
            current_code = html_doc.group(1)

    return current_code

def get_target_files():
    """Scans working directory for obfuscated source code files."""
    current_folder = Path(".")
    extensions = ['.html', '.js', '.php', '.css', '.java', '.dex', '.txt', '.json']
    files = [
        f for f in current_folder.glob("*.*")
        if f.suffix.lower() in extensions and not f.name.startswith(OUTPUT_PREFIX)
    ]
    return sorted(files, key=lambda x: x.name)

def display_banner():
    try:
        banner_text = pyfiglet.figlet_format("HINDUSTAN", font="small")
    except Exception:
        banner_text = "=== HINDUSTAN ==="
        
    colored_banner = Text(banner_text, style="bold cyan")
    
    console.print(Panel(
        colored_banner, 
        box=box.DOUBLE, 
        border_style="cyan",
        title="[bold red] Universal De-Obfuscator v3.0 [/bold red]",
        subtitle="[bold yellow] Developer: @Rolexconfigyt [/bold yellow]"
    ))
    
    desc = Text("⚡ High-Level Multi-Layer Unpacker & Code Restorer\nSupports HTML, JS, PHP, Java & Asset Decryption", style="bold green", justify="center")
    console.print(Panel(desc, box=box.ROUNDED, border_style="green"))
    console.print()

def format_size(size: float) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def display_files_table(files) -> bool:
    if not files:
        console.print(Panel(
            "[red]⚠️ No supported source files found in this directory![/red]\n"
            "[yellow]Please place your .html, .js, .php, .java, or .dex files here and retry.[/yellow]", 
            box=box.HEAVY, 
            border_style="red"
        ))
        return False
    
    table = Table(title="[bold yellow]📄 Available Protected / Obfuscated Files[/bold yellow]", box=box.SIMPLE_HEAVY, border_style="cyan")
    table.add_column("ID", style="bold red", justify="center")
    table.add_column("Filename", style="bold green")
    table.add_column("Size", style="bold yellow", justify="right")
    
    for idx, file in enumerate(files, start=1):
        size = format_size(file.stat().st_size)
        table.add_row(f"[{idx}]", file.name, size)
    
    console.print(table)
    console.print()
    return True

def process_deobfuscation(selected_file: Path) -> str | None:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]🔍 Analyzing File Structure...", total=100)
        
        try:
            content = selected_file.read_text(encoding='utf-8', errors='ignore')
            progress.update(task, advance=20, description="[yellow]📦 Unpacking Multi-Pass Protection...")
            sleep(0.4)
            
            restored_code = universal_deobfuscator(content)
            progress.update(task, advance=50, description="[magenta]🔓 Reconstructing Original Source Code...")
            sleep(0.4)
            
            output_name = OUTPUT_PREFIX + selected_file.name
            Path(output_name).write_text(restored_code, encoding='utf-8')
            progress.update(task, advance=30, description="[green]✅ Source Code Successfully Restored!")
            sleep(0.3)
            
            return output_name
            
        except Exception as e:
            progress.update(task, description=f"[red]❌ De-obfuscation Failed: {e}[/red]")
            sleep(1)
            return None

def display_result(original_file: Path, output_name: str, original_size: float, new_size: float):
    result_table = Table(box=box.SIMPLE, show_header=False)
    result_table.add_column("Property", style="bold cyan")
    result_table.add_column("Value", style="bold yellow")
    
    result_table.add_row("📄 Obfuscated File:", original_file.name)
    result_table.add_row("💾 Restored File  :", f"[bold green]{output_name}[/bold green]")
    result_table.add_row("📏 Protected Size :", format_size(original_size))
    result_table.add_row("🔓 Original Size  :", format_size(new_size))
    
    console.print(Panel(
        result_table,
        title="✨ [bold green]De-obfuscation Completed[/bold green] ✨",
        box=box.HEAVY,
        border_style="green",
        expand=False
    ))
    console.print(f"[bold cyan]📁 Saved Output Location:[/bold cyan] [yellow]{Path(output_name).absolute()}[/yellow]\n")

def main():
    console.clear()
    display_banner()
    
    files = get_target_files()
    if not display_files_table(files):
        return
    
    while True:
        try:
            choice = IntPrompt.ask(
                "[bold cyan]📌 Enter the ID of the file to restore[/bold cyan]",
                choices=[str(i) for i in range(1, len(files) + 1)],
                show_choices=False
            )
            if 1 <= choice <= len(files):
                selected_file = files[choice - 1]
                break
        except Exception:
            console.print("[red]❌ Invalid ID choice! Please enter a valid number.[/red]")
    
    console.print(f"\n[bold green]➜ Selected File:[/bold green] [cyan]{selected_file.name}[/cyan]")
    
    confirm = Prompt.ask("\n[bold yellow]⚡ Start Advanced De-Obfuscation?[/bold yellow]", choices=["y", "n"], default="y")
    if confirm.lower() != 'y':
        console.print("[yellow]❌ Operation cancelled.[/yellow]")
        return
    
    original_size = selected_file.stat().st_size
    output_name = process_deobfuscation(selected_file)
    
    if output_name:
        new_size = Path(output_name).stat().st_size
        console.print()
        display_result(selected_file, output_name, original_size, new_size)
    else:
        console.print(Panel("[red]❌ Unable to decode. File may use custom native binary encryption.[/red]", box=box.HEAVY, border_style="red"))
    
    another = Prompt.ask("[bold cyan]🔄 Process another file?[/bold cyan]", choices=["y", "n"], default="n")
    if another.lower() == 'y':
        main()
    else:
        console.print("\n[bold green]🙏 Thanks for using Hindustan Hack! Stay Secure. 🔒[/bold green]\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]👋 Exited by user. Goodbye![/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
