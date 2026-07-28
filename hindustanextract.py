import os
import re
import requests
from urllib.parse import urlparse, urljoin
from pathlib import Path
import zipfile
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import shutil

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box
from rich.text import Text
import pyfiglet

console = Console()

# Automatic Directory Config
FOLDER_NAME = "Hindustan_Hack_Projects"
CUSTOM_PREFIX = "Hindustan_Hack_"

def display_banner():
    try:
        banner_text = pyfiglet.figlet_format("HINDUSTAN", font="small")
    except Exception:
        banner_text = "=== HINDUSTAN ==="
        
    colored_banner = Text(banner_text, style="bold orange3")
    
    console.print(Panel(
        colored_banner, 
        box=box.DOUBLE, 
        border_style="orange3",
        title="[bold red] Ultra Heavy Source Code Extractor (5GB+ Supported) [/bold red]",
        subtitle="[bold bright_yellow] Developer: @Rolexconfigyt [/bold bright_yellow]"
    ))
    
    desc = Text("🌐 Multi-Threaded Heavy Source Code & Media Extractor\nAuto-Creates Folder & Saves ZIP directly to Download / MT Manager!", style="bold cyan", justify="center")
    console.print(Panel(desc, box=box.ROUNDED, border_style="cyan"))
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

# High-Speed 4MB Chunk Memory-Safe Streaming Engine
def download_asset_stream(asset_info, headers, output_folder):
    url, local_path = asset_info
    try:
        full_path = output_folder / local_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with requests.get(url, headers=headers, timeout=90, stream=True) as res:
            if res.status_code == 200:
                with open(full_path, 'wb') as f:
                    for chunk in res.iter_content(chunk_size=4 * 1024 * 1024): # 4MB High-Speed Chunks
                        if chunk:
                            f.write(chunk)
                return True
    except Exception:
        pass
    return False

def extract_full_source(target_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    site_name = get_clean_site_name(target_url)
    
    # Fully Automatic Storage Creation (No Manual Folder Needed)
    base_download_dir = Path("/sdcard/Download")
    if not base_download_dir.exists():
        base_download_dir = Path(".")
        
    hindustan_folder = base_download_dir / FOLDER_NAME
    hindustan_folder.mkdir(parents=True, exist_ok=True)

    custom_zip_name = f"{CUSTOM_PREFIX}{site_name}.zip"
    zip_path = hindustan_folder / custom_zip_name

    temp_dir_name = f"temp_{site_name}"
    output_dir = hindustan_folder / temp_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        response = requests.get(target_url, headers=headers, timeout=40)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        console.print(f"[bold red]❌ Connection Error:[/bold red] {e}")
        return None, 0

    soup = BeautifulSoup(html_content, 'html.parser')
    assets_to_download = []
    
    # 1. CSS Assets
    for link in soup.find_all('link', rel=True):
        if 'stylesheet' in link.get('rel', []):
            href = link.get('href')
            if href:
                full_url = urljoin(target_url, href)
                asset_filename = f"css_{len(assets_to_download) + 1}.css"
                assets_to_download.append((full_url, Path("assets") / asset_filename))
                link['href'] = f"assets/{asset_filename}"

    # 2. JS Assets
    for script in soup.find_all('script', src=True):
        src = script.get('src')
        if src:
            full_url = urljoin(target_url, src)
            asset_filename = f"js_{len(assets_to_download) + 1}.js"
            assets_to_download.append((full_url, Path("assets") / asset_filename))
            script['src'] = f"assets/{asset_filename}"

    # 3. All Heavy Media Assets (Images, HD Videos, Audio, Fonts, Objects, Embeds)
    for media in soup.find_all(['img', 'video', 'source', 'audio', 'embed', 'object', 'iframe', 'track'], src=True):
        src = media.get('src')
        if src and not src.startswith("data:"):
            full_url = urljoin(target_url, src)
            ext = Path(urlparse(full_url).path).suffix or ".png"
            if len(ext) > 6 or not ext:
                ext = ".png"
            asset_filename = f"media_{len(assets_to_download) + 1}{ext}"
            assets_to_download.append((full_url, Path("assets") / asset_filename))
            media['src'] = f"assets/{asset_filename}"

    # Save Primary HTML File
    index_file = output_dir / "index.html"
    index_file.write_text(str(soup), encoding='utf-8')

    # Multi-threaded Streaming Downloader (24 Parallel Threads for Speed)
    if assets_to_download:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"[cyan]📦 Extracting {len(assets_to_download)} Assets (Heavy Mode)...", total=len(assets_to_download))
            
            with ThreadPoolExecutor(max_workers=24) as executor:
                futures = [executor.submit(download_asset_stream, asset, headers, output_dir) for asset in assets_to_download]
                for future in futures:
                    future.result()
                    progress.advance(task)

    # Creating High Compression ZIP Archive
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(output_dir)
                zipf.write(file_path, arcname)

    # Cleanup Temporary Extractions
    try:
        shutil.rmtree(output_dir)
    except Exception:
        pass

    zip_size = zip_path.stat().st_size
    return str(zip_path), zip_size

def main():
    console.clear()
    display_banner()
    
    target_url = Prompt.ask("[bold green]🔗 Enter Full Website URL[/bold green]")
    
    if not target_url.startswith("http"):
        target_url = "https://" + target_url
        console.print(f"[dim]Auto-added https:// -> {target_url}[/dim]\n")
    
    console.print()
    zip_file, size = extract_full_source(target_url)
    
    if zip_file:
        console.print(Panel(
            f"🎉 [bold green]Full Original Source Code Extracted![/bold green] 🎉\n\n"
            f"🎯 [bold cyan]Target URL:[/bold cyan] [yellow]{target_url}[/yellow]\n"
            f"📦 [bold cyan]Saved Package Location:[/bold cyan]\n[bold green]{zip_file}[/bold green]\n"
            f"📏 [bold cyan]Total Package Size:[/bold cyan] [bold yellow]{format_size(size)}[/bold yellow]\n\n"
            f"📂 [bold yellow]Auto Saved MT Manager Location:[/bold yellow]\nOpen MT Manager ➔ Download ➔ [bold cyan]{FOLDER_NAME}[/bold cyan] ➔ [bold green]{Path(zip_file).name}[/bold green]",
            box=box.HEAVY,
            border_style="orange3",
            title="[bold orange3]Hindustan Extractor[/bold orange3]"
        ))
    
    another = Prompt.ask("\n[bold cyan]🔄 Extract another website?[/bold cyan]", choices=["y", "n"], default="n")
    if another.lower() == 'y':
        main()
    else:
        console.print("\n[bold orange3]🙏 Thank you for using Hindustan Tool![/bold orange3]\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]👋 Exited by user. Goodbye![/yellow]")
