import os
import re
import requests
from urllib.parse import urlparse, urljoin
from pathlib import Path
import zipfile
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import pyfiglet

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box
from rich.text import Text

console = Console()

# Custom Prefix for saved files
CUSTOM_PREFIX = "Hindustan_Hack_"

def display_banner():
    try:
        # standard font use kiya hai taaki naam achha dikhe
        banner_text = pyfiglet.figlet_format("HINDUSTAN", font="standard")
    except Exception:
        banner_text = "=== HINDUSTAN ==="
        
    # Banner color is set to Green as requested
    colored_banner = Text(banner_text, style="bold green")
    
    console.print(Panel(
        colored_banner, 
        box=box.DOUBLE, 
        border_style="green",
        title="[bold orange3] Universal Pro v3.0 [/bold orange3]",
        subtitle="[bold orange3] Developer: @Rolexconfigyt [/bold orange3]"
    ))
    
    desc = Text("🌐 Direct HTML, CSS, JS, Images & Fonts Extractor\nAuto-Save to Internal Storage / MT Manager!", style="bold green", justify="center")
    console.print(Panel(desc, box=box.ROUNDED, border_style="orange3"))
    console.print()

def get_clean_site_name(url):
    domain = urlparse(url).netloc
    if not domain:
        domain = "site"
    domain = domain.replace("www.", "").split(".")[0]
    return domain.capitalize()

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def get_ext(url, default=".png"):
    path = urlparse(url).path
    ext = Path(path).suffix
    return ext if ext else default

def download_file(url, local_path, headers):
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(res.content)
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
    download_dir = Path("/sdcard/Download") if Path("/sdcard/Download").exists() else Path(".")

    custom_zip_name = f"{CUSTOM_PREFIX}{site_name}.zip"
    zip_path = download_dir / custom_zip_name
    output_dir = download_dir / f"temp_{site_name}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Auto Folder Structure Creation
    dirs = {
        'css': output_dir / "css",
        'js': output_dir / "js",
        'img': output_dir / "images",
        'fonts': output_dir / "fonts"
    }
    for d in dirs.values():
        d.mkdir(exist_ok=True)

    try:
        console.print(f"[cyan]⏳ Connecting to {target_url}...[/cyan]")
        response = requests.get(target_url, headers=headers, timeout=15)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        console.print(f"[bold red]❌ Connection Error: {e}[/bold red]")
        return None, 0

    soup = BeautifulSoup(html_content, 'html.parser')
    download_tasks = [] 
    
    # 1. CSS Assets Extraction
    css_counter = 1
    for link in soup.find_all('link', rel=True):
        if 'stylesheet' in link.get('rel', []):
            href = link.get('href')
            if href:
                full_url = urljoin(target_url, href)
                filename = f"style_{css_counter}.css"
                local_path = dirs['css'] / filename
                
                # Download CSS and Extract Fonts/Images from inside CSS
                try:
                    css_res = requests.get(full_url, headers=headers, timeout=10)
                    if css_res.status_code == 200:
                        css_text = css_res.text
                        # Find url(...) in CSS
                        urls_in_css = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', css_text)
                        for url_in_css in urls_in_css:
                            if url_in_css.startswith('data:'): continue
                            asset_full_url = urljoin(full_url, url_in_css)
                            ext = get_ext(asset_full_url, '.woff2').lower()
                            
                            # Check if it is a font or image
                            if ext in ['.woff', '.woff2', '.ttf', '.eot', '.otf']:
                                asset_name = f"font_{len(download_tasks)}{ext}"
                                download_tasks.append((asset_full_url, dirs['fonts'] / asset_name))
                                css_text = css_text.replace(url_in_css, f"../fonts/{asset_name}")
                            else:
                                asset_name = f"bg_{len(download_tasks)}{ext}"
                                download_tasks.append((asset_full_url, dirs['img'] / asset_name))
                                css_text = css_text.replace(url_in_css, f"../images/{asset_name}")
                        
                        local_path.write_text(css_text, encoding='utf-8')
                        link['href'] = f"css/{filename}"
                        css_counter += 1
                except Exception:
                    pass

    # 2. JS Assets Extraction
    for i, script in enumerate(soup.find_all('script', src=True)):
        src = script.get('src')
        if src:
            full_url = urljoin(target_url, src)
            filename = f"script_{i+1}.js"
            download_tasks.append((full_url, dirs['js'] / filename))
            script['src'] = f"js/{filename}"

    # 3. Image Assets Extraction
    for i, img in enumerate(soup.find_all('img', src=True)):
        src = img.get('src')
        if src and not src.startswith("data:"):
            full_url = urljoin(target_url, src)
            ext = get_ext(full_url)
            filename = f"image_{i+1}{ext}"
            download_tasks.append((full_url, dirs['img'] / filename))
            img['src'] = f"images/{filename}"

    # Save Clean Index HTML
    (output_dir / "index.html").write_text(str(soup), encoding='utf-8')

    # Multi-threaded Fast Download for Assets
    if download_tasks:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"[bold green]📦 Extracting {len(download_tasks)} Assets (JS, Images, Fonts)...[/bold green]", total=len(download_tasks))
            
            with ThreadPoolExecutor(max_workers=15) as executor:
                futures = [executor.submit(download_file, asset[0], asset[1], headers) for asset in download_tasks]
                for future in futures:
                    future.result()
                    progress.advance(task)

    # Creating Final Auto ZIP File
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(output_dir)
                zipf.write(file_path, arcname)

    # Cleanup Temporary Folders
    try:
        import shutil
        shutil.rmtree(output_dir)
    except Exception:
        pass

    return str(zip_path), zip_path.stat().st_size

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
            f"🎉 [bold green]Full Source Extracted Successfully![/bold green] 🎉\n\n"
            f"🎯 [bold orange3]Target URL:[/bold orange3] [bold white]{target_url}[/bold white]\n"
            f"✅ [bold orange3]Extracted:[/bold orange3] [bold white]HTML, CSS, JS, Images, Fonts[/bold white]\n"
            f"📦 [bold orange3]Saved Zip:[/bold orange3] [bold green]{zip_file}[/bold green]\n"
            f"📏 [bold orange3]Total Size:[/bold orange3] [bold white]{format_size(size)}[/bold white]\n\n"
            f"📂 [bold green]MT Manager Location:[/bold green]\nOpen MT Manager ➔ Download folder ➔ [bold orange3]{Path(zip_file).name}[/bold orange3]",
            box=box.HEAVY,
            border_style="green",
            title="[bold green]Hindustan Hack Extractor v3.0[/bold green]"
        ))
    
    another = Prompt.ask("\n[bold orange3]🔄 Extract another website?[/bold orange3]", choices=["y", "n"], default="n")
    if another.lower() == 'y':
        main()
    else:
        console.print("\n[bold green]🙏 Thanks for using Hindustan Hack Tool![/bold green]\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[bold orange3]👋 Exited by user. Goodbye![/bold orange3]")
