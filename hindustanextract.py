import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse, urljoin, urldefrag
from pathlib import Path
import zipfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import mimetypes
from bs4 import BeautifulSoup
import json
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box
from rich.text import Text
from rich.table import Table
import pyfiglet

console = Console()

# Configuration
FOLDER_NAME = "Hindustan_Hack_Projects"
CUSTOM_PREFIX = "Hindustan_Hack_"
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB limit
MAX_WORKERS = 30

class WebsiteSourceExtractor:
    def __init__(self, target_url):
        self.target_url = target_url
        self.base_domain = urlparse(target_url).netloc
        self.session = self._get_robust_session()
        self.site_name = self._get_clean_site_name(target_url)
        self.output_dir = self._get_output_directory()
        self.temp_dir = self.output_dir / f"source_{self.site_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.downloaded_files = []
        self.total_files = 0
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create proper folder structure
        self.folders = {
            'html': 'HTML Files',
            'css': 'CSS Stylesheets',
            'js': 'JavaScript Files',
            'php': 'PHP Scripts',
            'images': 'Images',
            'videos': 'Videos',
            'fonts': 'Fonts',
            'api': 'API Endpoints',
            'config': 'Configurations',
            'database': 'Database Files',
            'server': 'Server Scripts',
            'assets': 'Other Assets'
        }
        
        for folder in self.folders:
            (self.temp_dir / folder).mkdir(exist_ok=True)

    def _get_robust_session(self):
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def _get_clean_site_name(self, url):
        domain = urlparse(url).netloc
        if not domain:
            domain = "site"
        domain = domain.replace("www.", "").split(".")[0]
        return domain.capitalize()

    def _get_output_directory(self):
        sdcard_path = Path("/sdcard/Download") / FOLDER_NAME
        try:
            sdcard_path.mkdir(parents=True, exist_ok=True)
            return sdcard_path
        except Exception:
            local_path = Path(".") / FOLDER_NAME
            local_path.mkdir(parents=True, exist_ok=True)
            return local_path

    def _get_proper_extension(self, url, content_type=None, content=None):
        """Get proper file extension based on URL and content"""
        parsed = urlparse(url)
        path = parsed.path
        
        # Check if path has extension
        ext = Path(path).suffix.lower()
        
        # If extension is empty or invalid, detect from content
        if not ext or len(ext) > 6:
            # Check content-type
            if content_type:
                ext = mimetypes.guess_extension(content_type.split(';')[0].strip())
                if ext:
                    return ext
            
            # Detect from content
            if content:
                content_lower = content[:500].lower()
                if '<html' in content_lower or '<!DOCTYPE' in content_lower:
                    return '.html'
                elif '<?php' in content_lower:
                    return '.php'
                elif 'function' in content_lower and 'var ' in content_lower:
                    return '.js'
                elif '{' in content_lower and ':' in content_lower and '"' in content_lower:
                    return '.json'
                elif '.css' in content_lower or 'style' in content_lower:
                    return '.css'
            
            # Detect from URL path
            if 'css' in path or 'style' in path:
                return '.css'
            elif 'js' in path or 'script' in path:
                return '.js'
            elif 'php' in path:
                return '.php'
            elif 'api' in path:
                return '.json'
            elif 'image' in path or 'img' in path:
                return '.jpg'
            elif 'video' in path:
                return '.mp4'
            elif 'font' in path:
                return '.woff2'
            else:
                return '.html'  # Default
        
        return ext

    def _get_category(self, ext, url=""):
        """Get proper category based on extension"""
        ext = ext.lower()
        url_lower = url.lower()
        
        # HTML
        if ext in ['.html', '.htm', '.xhtml', '.shtml']:
            return 'html'
        # CSS
        elif ext in ['.css', '.scss', '.sass', '.less']:
            return 'css'
        # JavaScript
        elif ext in ['.js', '.mjs', '.ts', '.jsx', '.tsx']:
            return 'js'
        # PHP
        elif ext in ['.php', '.phtml', '.php3', '.php4', '.php5', '.php7']:
            return 'php'
        # Images
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp', '.tiff']:
            return 'images'
        # Videos
        elif ext in ['.mp4', '.mkv', '.webm', '.avi', '.mov', '.mp3', '.wav', '.ogg']:
            return 'videos'
        # Fonts
        elif ext in ['.woff', '.woff2', '.ttf', '.eot', '.otf']:
            return 'fonts'
        # API
        elif ext in ['.json', '.xml'] or 'api' in url_lower:
            return 'api'
        # Config
        elif ext in ['.config', '.cfg', '.conf', '.ini', '.env']:
            return 'config'
        # Database
        elif ext in ['.db', '.sql', '.sqlite']:
            return 'database'
        # Server scripts
        elif ext in ['.py', '.rb', '.go', '.java', '.asp', '.aspx', '.jsp']:
            return 'server'
        # Default
        else:
            return 'assets'

    def _create_proper_filename(self, url, category, index):
        """Create proper filename with correct extension"""
        parsed = urlparse(url)
        path = parsed.path
        
        # Get base name
        base_name = Path(path).stem
        if not base_name or base_name == '':
            base_name = f"file_{index}"
        
        # Clean filename
        base_name = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)
        
        # Get proper extension
        ext = self._get_proper_extension(url)
        
        # Special cases
        if category == 'html' and not ext:
            ext = '.html'
        elif category == 'php' and not ext:
            ext = '.php'
        elif category == 'js' and not ext:
            ext = '.js'
        elif category == 'css' and not ext:
            ext = '.css'
        elif category == 'api' and not ext:
            ext = '.json'
        
        # Ensure extension exists
        if not ext:
            ext = '.html'
        
        return f"{base_name}{ext}"

    def _extract_urls_from_html(self, html_content, base_url):
        """Extract all URLs from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = []
        
        # All tags that can contain URLs
        tag_attributes = {
            'link': ['href'],
            'script': ['src'],
            'img': ['src', 'data-src', 'lazy-src'],
            'a': ['href'],
            'form': ['action'],
            'iframe': ['src'],
            'source': ['src'],
            'video': ['src', 'poster'],
            'audio': ['src'],
            'embed': ['src'],
            'object': ['data'],
            'track': ['src'],
            'input': ['src'],
            'meta': ['content']
        }
        
        for tag_name, attributes in tag_attributes.items():
            for element in soup.find_all(tag_name):
                for attr in attributes:
                    if element.has_attr(attr):
                        value = element[attr]
                        if value and not value.startswith(('#', 'javascript:', 'data:', 'mailto:', 'tel:')):
                            full_url = urljoin(base_url, value)
                            urls.append((full_url, element, attr, value))
        
        # Find CSS url() references
        css_pattern = r'url\([\'"]?(.*?)[\'"]?\)'
        
        # Inline styles
        for element in soup.find_all(style=True):
            style_content = element.get('style', '')
            for match in re.finditer(css_pattern, style_content):
                url = match.group(1)
                if url and not url.startswith(('#', 'data:', 'javascript:')):
                    full_url = urljoin(base_url, url)
                    urls.append((full_url, element, 'style', url))
        
        # In style tags
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                for match in re.finditer(css_pattern, style_tag.string):
                    url = match.group(1)
                    if url and not url.startswith(('#', 'data:', 'javascript:')):
                        full_url = urljoin(base_url, url)
                        urls.append((full_url, style_tag, 'style', url))
        
        return urls, soup

    def download_file(self, url, file_path):
        """Download file with proper content type detection"""
        try:
            if file_path.exists():
                return True
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            response = self.session.get(url, headers=self.headers, timeout=60, stream=True)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            content_length = int(response.headers.get('content-length', 0))
            
            if content_length > MAX_FILE_SIZE:
                console.print(f"[yellow]⚠️ Skipping large file: {url}[/yellow]")
                return False
            
            # Read content to detect proper extension
            content = response.content[:1024]  # First 1KB for detection
            
            # Get proper extension and update filename
            detected_ext = self._get_proper_extension(url, content_type, content.decode('utf-8', errors='ignore'))
            current_ext = file_path.suffix
            
            if detected_ext and detected_ext != current_ext:
                # Update file extension
                new_path = file_path.with_suffix(detected_ext)
                
                # If new path already exists, add number
                counter = 1
                while new_path.exists():
                    new_path = file_path.parent / f"{file_path.stem}_{counter}{detected_ext}"
                    counter += 1
                
                file_path = new_path
            
            # Write file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            
            self.total_files += 1
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error: {e} - {url}[/red]")
            return False

    def extract_website(self):
        """Main extraction function"""
        console.print(f"[bold cyan]🌐 Extracting: {self.target_url}[/bold cyan]")
        console.print(f"[yellow]📂 Target: {self.base_domain}[/yellow]")
        
        # Step 1: Download main page
        console.print(f"[yellow]📄 Downloading main page...[/yellow]")
        try:
            response = self.session.get(self.target_url, headers=self.headers, timeout=60)
            response.raise_for_status()
            main_html = response.text
            
            # Save main HTML with proper extension
            main_file = self.temp_dir / 'html' / 'index.html'
            main_file.write_text(main_html, encoding='utf-8')
            self.downloaded_files.append(main_file)
            
        except Exception as e:
            console.print(f"[red]❌ Failed: {e}[/red]")
            return None, 0
        
        # Step 2: Extract all URLs from HTML
        console.print(f"[yellow]🔍 Extracting resources from HTML...[/yellow]")
        urls, soup = self._extract_urls_from_html(main_html, self.target_url)
        console.print(f"[green]✅ Found {len(urls)} resources[/green]")
        
        # Step 3: Download all resources
        console.print(f"[yellow]⬇️ Downloading resources...[/yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=False
        ) as progress:
            task = progress.add_task(f"[cyan]Downloading...", total=len(urls))
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                
                for url, element, attr, original_value in urls:
                    # Determine category and create filename
                    ext = self._get_proper_extension(url)
                    category = self._get_category(ext, url)
                    filename = self._create_proper_filename(url, category, len(self.downloaded_files) + 1)
                    file_path = self.temp_dir / category / filename
                    
                    # Submit download
                    future = executor.submit(self.download_file, url, file_path)
                    futures.append(future)
                    
                    # Update HTML to use local file
                    if attr:
                        local_path = f"{category}/{filename}"
                        if attr == 'style':
                            # Replace in style attribute
                            element[attr] = element[attr].replace(original_value, local_path)
                        else:
                            # Replace URL in attribute
                            element[attr] = local_path
                
                # Wait for all downloads
                for future in as_completed(futures):
                    future.result()
                    progress.advance(task)
        
        # Step 4: Save updated HTML
        console.print(f"[yellow]💾 Saving updated HTML...[/yellow]")
        updated_html = str(soup)
        updated_file = self.temp_dir / 'html' / 'index_updated.html'
        updated_file.write_text(updated_html, encoding='utf-8')
        self.downloaded_files.append(updated_file)
        
        # Step 5: Process CSS files
        console.print(f"[yellow]🎨 Processing CSS files...[/yellow]")
        css_files = list((self.temp_dir / 'css').glob('*.css'))
        
        for css_file in css_files:
            try:
                css_content = css_file.read_text(encoding='utf-8', errors='ignore')
                css_pattern = r'url\([\'"]?(.*?)[\'"]?\)'
                
                for match in re.finditer(css_pattern, css_content):
                    url = match.group(1)
                    if url and not url.startswith(('#', 'data:', 'javascript:')):
                        full_url = urljoin(self.target_url, url)
                        ext = self._get_proper_extension(full_url)
                        category = self._get_category(ext, full_url)
                        filename = self._create_proper_filename(full_url, category, len(self.downloaded_files) + 1)
                        file_path = self.temp_dir / category / filename
                        
                        # Download CSS resource
                        self.download_file(full_url, file_path)
                        
                        # Update CSS
                        css_content = css_content.replace(url, f"{category}/{filename}")
                
                css_file.write_text(css_content, encoding='utf-8')
                
            except Exception as e:
                console.print(f"[red]❌ CSS Error: {e}[/red]")
        
        # Step 6: Process JavaScript files for additional resources
        console.print(f"[yellow]📜 Processing JavaScript files...[/yellow]")
        js_files = list((self.temp_dir / 'js').glob('*.js'))
        
        for js_file in js_files:
            try:
                js_content = js_file.read_text(encoding='utf-8', errors='ignore')
                
                # Find API calls and URLs in JS
                url_patterns = [
                    r'(?:fetch|axios|\.get|\.post|\.put|\.delete)\s*\(\s*[\'"]([^\'"]+)[\'"]',
                    r'(?:url|api|endpoint)\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
                    r'https?://[^\s\'"]+',
                    r'/(?:api|v[0-9]+|rest)/[^\s\'"]+'
                ]
                
                for pattern in url_patterns:
                    for match in re.finditer(pattern, js_content, re.IGNORECASE):
                        url = match.group(1) if match.groups() else match.group(0)
                        if url and not url.startswith(('#', 'javascript:', 'data:')):
                            full_url = urljoin(self.target_url, url)
                            ext = self._get_proper_extension(full_url)
                            category = self._get_category(ext, full_url)
                            filename = self._create_proper_filename(full_url, category, len(self.downloaded_files) + 1)
                            file_path = self.temp_dir / category / filename
                            
                            self.download_file(full_url, file_path)
                            
            except Exception as e:
                console.print(f"[red]❌ JS Error: {e}[/red]")
        
        # Step 7: Create extraction summary
        summary = {
            'target_url': self.target_url,
            'domain': self.base_domain,
            'site_name': self.site_name,
            'extraction_date': datetime.now().isoformat(),
            'total_files': self.total_files,
            'folders_created': list(self.folders.keys())
        }
        
        summary_file = self.temp_dir / 'extraction_summary.json'
        summary_file.write_text(json.dumps(summary, indent=2))
        self.downloaded_files.append(summary_file)
        
        # Step 8: Create ZIP archive
        console.print(f"[bold green]📦 Creating ZIP archive...[/bold green]")
        zip_filename = f"{CUSTOM_PREFIX}{self.site_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = self.output_dir / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in self.temp_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.temp_dir)
                    zipf.write(file_path, arcname)
        
        # Clean up
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
        
        zip_size = zip_path.stat().st_size
        return str(zip_path), zip_size, summary

def display_banner():
    try:
        banner_text = pyfiglet.figlet_format("SOURCE EXTRACTOR", font="small")
    except:
        banner_text = "=== SOURCE EXTRACTOR ==="
    
    colored_banner = Text(banner_text, style="bold cyan")
    
    console.print(Panel(
        colored_banner,
        box=box.DOUBLE,
        border_style="cyan",
        title="[bold red] PRO SOURCE CODE EXTRACTOR v6.0 [/bold red]",
        subtitle="[bold yellow] Developer: @Rolexconfigyt [/bold yellow]"
    ))
    
    desc = Text(
        "📦 Complete Website Source Code Extractor\n"
        "✅ HTML | CSS | JavaScript | PHP | Images | Videos | Fonts\n"
        "✅ Proper File Extensions | Correct Folder Structure\n"
        "✅ Fast Multi-Threaded Download | 10GB+ Support\n"
        "✅ Working Source Code - Not Garbage!",
        style="bold green",
        justify="center"
    )
    console.print(Panel(desc, box=box.ROUNDED, border_style="green"))
    console.print()

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def main():
    console.clear()
    display_banner()
    
    target_url = Prompt.ask("[bold green]🔗 Enter Website URL[/bold green]")
    
    if not target_url.startswith("http"):
        target_url = "https://" + target_url
        console.print(f"[dim]✅ Added https://[/dim]\n")
    
    extractor = WebsiteSourceExtractor(target_url)
    zip_file, size, summary = extractor.extract_website()
    
    if zip_file:
        console.print(Panel(
            f"🎉 [bold green]SOURCE CODE EXTRACTED SUCCESSFULLY![/bold green] 🎉\n\n"
            f"🌐 [bold cyan]Website:[/bold cyan] [yellow]{target_url}[/yellow]\n"
            f"📦 [bold cyan]Package:[/bold cyan] [bold green]{Path(zip_file).name}[/bold green]\n"
            f"📏 [bold cyan]Size:[/bold cyan] [bold yellow]{format_size(size)}[/bold yellow]\n"
            f"📁 [bold cyan]Files:[/bold cyan] [bold magenta]{summary['total_files']}[/bold magenta]\n"
            f"📂 [bold cyan]Categories:[/bold cyan] [bold magenta]{len(summary['folders_created'])}[/bold magenta]\n\n"
            f"📂 [bold yellow]Location:[/bold yellow]\n[bold green]{Path(zip_file).absolute()}[/bold green]",
            box=box.HEAVY,
            border_style="green",
            title="[bold green] ✨ SOURCE EXTRACTOR RESULT ✨ [/bold green]"
        ))
    
    another = Prompt.ask("\n[bold cyan]🔄 Extract another website?[/bold cyan]", choices=["y", "n"], default="n")
    if another.lower() == 'y':
        main()
    else:
        console.print("\n[bold green]🙏 Thanks for using Source Extractor![/bold green]\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Exited by user. Goodbye![/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
