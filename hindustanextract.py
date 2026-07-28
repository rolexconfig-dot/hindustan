import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse, urljoin
from pathlib import Path
import zipfile
import shutil
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box
from rich.text import Text
import pyfiglet

console = Console()

# Automatic Storage Settings (MT Manager Auto Path)
FOLDER_NAME = "Hindustan_Hack_Projects"
CUSTOM_PREFIX = "Hindustan_Hack_"

def get_robust_session():
    """कनेक्शन को मजबूत बनाने और नेटवर्क एरर से बचने के लिए सेशन सेट-अप"""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=30)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def display_banner():
    # Termux/Mobile स्क्रीन पर टेक्स्ट फटने से बचाने के लिए 'small' फ़ॉन्ट
    try:
        banner_text = pyfiglet.figlet_format("HINDUSTAN", font="small")
    except Exception:
        banner_text = "=== HINDUSTAN ==="
        
    colored_banner = Text(banner_text, style="bold cyan")
    
    console.print(Panel(
        colored_banner, 
        box=box.DOUBLE, 
        border_style="cyan",
        title="[bold red] Extractor v1.0 [/bold red]",
        subtitle="[bold yellow] Developer: @Rolexconfigyt [/bold yellow]"
    ))
    
    desc = Text("🚀 Advanced Direct Source Code & Asset Scraper (Up to 10GB Engine)\nAuto-Saves Original Package directly into MT Manager!", style="bold green", justify="center")
    console.print(Panel(desc, box=box.ROUNDED, border_style="green"))
    console.print()

def get_clean_site_name(url):
    domain = urlparse(url).netloc
    if not domain:
        domain = "site"
    domain = domain.replace("www.", "").split(".")[0]
    return domain.capitalize()

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

# Memory-Safe 4MB Chunk Streaming for Heavy Assets (Videos, High-Res Images)
def download_heavy_asset(asset_info, headers, output_folder, session):
    url, local_path = asset_info
    try:
        full_path = output_folder / local_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with session.get(url, headers=headers, timeout=60, stream=True) as res:
            if res.status_code == 200:
                with open(full_path, 'wb') as f:
                    for chunk in res.iter_content(chunk_size=4 * 1024 * 1024):  # 4MB Chunks
                        if chunk:
                            f.write(chunk)
                return True
    except Exception:
        pass
    return False

def extract_direct_source(target_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    session = get_robust_session()
    site_name = get_clean_site_name(target_url)
    
    # Auto Directory Path Setup for MT Manager
    base_download_dir = Path("/sdcard/Download")
    if not base_download_dir.exists():
        base_download_dir = Path(".")
        
    hindustan_folder = base_download_dir / FOLDER_NAME
    hindustan_folder.mkdir(parents=True, exist_ok=True)

    zip_filename = f"{CUSTOM_PREFIX}{site_name}.zip"
    zip_path = hindustan_folder / zip_filename

    temp_dir = hindustan_folder / f"temp_{site_name}"
    assets_dir = temp_dir / "assets"
    temp_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]🌐 Connecting directly to {target_url}...[/cyan]")
    try:
        response = session.get(target_url, headers=headers, timeout=40)
        response.raise_for_status()
        raw_html = response.text
    except Exception as e:
        console.print(f"[bold red]❌ Connection Error:[/bold red] {e}")
        return None, 0

    # Asset Discovery using Regex
    asset_urls = re.findall(r'(?:href|src|action)=["\'](.*?)["\']', raw_html)
    
    download_queue = []
    seen = set()
    
    for link in asset_urls:
        if link.startswith("data:") or link.startswith("#") or link.startswith("javascript:"):
            continue
            
        full_url = urljoin(target_url, link)
        if full_url in seen:
            continue
        seen.add(full_url)
        
        parsed = urlparse(full_url)
        ext = Path(parsed.path).suffix
        if not ext or len(ext) > 5:
            ext = ".asset"
            
        filename = f"file_{len(download_queue) + 1}{ext}"
        relative_path = Path("assets") / filename
        
        download_queue.append((full_url, relative_path))
        raw_html = raw_html.replace(link, f"assets/{filename}")

    # Save Primary HTML Code
    (temp_dir / "index.html").write_text(raw_html, encoding='utf-8')

    # Multi-Threaded Engine for Heavy Downloading
    if download_queue:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"[yellow]📦 Extracting {len(download_queue)} Assets (Up to 10GB Capacity)...", total=len(download_queue))
            
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(download_heavy_asset, item, headers, temp_dir, session) for item in download_queue]
                for future in futures:
                    future.result()
                    progress.advance(task)

    # Creating ZIP Archive
    console.print("[green]⚡ Packaging extracted source into ZIP...[/green]")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(temp_dir)
                zipf.write(file_path, arcname)

    # Cleanup Temporary Folder
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass

    zip_size = zip_path.stat().st_size
    return str(zip_path), zip_size

def main():
    console.clear()
    display_banner()
    
    target_url = Prompt.ask("[bold green]🔗 Enter Target Website URL[/bold green]")
    
    if not target_url.startswith("http"):
        target_url = "https://" + target_url
        console.print(f"[dim]Auto-added https:// -> {target_url}[/dim]\n")
    
    console.print()
    zip_file, size = extract_direct_source(target_url)
    
    if zip_file:
        console.print(Panel(
            f"🎉 [bold green]FULL SOURCE CODE EXTRACTED SUCCESSFULLY![/bold green] 🎉\n\n"
            f"🎯 [bold cyan]Target URL:[/bold cyan] [yellow]{target_url}[/yellow]\n"
            f"📦 [bold cyan]Saved Package:[/bold cyan] [bold green]{Path(zip_file).name}[/bold green]\n"
            f"📏 [bold cyan]Package Size:[/bold cyan]  [bold yellow]{format_size(size)}[/bold yellow]\n\n"
            f"📂 [bold yellow]MT Manager Auto-Saved Path:[/bold yellow]\nOpen MT Manager ➔ Download ➔ [bold cyan]{FOLDER_NAME}[/bold cyan] ➔ [bold green]{Path(zip_file).name}[/bold green]",
            box=box.HEAVY,
            border_style="green",
            title="[bold green] ✨ HINDUSTAN EXTRACTOR RESULT ✨ [/bold green]"
        ))
    
    another = Prompt.ask("\n[bold cyan]🔄 Extract another website?[/bold cyan]", choices=["y", "n"], default="n")
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
