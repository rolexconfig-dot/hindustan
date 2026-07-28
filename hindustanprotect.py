import os
import base64
import zlib
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box
from rich.text import Text
import pyfiglet
from time import sleep

console = Console()
OUTPUT_PREFIX = "protected_"

def protect_html(html_code):
    compressed = zlib.compress(html_code.encode("utf-8"), level=9)
    encoded = base64.b64encode(compressed).decode()
    
    protected = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Protected by Hindustan Hack</title>
</head>
<body>
<script>
(function(){{
const data = "{encoded}";
async function decode(){{
    const binary = atob(data);
    const bytes = new Uint8Array(binary.length);
    for(let i = 0; i < binary.length; i++) {{
        bytes[i] = binary.charCodeAt(i);
    }}
    const stream = new DecompressionStream("deflate");
    const writer = stream.writable.getWriter();
    writer.write(bytes);
    writer.close();
    const buffer = await new Response(stream.readable).arrayBuffer();
    return new TextDecoder().decode(buffer);
}}
decode().then(html => {{
    document.open();
    document.write(html);
    document.close();
}});
}})();
</script>
</body>
</html>
"""
    return protected

def get_html_files():
    current_folder = Path(".")
    html_files = [
        f for f in current_folder.glob("*.html")
        if not f.name.startswith(OUTPUT_PREFIX)
    ]
    return sorted(html_files, key=lambda x: x.name)

def display_banner():
    # Use 'small' font so it doesn't break on Termux/Mobile screens
    try:
        banner_text = pyfiglet.figlet_format("HINDUSTAN", font="small")
    except:
        banner_text = "=== HINDUSTAN ==="
        
    colored_banner = Text(banner_text, style="bold cyan")
    
    console.print(Panel(
        colored_banner, 
        box=box.DOUBLE, 
        border_style="cyan",
        title="[bold red] v1.0 [/bold red]",
        subtitle="[bold yellow] Developer: @Rolexconfigyt  [/bold yellow]"
    ))
    
    desc = Text("🚀 Advanced HTML/CSS/JS Protection Tool\nSecure your source code from being stolen!", style="bold green", justify="center")
    console.print(Panel(desc, box=box.ROUNDED, border_style="green"))
    console.print()

def display_stats(html_files):
    total_files = len(html_files)
    total_size = sum(f.stat().st_size for f in html_files)
    
    stats_table = Table(box=box.MINIMAL_DOUBLE_HEAD, border_style="blue", show_header=False)
    stats_table.add_column("Metric", style="bold cyan")
    stats_table.add_column("Value", style="bold yellow")
    
    stats_table.add_row("📁 HTML Files Found :", str(total_files))
    stats_table.add_row("💾 Total Size       :", format_size(total_size))
    stats_table.add_row("🎯 Output Prefix    :", f"[red]{OUTPUT_PREFIX}[/red]")
    
    console.print(Panel(stats_table, title="📊 [bold magenta]Directory Statistics[/bold magenta]", box=box.ROUNDED, border_style="magenta", expand=False))
    console.print()

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def display_files_table(html_files):
    if not html_files:
        console.print(Panel("[red]⚠️ No unprotected HTML files found in this directory![/red]\n[yellow]Please paste your .html files here and try again.[/yellow]", box=box.HEAVY, border_style="red"))
        return False
    
    table = Table(title="[bold yellow]📄 Available HTML Files[/bold yellow]", box=box.SIMPLE_HEAVY, border_style="cyan")
    table.add_column("ID", style="bold red", justify="center")
    table.add_column("Filename", style="bold green")
    table.add_column("Size", style="bold yellow", justify="right")
    
    for idx, file in enumerate(html_files, start=1):
        size = format_size(file.stat().st_size)
        table.add_row(f"[{idx}]", file.name, size)
    
    console.print(table)
    console.print()
    return True

def show_file_preview(file_path):
    try:
        content = file_path.read_text(encoding='utf-8')
        preview_length = min(300, len(content)) # Shortened for mobile screens
        
        preview_text = content[:preview_length]
        if len(content) > preview_length:
            preview_text += "\n\n... [dim](Preview truncated for display)[/dim]"
            
        preview_panel = Panel(
            preview_text,
            title=f"📖 [bold magenta]Preview: {file_path.name}[/bold magenta]",
            border_style="magenta",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(preview_panel)
        console.print()
    except Exception as e:
        console.print(f"[red]❌ Error loading preview: {e}[/red]")

def protect_with_animation(selected_file):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]🔒 Initializing...", total=100)
        
        try:
            html_code = selected_file.read_text(encoding='utf-8')
            progress.update(task, advance=20, description="[yellow]📦 Reading Source Code...")
            sleep(0.4)
            
            protected_html = protect_html(html_code)
            progress.update(task, advance=50, description="[magenta]🔐 Compressing & Encoding Data...")
            sleep(0.6)
            
            output_name = OUTPUT_PREFIX + selected_file.stem + ".html"
            Path(output_name).write_text(protected_html, encoding='utf-8')
            progress.update(task, advance=30, description="[green]✅ Generating Protected File...")
            sleep(0.4)
            
            return output_name
            
        except Exception as e:
            progress.update(task, description=f"[red]❌ Error: {e}[/red]")
            sleep(1)
            return None

def display_protection_result(original_file, output_name, original_size, new_size):
    result_table = Table(box=box.SIMPLE, show_header=False)
    result_table.add_column("Property", style="bold cyan")
    result_table.add_column("Value", style="bold yellow")
    
    result_table.add_row("📄 Original File :", original_file.name)
    result_table.add_row("💾 Output File   :", f"[bold green]{output_name}[/bold green]")
    result_table.add_row("📏 Original Size :", format_size(original_size))
    result_table.add_row("🔒 Protected Size:", format_size(new_size))
    
    console.print(Panel(
        result_table,
        title="✨ [bold green]Protection Result[/bold green] ✨",
        box=box.HEAVY,
        border_style="green",
        expand=False
    ))
    console.print(f"[bold cyan]📁 Location:[/bold cyan] [yellow]{Path(output_name).absolute()}[/yellow]\n")

def main():
    console.clear()
    display_banner()
    
    html_files = get_html_files()
    if not display_files_table(html_files):
        return
    
    display_stats(html_files)
    
    while True:
        try:
            choice = IntPrompt.ask(
                "[bold cyan]📌 Enter the ID of the file to protect[/bold cyan]",
                choices=[str(i) for i in range(1, len(html_files) + 1)],
                show_choices=False
            )
            if 1 <= choice <= len(html_files):
                selected_file = html_files[choice - 1]
                break
        except Exception:
            console.print("[red]❌ Invalid ID! Please try again.[/red]")
    
    console.print(f"\n[bold green]➜ Selected:[/bold green] [cyan]{selected_file.name}[/cyan]")
    
    show_preview = Prompt.ask("[dim]Show file preview?[/dim]", choices=["y", "n"], default="n")
    if show_preview.lower() == 'y':
        console.print()
        show_file_preview(selected_file)
    
    confirm = Prompt.ask("\n[bold yellow]⚡ Ready to protect this file?[/bold yellow]", choices=["y", "n"], default="y")
    if confirm.lower() != 'y':
        console.print("[yellow]❌ Operation cancelled.[/yellow]")
        return
    
    original_size = selected_file.stat().st_size
    output_name = protect_with_animation(selected_file)
    
    if output_name:
        new_size = Path(output_name).stat().st_size
        console.print()
        display_protection_result(selected_file, output_name, original_size, new_size)
    else:
        console.print(Panel("[red]❌ Failed to protect the file![/red]", box=box.HEAVY, border_style="red"))
    
    another = Prompt.ask("[bold cyan]🔄 Protect another file?[/bold cyan]", choices=["y", "n"], default="n")
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
