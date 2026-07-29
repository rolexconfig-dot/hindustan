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
from rich import box
from rich.text import Text
import pyfiglet

console = Console()

FOLDER_NAME = "Hindustan_Hack_Projects"
CUSTOM_PREFIX = "Hindustan_Hack_"

def get_fast_session():
    """High-concurrency HTTP session built for ultra-fast downloads."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=100)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def display_banner():
    """Renders the exact UI matching screenshot 199981.jpg."""
    try:
        banner_text = pyfiglet.figlet_format("HINDUSTAN", font="standard")
    except Exception:
        banner_text = "HINDUSTAN"
        
    banner_lines = banner_text.splitlines()
    colored_text = Text()
    for line in banner_lines:
        colored_text.append(line + "\n", style="bold cyan")
    
    colored_text.append("\n          Developer: @Rolexconfigyt          ", style="bold yellow")

    console.print(Panel(
        colored_text, 
        box=box.DOUBLE, 
        border_style="cyan",
        title="[bold red]Extractor v1.0[/bold red]",
        title_align="center"
    ))
    
    desc = Text("🚀 Advanced Direct Source Code & Asset Scraper\nSecure & Fast Web Extraction Engine", style="bold green", justify="center")
    console.print(Panel(desc, box=box.ROUNDED, border_style="green"))

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
    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico']:
        return "images"
    elif ext in ['.mp4', '.webm', '.ogg', '.mp3', '.avi', '.mkv']:
        return "media"
    elif ext in ['.woff', '.woff2', '.ttf', '.eot', '.otf']:
        return "fonts"
    else:
        return "assets"

def download_single_asset(asset_info, headers, output_folder, session):
    url, local_rel_path = asset_info
    try:
        full_path = output_folder / local_rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with session.get(url, headers=headers, timeout=15, stream=True) as res:
            if res.status_code == 200:
                with open(full_path, 'wb') as f:
                    for chunk in res.iter_content(chunk_size=4 * 1024 * 1024):
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
    
    session = get_fast_session()
    site_name = get_clean_site_name(target_url)
    output_dir = get_output_directory()

    zip_filename = f"{CUSTOM_PREFIX}{site_name}.zip"
    zip_path = output_dir / zip_filename
    temp_dir = output_dir / f"temp_{site_name}"
    
    temp_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"🌐 Connecting directly to\n[bold cyan]{target_url}...[/bold cyan]")
    
    try:
        response = session.get(target_url, headers=headers, timeout=20)
        response.raise_for_status()
        raw_html = response.text
    except Exception as e:
        console.print(f"[bold red]❌ Connection Error:[/bold red] {e}")
        return None, 0

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
        clean_ext = ext.split('?')[0]
        filename = f"asset_{count}{clean_ext}"
        relative_path = Path(subfolder) / filename
        
        download_queue.append((full_url, relative_path))
        raw_html = raw_html.replace(link, f"{subfolder}/{filename}")

    parsed_target_path = urlparse(target_url).path
    index_name = "index.php" if parsed_target_path.endswith(".php") else "index.html"
    (temp_dir / index_name).write_text(raw_html, encoding='utf-8')

    # Fast 50 Parallel Worker Threads
    if download_queue:
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(download_single_asset, item, headers, temp_dir, session) for item in download_queue]
            for future in futures:
                future.result()

    console.print("[bold yellow]⚡ Packaging extracted source into ZIP...[/bold yellow]")
    
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
    
    console.print()
    zip_file, size = extract_direct_source(target_url)
    
    if zip_file:
        saved_name = Path(zip_file).name
        full_output_location = str(Path(zip_file).absolute())
        
        result_text = (
            f"🎉 [bold green]FULL SOURCE CODE EXTRACTED SUCCESSFULLY![/bold green] 🎉\n\n"
            f"🎯 [bold cyan]Target URL:[/bold cyan] [yellow]{target_url}[/yellow]\n"
            f"📦 [bold cyan]Saved Package:[/bold cyan]\n[bold green]{saved_name}[/bold green]\n"
            f"📏 [bold cyan]Package Size:[/bold cyan]  [bold yellow]{format_size(size)}[/bold yellow]\n\n"
            f"📂 [bold yellow]Output Location:[/bold yellow]\n[bold green]{full_output_location}[/bold green]"
        )
        
        console.print(Panel(
            result_text,
            box=box.ROUNDED,
            border_style="green",
            title="✨ HINDUSTAN EXTRACTOR RESULT ✨",
            title_align="center"
        ))
    
    console.print()
    another = Prompt.ask("🔄 Extract another website? [y/n]", default="n")
    if another.lower() == 'y':
        main()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]👋 Exited by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")

