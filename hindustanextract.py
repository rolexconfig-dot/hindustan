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

# Automatic Storage Settings (MT Manager / Termux / Storage Path)
FOLDER_NAME = "Hindustan_Hack_Projects"
CUSTOM_PREFIX = "Hindustan_Hack_"

def get_robust_session():
    """Builds an enterprise-grade resilient HTTP session with retry logic for heavy transfers."""
    session = requests.Session()
    retries = Retry(
        total=10,
        backoff_factor=1.5,
        status_forcelist=[500, 502, 503, 504, 429],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=50)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

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
        title="[bold red] Ultra Extractor v3.0 Pro [/bold red]",
        subtitle="[bold yellow] Developer: @Rolexconfigyt [/bold yellow]"
    ))
    
    desc = Text("🚀 High-Capacity (10GB+) Direct Source Code & Multi-Asset Scraper\nPro Asset Isolation Engine for CSS, JS, Media & Media Paths", style="bold green", justify="center")
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

def get_output_directory():
    """Selects target storage path safely, falling back gracefully if permission is denied."""
    sdcard_path = Path("/sdcard/Download") / FOLDER_NAME
    try:
        sdcard_path.mkdir(parents=True, exist_ok=True)
        test_file = sdcard_path / ".perm_test"
        test_file.touch()
        test_file.unlink()
        return sdcard_path
    except Exception:
        local_path = Path(".") / FOLDER_NAME
        local_path.mkdir(parents=True, exist_ok=True)
        return local_path

def categorize_extension(ext):
    ext = ext.lower().split('?')[0]
    if ext in ['.css']:
        return "css"
    elif ext in ['.js', '.mjs']:
        return "js"
    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp']:
        return "images"
    elif ext in ['.mp4', '.mkv', '.webm', '.avi', '.mov', '.mp3', '.wav', '.ogg']:
        return "videos"
    elif ext in ['.woff', '.woff2', '.ttf', '.eot', '.otf']:
        return "fonts"
    elif ext in ['.php', '.asp', '.aspx', '.jsp']:
        return "server_routes"
    else:
        return "assets"

def download_asset(asset_info, headers, output_folder, session):
    url, local_rel_path = asset_info
    try:
        full_path = output_folder / local_rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 8MB memory buffer for ultra-large media handling (up to 10GB+)
        with session.get(url, headers=headers, timeout=120, stream=True) as res:
            if res.status_code == 200:
                with open(full_path, 'wb') as f:
                    for chunk in res.iter_content(chunk_size=8 * 1024 * 1024):
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
    output_dir = get_output_directory()

    zip_filename = f"{CUSTOM_PREFIX}{site_name}.zip"
    zip_path = output_dir / zip_filename
    temp_dir = output_dir / f"temp_{site_name}"
    
    temp_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold cyan]🌐 Connecting directly to {target_url}...[/bold cyan]")
    try:
        response = session.get(target_url, headers=headers, timeout=60)
        response.raise_for_status()
        raw_html = response.text
    except Exception as e:
        console.print(f"[bold red]❌ Connection Error:[/bold red] {e}")
        return None, 0

    # Scan HTML tags and internal CSS url() calls
    html_links = re.findall(r'(?:href|src|action)=["\'](.*?)["\']', raw_html)
    css_links = re.findall(r'url\(["\']?(.*?)["\']?\)', raw_html)
    
    all_links = html_links + css_links
    download_queue = []
    seen = set()
    
    for count, link in enumerate(all_links, start=1):
        if link.startswith("data:") or link.startswith("#") or link.startswith("javascript:"):
            continue
            
        full_url = urljoin(target_url, link)
        if full_url in seen:
            continue
        seen.add(full_url)
        
        parsed_path = urlparse(full_url).path
        ext = Path(parsed_path).suffix
        if not ext or len(ext) > 6:
            ext = ".asset"
            
        subfolder = categorize_extension(ext)
        filename = f"file_{count}{ext.split('?')[0]}"
        relative_path = Path(subfolder) / filename
        
        download_queue.append((full_url, relative_path))
        raw_html = raw_html.replace(link, f"{subfolder}/{filename}")

    # Write reconstructed root HTML
    (temp_dir / "index.html").write_text(raw_html, encoding='utf-8')

    # Parallel Asset Downloader (High Concurrent Queue)
    if download_queue:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"[bold yellow]📦 Extracting {len(download_queue)} High-Speed Assets...", total=len(download_queue))
            
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(download_asset, item, headers, temp_dir, session) for item in download_queue]
                for future in futures:
                    future.result()
                    progress.advance(task)

    console.print("[bold green]⚡ Packaging extracted source into ZIP...[/bold green]")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(temp_dir)
                zipf.write(file_path, arcname)

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
            f"📂 [bold yellow]Output Location:[/bold yellow]\n[bold green]{Path(zip_file).absolute()}[/bold green]",
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
