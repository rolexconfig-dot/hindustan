import os
import re
import zipfile
import shutil
from pathlib import Path
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box

console = Console()

OUTPUT_FOLDER = "Downloaded_Projects"
ZIP_PREFIX = "Web_Archive_"

def create_resilient_session():
    """Builds an HTTP session with retry mechanisms for stable asset downloading."""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_domain_name(url):
    domain = urlparse(url).netloc
    if not domain:
        domain = "website"
    return domain.replace("www.", "").split(".")[0].capitalize()

def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def determine_asset_directory(extension):
    ext = extension.lower().split('?')[0]
    if ext in ['.css']:
        return "css"
    elif ext in ['.js', '.mjs']:
        return "js"
    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico']:
        return "images"
    elif ext in ['.woff', '.woff2', '.ttf', '.eot', '.otf']:
        return "fonts"
    elif ext in ['.mp4', '.webm', '.ogg', '.mp3']:
        return "media"
    else:
        return "assets"

def fetch_single_asset(asset_tuple, headers, temp_directory, session):
    asset_url, relative_path = asset_tuple
    try:
        destination_path = temp_directory / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        with session.get(asset_url, headers=headers, timeout=30, stream=True) as resp:
            if resp.status_code == 200:
                with open(destination_path, 'wb') as file:
                    for chunk in resp.iter_content(chunk_size=2 * 1024 * 1024):
                        if chunk:
                            file.write(chunk)
                return True
    except Exception:
        pass
    return False

def archive_website(target_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    session = create_resilient_session()
    site_label = get_domain_name(target_url)

    output_base_dir = Path(OUTPUT_FOLDER)
    output_base_dir.mkdir(parents=True, exist_ok=True)

    zip_file_path = output_base_dir / f"{ZIP_PREFIX}{site_label}.zip"
    temp_working_dir = output_base_dir / f"temp_{site_label}"
    temp_working_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold cyan]🌐 Fetching page content from {target_url}...[/bold cyan]")
    try:
        response = session.get(target_url, headers=headers, timeout=30)
        response.raise_for_status()
        raw_content = response.text
    except Exception as err:
        console.print(f"[bold red]❌ Request Failed:[/bold red] {err}")
        return None, 0

    # Extract asset references
    found_links = re.findall(r'(?:href|src|action)=["\'](.*?)["\']', raw_content)
    css_url_links = re.findall(r'url\(["\']?(.*?)["\']?\)', raw_content)
    all_references = found_links + css_url_links

    download_tasks = []
    processed_urls = set()

    for index, link in enumerate(all_references, start=1):
        if link.startswith("data:") or link.startswith("#") or link.startswith("javascript:"):
            continue

        absolute_asset_url = urljoin(target_url, link)
        if absolute_asset_url in processed_urls:
            continue
        processed_urls.add(absolute_asset_url)

        parsed_path = urlparse(absolute_asset_url).path
        ext = Path(parsed_path).suffix
        if not ext or len(ext) > 6:
            ext = ".asset"

        target_folder = determine_asset_directory(ext)
        clean_ext = ext.split('?')[0]
        filename = f"asset_{index}{clean_ext}"
        relative_filepath = Path(target_folder) / filename

        download_tasks.append((absolute_asset_url, relative_filepath))
        raw_content = raw_content.replace(link, f"{target_folder}/{filename}")

    # Determine index file naming based on target URL extension
    parsed_target_path = urlparse(target_url).path
    if parsed_target_path.endswith(".php"):
        main_file_name = "index.php"
    else:
        main_file_name = "index.html"

    (temp_working_dir / main_file_name).write_text(raw_content, encoding='utf-8')

    if download_tasks:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"[bold yellow]📦 Downloading {len(download_tasks)} Assets...", total=len(download_tasks))

            with ThreadPoolExecutor(max_workers=15) as executor:
                futures = [executor.submit(fetch_single_asset, item, headers, temp_working_dir, session) for item in download_tasks]
                for future in futures:
                    future.result()
                    progress.advance(task)

    console.print("[bold green]⚡ Packaging assets into ZIP archive...[/bold green]")
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
        for root, _, files in os.walk(temp_working_dir):
            for file in files:
                full_file_path = Path(root) / file
                archive_name = full_file_path.relative_to(temp_working_dir)
                zip_out.write(full_file_path, archive_name)

    try:
        shutil.rmtree(temp_working_dir)
    except Exception:
        pass

    archive_size = zip_file_path.stat().st_size
    return str(zip_file_path), archive_size

def main():
    console.clear()
    console.print(Panel("[bold cyan]Web Page Asset Archiver[/bold cyan]", box=box.ROUNDED, border_style="cyan"))

    target_url = Prompt.ask("[bold green]🔗 Enter Target Web URL[/bold green]")

    if not target_url.startswith("http"):
        target_url = "https://" + target_url

    zip_file, size = archive_website(target_url)

    if zip_file:
        console.print(Panel(
            f"🎉 [bold green]Archive Created Successfully![/bold green]\n\n"
            f"🎯 [bold cyan]Target URL:[/bold cyan] {target_url}\n"
            f"📦 [bold cyan]Saved Package:[/bold cyan] {Path(zip_file).name}\n"
            f"📏 [bold cyan]Package Size:[/bold cyan] {format_bytes(size)}\n"
            f"📂 [bold yellow]Location:[/bold yellow] {Path(zip_file).absolute()}",
            box=box.HEAVY,
            border_style="green",
            title="[bold green] Extraction Summary [/bold green]"
        ))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Exited by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
