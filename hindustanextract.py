import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse, urljoin, urldefrag, parse_qs
from pathlib import Path
import zipfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import mimetypes
from bs4 import BeautifulSoup
import hashlib
import json
import ast
import base64
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
MAX_WORKERS = 50  # Increased for faster extraction

class UltimateWebsiteScraper:
    def __init__(self, target_url):
        self.target_url = target_url
        self.base_domain = urlparse(target_url).netloc
        self.session = self._get_robust_session()
        self.site_name = self._get_clean_site_name(target_url)
        self.output_dir = self._get_output_directory()
        self.temp_dir = self.output_dir / f"temp_{self.site_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.downloaded_files = []
        self.file_map = {}
        self.api_endpoints = set()
        self.firebase_configs = []
        self.php_files = []
        self.javascript_apis = []
        self.hidden_dirs = []
        self.extracted_data = {
            'apis': [],
            'firebase': [],
            'php_files': [],
            'databases': [],
            'configs': [],
            'secrets': []
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create comprehensive directory structure
        self.dirs = [
            'html', 'css', 'javascript', 'js_libs', 'images', 'media', 'fonts',
            'php', 'api', 'firebase', 'database', 'config', 'secrets',
            'server_scripts', 'xml', 'json', 'text', 'documents', 'assets',
            'hidden', 'backup', 'logs', 'cache', 'uploads', 'vendor', 'node_modules'
        ]
        for d in self.dirs:
            (self.temp_dir / d).mkdir(exist_ok=True)

    def _get_robust_session(self):
        session = requests.Session()
        retries = Retry(
            total=10,
            backoff_factor=2,
            status_forcelist=[500, 502, 503, 504, 429, 401, 403],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=100)
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
            test_file = sdcard_path / ".perm_test"
            test_file.touch()
            test_file.unlink()
            return sdcard_path
        except Exception:
            local_path = Path(".") / FOLDER_NAME
            local_path.mkdir(parents=True, exist_ok=True)
            return local_path

    def _get_file_extension(self, url, content_type=None):
        parsed = urlparse(url)
        path = parsed.path
        
        # Check if path has extension
        ext = Path(path).suffix.lower()
        if ext and len(ext) <= 6:
            return ext
        
        if content_type:
            ext = mimetypes.guess_extension(content_type.split(';')[0].strip())
            if ext:
                return ext
        
        # Check for known resource types
        if 'css' in path or 'style' in path:
            return '.css'
        elif 'js' in path or 'script' in path or 'javascript' in path:
            return '.js'
        elif 'php' in path:
            return '.php'
        elif 'api' in path:
            return '.json'
        elif 'firebase' in path or 'firestore' in path:
            return '.json'
        elif 'font' in path or 'woff' in path:
            return '.woff2'
        elif 'image' in path or 'img' in path:
            return '.png'
        elif 'video' in path or 'stream' in path:
            return '.mp4'
        elif 'config' in path or 'cfg' in path:
            return '.config'
        elif 'database' in path or 'db' in path:
            return '.db'
        
        return '.html'

    def _categorize_file(self, ext, url=""):
        ext = ext.lower()
        url_lower = url.lower()
        
        # PHP files
        if ext in ['.php', '.phtml', '.php3', '.php4', '.php5', '.php7', '.phps']:
            return "php"
        # API files
        elif ext in ['.json', '.xml', '.yml', '.yaml'] or 'api' in url_lower:
            return "api"
        # Firebase/Firestore
        elif 'firebase' in url_lower or 'firestore' in url_lower or 'firebase' in ext:
            return "firebase"
        # Database
        elif ext in ['.db', '.sql', '.sqlite', '.sqlite3', '.mdb', '.accdb']:
            return "database"
        # Config files
        elif ext in ['.config', '.cfg', '.conf', '.ini', '.properties', '.toml'] or 'config' in url_lower:
            return "config"
        # CSS
        elif ext in ['.css', '.scss', '.sass', '.less']:
            return "css"
        # JavaScript
        elif ext in ['.js', '.mjs', '.ts', '.jsx', '.tsx', '.vue']:
            return "javascript"
        # Images
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp', '.tiff', '.avif']:
            return "images"
        # Media
        elif ext in ['.mp4', '.mkv', '.webm', '.avi', '.mov', '.mp3', '.wav', '.ogg', '.flac', '.m4a']:
            return "media"
        # Fonts
        elif ext in ['.woff', '.woff2', '.ttf', '.eot', '.otf']:
            return "fonts"
        # Server scripts
        elif ext in ['.py', '.rb', '.go', '.java', '.asp', '.aspx', '.jsp', '.cfm']:
            return "server_scripts"
        # Documents
        elif ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
            return "documents"
        # Text
        elif ext in ['.txt', '.md', '.rst', '.log']:
            return "text"
        # Hidden files
        elif url_lower.startswith('/.') or '/hidden/' in url_lower:
            return "hidden"
        # Default
        else:
            return "assets"

    def _generate_filename(self, url, category, index):
        parsed = urlparse(url)
        path = parsed.path
        
        # Get extension
        ext = self._get_file_extension(url)
        
        # Clean filename
        name = Path(path).stem
        if not name or name == '':
            name = f"file_{index}"
        
        # Remove special characters
        name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        
        # Truncate if too long
        if len(name) > 50:
            name = name[:50]
        
        return f"{name}{ext}"

    def _extract_apis_from_javascript(self, content, base_url):
        """Extract API endpoints from JavaScript code"""
        apis = []
        
        # Patterns for common API calls
        patterns = [
            r'(?:fetch|axios|http|\.get|\.post|\.put|\.delete|\.patch)\s*\(\s*[\'"]([^\'"]+)[\'"]',
            r'(?:url|api|endpoint|baseURL|baseUrl|base_url)\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
            r'(?:api|endpoint|route|path)\s*:\s*[\'"]([^\'"]+)[\'"]',
            r'https?://[^\s\'"]+(?:/api|/v[0-9]+|/rest|/graphql)[^\s\'"]*',
            r'/(?:api|v[0-9]+|rest|graphql)/[^\s\'"]+',
            r'firebase\.(?:firestore|database|storage|auth)\.(?:collection|doc|ref|get|set|update|delete)\([\'"]([^\'"]+)[\'"]',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                api_url = match.group(1) if match.groups() else match.group(0)
                if api_url and not api_url.startswith(('#', 'javascript:', 'data:', 'mailto:')):
                    full_url = urljoin(base_url, api_url)
                    apis.append(full_url)
                    self.api_endpoints.add(full_url)
        
        return apis

    def _extract_firebase_configs(self, content):
        """Extract Firebase configuration from code"""
        configs = []
        
        # Firebase config patterns
        patterns = [
            r'firebase\.initializeApp\s*\(\s*\{[^}]*\}',
            r'firebaseConfig\s*=\s*\{[^}]*\}',
            r'const\s+config\s*=\s*\{[^}]*\}',
            r'apiKey\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
            r'authDomain\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
            r'projectId\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
            r'storageBucket\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
            r'messagingSenderId\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
            r'appId\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                configs.append(match.group(0))
        
        return configs

    def _extract_php_resources(self, content, base_url):
        """Extract PHP file references and potential database connections"""
        php_resources = []
        
        # PHP file patterns
        patterns = [
            r'(?:include|require|include_once|require_once)\s*[\'"]([^\'"]+\.php)[\'"]',
            r'(?:action|href|src)\s*=\s*[\'"]([^\'"]+\.php)[\'"]',
            r'(?:url|link|path)\s*[:=]\s*[\'"]([^\'"]+\.php)[\'"]',
            r'/(?:[^\s\'"]+)\.php',
            r'mysqli_connect\s*\([\'"]([^\'"]+)[\'"]',
            r'new\s+PDO\s*\([\'"]([^\'"]+)[\'"]',
            r'database\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
            r'password\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
            r'username\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                resource = match.group(1) if match.groups() else match.group(0)
                if resource and not resource.startswith(('#', 'javascript:', 'data:')):
                    full_url = urljoin(base_url, resource)
                    php_resources.append(full_url)
        
        return php_resources

    def _scan_hidden_directories(self, base_url):
        """Scan for common hidden/admin directories"""
        hidden_dirs = [
            '/.git/', '/.env', '/.htaccess', '/.htpasswd',
            '/admin/', '/api/', '/backup/', '/config/',
            '/database/', '/log/', '/tmp/', '/cache/',
            '/uploads/', '/vendor/', '/node_modules/',
            '/.well-known/', '/.aws/', '/.ssh/',
            '/wp-admin/', '/wp-content/', '/wp-includes/'
        ]
        
        found_dirs = []
        for dir_path in hidden_dirs:
            test_url = urljoin(base_url, dir_path)
            try:
                response = self.session.head(test_url, timeout=5, allow_redirects=True)
                if response.status_code in [200, 301, 302, 403]:
                    found_dirs.append(test_url)
                    self.hidden_dirs.append(test_url)
            except:
                pass
        
        return found_dirs

    def download_file(self, url, file_path, headers=None):
        """Download a single file with progress tracking"""
        try:
            if file_path.exists():
                return True
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            response = self.session.get(url, headers=headers or self.headers, timeout=120, stream=True)
            response.raise_for_status()
            
            content_length = int(response.headers.get('content-length', 0))
            if content_length > MAX_FILE_SIZE:
                console.print(f"[yellow]⚠️ Skipping {url} - exceeds 10GB limit[/yellow]")
                return False
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)
            
            # Process file content based on type
            if file_path.suffix in ['.php', '.js', '.json', '.html', '.css']:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    
                    # Extract APIs
                    apis = self._extract_apis_from_javascript(content, url)
                    if apis:
                        self.extracted_data['apis'].extend(apis)
                    
                    # Extract Firebase configs
                    firebase_configs = self._extract_firebase_configs(content)
                    if firebase_configs:
                        self.extracted_data['firebase'].extend(firebase_configs)
                    
                    # Extract PHP resources
                    if file_path.suffix in ['.php', '.phtml']:
                        php_resources = self._extract_php_resources(content, url)
                        if php_resources:
                            self.extracted_data['php_files'].extend(php_resources)
                    
                except:
                    pass
            
            self.downloaded_files.append(file_path)
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error downloading {url}: {str(e)}[/red]")
            return False

    def scrape_website(self):
        """Main scraping function - extracts EVERYTHING"""
        console.print(f"[bold cyan]🌐 Starting ULTIMATE scrape of {self.target_url}[/bold cyan]")
        console.print(f"[yellow]📊 Extracting: HTML, CSS, JS, PHP, APIs, Firebase, Databases, Configs, Secrets, Hidden Dirs[/yellow]")
        
        # Stage 1: Hidden directories scan
        console.print(f"[yellow]🔍 Scanning for hidden/admin directories...[/yellow]")
        hidden_dirs = self._scan_hidden_directories(self.target_url)
        if hidden_dirs:
            console.print(f"[green]✅ Found {len(hidden_dirs)} hidden directories[/green]")
        
        # Stage 2: Download main page
        console.print(f"[yellow]📄 Downloading main page...[/yellow]")
        try:
            response = self.session.get(self.target_url, headers=self.headers, timeout=60)
            response.raise_for_status()
            main_html = response.text
            
            # Save main HTML
            main_file = self.temp_dir / "html" / "index.html"
            main_file.write_text(main_html, encoding='utf-8')
            self.downloaded_files.append(main_file)
            
        except Exception as e:
            console.print(f"[red]❌ Failed to download main page: {e}[/red]")
            return None, 0
        
        # Stage 3: Process HTML to find ALL resources
        soup = BeautifulSoup(main_html, 'html.parser')
        all_resources = []
        
        # All resource tags
        tags_to_check = {
            'link': ['href', 'hreflang', 'as', 'rel'],
            'script': ['src'],
            'img': ['src', 'srcset', 'data-src', 'lazy-src'],
            'source': ['src', 'srcset'],
            'audio': ['src'],
            'video': ['src', 'poster'],
            'track': ['src'],
            'iframe': ['src'],
            'object': ['data'],
            'embed': ['src'],
            'a': ['href'],
            'form': ['action'],
            'meta': ['content'],
            'input': ['src', 'value'],
            'button': ['formaction'],
            'area': ['href'],
            'base': ['href'],
            'applet': ['code'],
            'param': ['value']
        }
        
        for tag_name, attributes in tags_to_check.items():
            for element in soup.find_all(tag_name):
                for attr in attributes:
                    if element.has_attr(attr):
                        value = element[attr]
                        if value and not value.startswith(('#', 'javascript:', 'data:', 'mailto:', 'tel:')):
                            full_url = urljoin(self.target_url, value)
                            all_resources.append({
                                'url': full_url,
                                'element': element,
                                'attr': attr,
                                'original': value
                            })
        
        # Find CSS url() references
        css_pattern = r'url\([\'"]?(.*?)[\'"]?\)'
        style_elements = soup.find_all('style')
        for style in style_elements:
            if style.string:
                for match in re.finditer(css_pattern, style.string):
                    url = match.group(1)
                    if url and not url.startswith(('#', 'data:', 'javascript:')):
                        full_url = urljoin(self.target_url, url)
                        all_resources.append({
                            'url': full_url,
                            'element': style,
                            'attr': None,
                            'original': url
                        })
        
        # Find inline CSS href
        for element in soup.find_all(style=True):
            if 'background-image' in element.get('style', ''):
                for match in re.finditer(css_pattern, element['style']):
                    url = match.group(1)
                    if url and not url.startswith(('#', 'data:')):
                        full_url = urljoin(self.target_url, url)
                        all_resources.append({
                            'url': full_url,
                            'element': element,
                            'attr': 'style',
                            'original': url
                        })
        
        # Stage 4: Extract APIs from JavaScript and HTML
        console.print(f"[yellow]🔌 Extracting API endpoints...[/yellow]")
        all_apis = self._extract_apis_from_javascript(main_html, self.target_url)
        self.extracted_data['apis'].extend(all_apis)
        
        # Stage 5: Extract Firebase configs
        console.print(f"[yellow]🔥 Extracting Firebase configurations...[/yellow]")
        firebase_configs = self._extract_firebase_configs(main_html)
        self.extracted_data['firebase'].extend(firebase_configs)
        
        # Stage 6: Extract PHP resources
        console.print(f"[yellow]🐘 Extracting PHP resources...[/yellow]")
        php_resources = self._extract_php_resources(main_html, self.target_url)
        self.extracted_data['php_files'].extend(php_resources)
        
        # Stage 7: Download ALL resources
        console.print(f"[yellow]📦 Downloading {len(all_resources)} resources (multi-threaded)...[/yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=False
        ) as progress:
            download_task = progress.add_task(
                f"[bold cyan]⬇️ Downloading resources...", 
                total=len(all_resources) + len(self.extracted_data['php_files']) + len(self.extracted_data['apis'])
            )
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                
                # Download HTML resources
                for resource in all_resources:
                    url = resource['url']
                    ext = self._get_file_extension(url)
                    category = self._categorize_file(ext, url)
                    
                    # Generate filename
                    filename = self._generate_filename(url, category, len(self.downloaded_files) + 1)
                    file_path = self.temp_dir / category / filename
                    
                    # Submit download
                    future = executor.submit(self.download_file, url, file_path, self.headers)
                    futures.append(future)
                
                # Download PHP resources
                for php_url in self.extracted_data['php_files']:
                    ext = self._get_file_extension(php_url)
                    filename = self._generate_filename(php_url, 'php', len(self.downloaded_files) + 1)
                    file_path = self.temp_dir / 'php' / filename
                    future = executor.submit(self.download_file, php_url, file_path, self.headers)
                    futures.append(future)
                
                # Download API endpoints
                for api_url in self.extracted_data['apis'][:100]:  # Limit to 100 APIs
                    if api_url.startswith('http'):
                        ext = '.json'
                        filename = self._generate_filename(api_url, 'api', len(self.downloaded_files) + 1)
                        file_path = self.temp_dir / 'api' / filename
                        future = executor.submit(self.download_file, api_url, file_path, self.headers)
                        futures.append(future)
                
                # Process completed downloads
                for future in as_completed(futures):
                    progress.advance(download_task)
                    
        # Stage 8: Process CSS files and extract more resources
        console.print(f"[yellow]🎨 Processing CSS files...[/yellow]")
        css_files = list((self.temp_dir / "css").glob("*.css"))
        
        for css_file in css_files:
            try:
                css_content = css_file.read_text(encoding='utf-8', errors='ignore')
                css_urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', css_content)
                
                for css_url in css_urls:
                    if css_url and not css_url.startswith(('#', 'data:', 'javascript:')):
                        full_url = urljoin(self.target_url, css_url)
                        ext = self._get_file_extension(full_url)
                        category = self._categorize_file(ext, full_url)
                        filename = self._generate_filename(full_url, category, len(self.downloaded_files) + 1)
                        file_path = self.temp_dir / category / filename
                        
                        self.download_file(full_url, file_path, self.headers)
                        
                        # Update CSS content
                        css_content = css_content.replace(css_url, category + '/' + filename)
                
                css_file.write_text(css_content, encoding='utf-8')
            except Exception as e:
                console.print(f"[red]❌ Error processing CSS {css_file}: {e}[/red]")
        
        # Stage 9: Save all extracted data to files
        console.print(f"[yellow]💾 Saving extracted data...[/yellow]")
        
        # Save APIs to file
        if self.extracted_data['apis']:
            api_file = self.temp_dir / 'api' / '_extracted_apis.json'
            api_file.write_text(json.dumps(list(set(self.extracted_data['apis'])), indent=2))
            self.downloaded_files.append(api_file)
        
        # Save Firebase configs
        if self.extracted_data['firebase']:
            firebase_file = self.temp_dir / 'firebase' / '_firebase_configs.json'
            firebase_file.write_text(json.dumps(list(set(self.extracted_data['firebase'])), indent=2))
            self.downloaded_files.append(firebase_file)
        
        # Save PHP resources
        if self.extracted_data['php_files']:
            php_file = self.temp_dir / 'php' / '_php_resources.json'
            php_file.write_text(json.dumps(list(set(self.extracted_data['php_files'])), indent=2))
            self.downloaded_files.append(php_file)
        
        # Save hidden directories
        if self.hidden_dirs:
            hidden_file = self.temp_dir / 'hidden' / '_hidden_directories.txt'
            hidden_file.write_text('\n'.join(self.hidden_dirs))
            self.downloaded_files.append(hidden_file)
        
        # Stage 10: Create master summary
        summary = {
            'target_url': self.target_url,
            'site_name': self.site_name,
            'extraction_date': datetime.now().isoformat(),
            'files_extracted': len(self.downloaded_files),
            'api_endpoints': len(self.extracted_data['apis']),
            'firebase_configs': len(self.extracted_data['firebase']),
            'php_files': len(self.extracted_data['php_files']),
            'hidden_directories': len(self.hidden_dirs),
            'total_size': 0
        }
        
        summary_file = self.temp_dir / '_extraction_summary.json'
        summary_file.write_text(json.dumps(summary, indent=2))
        self.downloaded_files.append(summary_file)
        
        # Stage 11: Create ZIP archive
        console.print(f"[bold green]📦 Creating ZIP archive...[/bold green]")
        zip_filename = f"{CUSTOM_PREFIX}{self.site_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = self.output_dir / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in self.temp_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.temp_dir)
                    zipf.write(file_path, arcname)
        
        # Clean up temp directory
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass
        
        zip_size = zip_path.stat().st_size
        summary['total_size'] = zip_size
        
        return str(zip_path), zip_size, summary

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
        title="[bold red] ULTIMATE WEBSITE EXTRACTOR v5.0 Pro [/bold red]",
        subtitle="[bold yellow] Developer: @Rolexconfigyt [/bold yellow]"
    ))
    
    desc = Text("🔥 Complete Website Extraction Engine\n"
                "📦 HTML | CSS | JavaScript | PHP | APIs | Firebase | Databases\n"
                "🔐 Configs | Secrets | Hidden Directories | All Resources\n"
                "💾 10GB+ Capacity | 50x Multi-threaded | Smart Detection", 
                style="bold green", justify="center")
    console.print(Panel(desc, box=box.ROUNDED, border_style="green"))
    console.print()

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def display_summary(summary):
    table = Table(title="📊 Extraction Summary", box=box.HEAVY)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    
    table.add_row("🎯 Target URL", summary['target_url'])
    table.add_row("📁 Site Name", summary['site_name'])
    table.add_row("📄 Files Extracted", str(summary['files_extracted']))
    table.add_row("🔌 API Endpoints Found", str(summary['api_endpoints']))
    table.add_row("🔥 Firebase Configs", str(summary['firebase_configs']))
    table.add_row("🐘 PHP Resources", str(summary['php_files']))
    table.add_row("🔍 Hidden Directories", str(summary['hidden_directories']))
    table.add_row("💾 Total Size", format_size(summary['total_size']))
    table.add_row("📅 Extraction Date", summary['extraction_date'])
    
    console.print(table)

def main():
    console.clear()
    display_banner()
    
    target_url = Prompt.ask("[bold green]🔗 Enter Target Website URL[/bold green]")
    
    if not target_url.startswith("http"):
        target_url = "https://" + target_url
        console.print(f"[dim]Auto-added https:// -> {target_url}[/dim]\n")
    
    scraper = UltimateWebsiteScraper(target_url)
    zip_file, size, summary = scraper.scrape_website()
    
    if zip_file:
        display_summary(summary)
        
        console.print(Panel(
            f"🎉 [bold green]WEBSITE COMPLETELY EXTRACTED![/bold green] 🎉\n\n"
            f"🎯 [bold cyan]Target:[/bold cyan] [yellow]{target_url}[/yellow]\n"
            f"📦 [bold cyan]Package:[/bold cyan] [bold green]{Path(zip_file).name}[/bold green]\n"
            f"📏 [bold cyan]Size:[/bold cyan] [bold yellow]{format_size(size)}[/bold yellow]\n"
            f"📁 [bold cyan]Total Files:[/bold cyan] [bold magenta]{summary['files_extracted']}[/bold magenta]\n"
            f"🔌 [bold cyan]APIs Found:[/bold cyan] [bold magenta]{summary['api_endpoints']}[/bold magenta]\n"
            f"🔥 [bold cyan]Firebase Configs:[/bold cyan] [bold magenta]{summary['firebase_configs']}[/bold magenta]\n"
            f"🐘 [bold cyan]PHP Files:[/bold cyan] [bold magenta]{summary['php_files']}[/bold magenta]\n\n"
            f"📂 [bold yellow]Location:[/bold yellow]\n[bold green]{Path(zip_file).absolute()}[/bold green]",
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
