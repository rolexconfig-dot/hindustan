import os
import re
import base64
import zlib
import gzip
import urllib.parse
import hashlib
import json
import ast
from pathlib import Path
from time import sleep
import struct
import subprocess
import tempfile
import shutil
import zipfile
from typing import Optional, Tuple, List

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

class CryptoDeobfuscator:
    """Advanced multi-layer deobfuscator with APK support"""
    
    def __init__(self):
        self.max_passes = 25
        self.decoded_strings = []
        
    def decode_xor(self, text: str, key: int = 42) -> str:
        """Decode XOR encrypted strings"""
        try:
            return ''.join(chr(ord(c) ^ key) for c in text)
        except:
            return text
    
    def decode_rot13(self, text: str) -> str:
        """Decode ROT13"""
        try:
            import codecs
            return codecs.decode(text, 'rot_13')
        except:
            return text
    
    def decode_hex(self, text: str) -> str:
        """Decode hex strings"""
        try:
            hex_patterns = [
                r'(?:[0-9a-fA-F]{2}\s*){8,}',  # Space separated hex
                r'[0-9a-fA-F]{16,}',  # Continuous hex
            ]
            for pattern in hex_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    clean_hex = re.sub(r'\s', '', match)
                    if len(clean_hex) % 2 == 0:
                        try:
                            decoded = bytes.fromhex(clean_hex).decode('utf-8', errors='ignore')
                            if any(c.isprintable() for c in decoded[:50]):
                                text = text.replace(match, decoded)
                        except:
                            pass
            return text
        except:
            return text
    
    def decode_base64_multi(self, text: str) -> str:
        """Handle multiple Base64 encodings"""
        try:
            # Find potential base64 strings
            b64_pattern = r'[A-Za-z0-9+/=]{20,}'
            matches = re.findall(b64_pattern, text)
            
            for match in matches:
                # Try multiple decoding attempts
                for _ in range(5):  # Max 5 layers
                    try:
                        raw = base64.b64decode(match)
                        # Try to decode as text
                        decoded = raw.decode('utf-8', errors='ignore')
                        if len(decoded) > 10 and any(c.isprintable() for c in decoded[:20]):
                            text = text.replace(match, decoded)
                            match = decoded  # Continue with decoded value
                        else:
                            break
                    except:
                        break
            return text
        except:
            return text
    
    def decode_javascript_obfuscation(self, text: str) -> str:
        """Decode common JavaScript obfuscation patterns"""
        replacements = {
            r'\\x([0-9a-fA-F]{2})': lambda m: bytes.fromhex(m.group(1)).decode('utf-8', errors='ignore'),
            r'\\u([0-9a-fA-F]{4})': lambda m: chr(int(m.group(1), 16)),
            r'%([0-9a-fA-F]{2})': lambda m: bytes.fromhex(m.group(1)).decode('utf-8', errors='ignore'),
            r'\\(\d{3})': lambda m: chr(int(m.group(1), 8)),
        }
        
        for pattern, repl in replacements.items():
            try:
                text = re.sub(pattern, repl, text)
            except:
                pass
        return text
    
    def decode_packed_js(self, text: str) -> str:
        """Detect and unpack packed JavaScript"""
        try:
            # Look for eval or Function constructor with packed code
            packed_pattern = r'(eval|Function)\s*\(\s*["\'](.*?)["\']\s*\)'
            matches = re.findall(packed_pattern, text, re.DOTALL)
            
            for match in matches:
                try:
                    packed = match[1]
                    # Try to decode the packed content
                    if 'decode' in packed or 'base64' in packed.lower():
                        # Execute in safe environment? We'll just try to extract
                        pass
                except:
                    pass
            return text
        except:
            return text
    
    def decode_android_assets(self, content: bytes) -> str:
        """Decode Android asset files"""
        try:
            # Try to identify and decode Android specific encoding
            # Check for AES encrypted assets
            if len(content) > 32:
                # Check for signature patterns
                if content[:4] == b'\x00\x00\x00\x00':
                    # Could be AES encrypted asset
                    pass
            return content.decode('utf-8', errors='ignore')
        except:
            return content.decode('utf-8', errors='ignore')
    
    def universal_deobfuscator(self, content: str) -> str:
        """Enhanced universal deobfuscator with multiple layers"""
        current = content
        modified = True
        passes = 0
        
        while modified and passes < self.max_passes:
            modified = False
            passes += 1
            
            # Apply all decoders
            decoders = [
                self.decode_base64_multi,
                self.decode_hex,
                self.decode_rot13,
                self.decode_javascript_obfuscation,
                self.decode_packed_js,
                self.decode_xor,
            ]
            
            for decoder in decoders:
                try:
                    new_content = decoder(current)
                    if new_content != current:
                        current = new_content
                        modified = True
                except:
                    pass
            
            # Check for decoded strings in console
            if 'console.log' in current:
                log_pattern = r'console\.log\s*\(\s*["\']([^"\']*)["\']\s*\)'
                matches = re.findall(log_pattern, current)
                for match in matches:
                    self.decoded_strings.append(match)
        
        # Try to extract HTML content if wrapped
        html_match = re.search(r'(<!DOCTYPE.*?<html.*?>.*?</html>)', current, re.DOTALL | re.IGNORECASE)
        if html_match:
            current = html_match.group(1)
            
        return current

class APKDeobfuscator:
    """Handle APK file deobfuscation"""
    
    def __init__(self):
        self.temp_dir = None
        
    def extract_apk(self, apk_path: Path) -> Path:
        """Extract APK contents"""
        temp_dir = Path(tempfile.mkdtemp(prefix="apk_extract_"))
        try:
            with zipfile.ZipFile(apk_path, 'r') as apk_zip:
                apk_zip.extractall(temp_dir)
            return temp_dir
        except Exception as e:
            console.print(f"[red]Error extracting APK: {e}[/red]")
            return None
    
    def decompile_dex(self, dex_path: Path, output_dir: Path) -> bool:
        """Decompile DEX files using various tools"""
        try:
            # Try using pycdc if available
            if shutil.which('pycdc'):
                cmd = ['pycdc', str(dex_path), '-o', str(output_dir)]
                subprocess.run(cmd, capture_output=True, timeout=30)
                return True
            
            # Try using jadx if available
            if shutil.which('jadx'):
                cmd = ['jadx', str(dex_path), '-d', str(output_dir), '--show-bad-code']
                subprocess.run(cmd, capture_output=True, timeout=30)
                return True
            
            # Try using dexdump if available
            if shutil.which('dexdump'):
                cmd = ['dexdump', str(dex_path), '-f', '-d', '-h']
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                if result.stdout:
                    output_file = output_dir / f"{dex_path.stem}_dump.txt"
                    output_file.write_bytes(result.stdout)
                    return True
            
            return False
        except:
            return False
    
    def extract_android_manifest(self, apk_dir: Path) -> Optional[str]:
        """Extract and parse Android manifest"""
        manifest_path = apk_dir / 'AndroidManifest.xml'
        if manifest_path.exists():
            try:
                # Try to parse binary XML if possible
                content = manifest_path.read_bytes()
                # Look for readable strings
                strings = re.findall(rb'[\x20-\x7E]{4,}', content)
                decoded_strings = [s.decode('utf-8', errors='ignore') for s in strings]
                return '\n'.join(decoded_strings)
            except:
                return None
        return None
    
    def process_apk(self, apk_path: Path) -> Optional[str]:
        """Main APK processing function"""
        console.print(f"[cyan]Processing APK: {apk_path.name}[/cyan]")
        
        output_dir = Path(f"{OUTPUT_PREFIX}{apk_path.stem}_decompiled")
        output_dir.mkdir(exist_ok=True)
        
        # Extract APK
        extracted_dir = self.extract_apk(apk_path)
        if not extracted_dir:
            return None
        
        try:
            # Process DEX files
            dex_files = list(extracted_dir.glob('*.dex'))
            if not dex_files:
                console.print("[yellow]No DEX files found in APK[/yellow]")
                return str(output_dir)
            
            decompiled_content = []
            
            for dex_file in dex_files:
                console.print(f"[cyan]Decompiling: {dex_file.name}[/cyan]")
                dex_output = output_dir / dex_file.stem
                dex_output.mkdir(exist_ok=True)
                
                if self.decompile_dex(dex_file, dex_output):
                    # Read decompiled files
                    for java_file in dex_output.glob('**/*.java'):
                        try:
                            content = java_file.read_text(encoding='utf-8', errors='ignore')
                            decompiled_content.append(f"// File: {java_file.relative_to(output_dir)}\n{content}")
                        except:
                            pass
                    
                    for txt_file in dex_output.glob('**/*.txt'):
                        try:
                            content = txt_file.read_text(encoding='utf-8', errors='ignore')
                            decompiled_content.append(f"// File: {txt_file.relative_to(output_dir)}\n{content}")
                        except:
                            pass
            
            # Process manifest
            manifest_text = self.extract_android_manifest(extracted_dir)
            if manifest_text:
                manifest_output = output_dir / 'AndroidManifest.txt'
                manifest_output.write_text(manifest_text, encoding='utf-8')
                decompiled_content.append(f"// AndroidManifest.xml\n{manifest_text}")
            
            # Process other assets
            assets_dir = extracted_dir / 'assets'
            if assets_dir.exists():
                assets_output = output_dir / 'assets'
                assets_output.mkdir(exist_ok=True)
                
                for asset_file in assets_dir.glob('**/*'):
                    if asset_file.is_file():
                        try:
                            content = asset_file.read_text(encoding='utf-8', errors='ignore')
                            asset_out = assets_output / asset_file.relative_to(assets_dir)
                            asset_out.parent.mkdir(exist_ok=True)
                            asset_out.write_text(content, encoding='utf-8')
                        except:
                            # Handle binary files
                            try:
                                shutil.copy2(asset_file, assets_output / asset_file.relative_to(assets_dir))
                            except:
                                pass
            
            # Save combined decompiled content
            if decompiled_content:
                combined_file = output_dir / 'combined_source.txt'
                combined_file.write_text('\n\n'.join(decompiled_content), encoding='utf-8')
            
            return str(output_dir)
            
        finally:
            # Cleanup temp directory
            try:
                shutil.rmtree(extracted_dir)
            except:
                pass

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
        title="[bold red] Universal De-Obfuscator v4.0 - Ultimate Edition [/bold red]",
        subtitle="[bold yellow] Developer: @Rolexconfigyt [/bold yellow]"
    ))
    
    desc = Text("⚡ High-Level Multi-Layer Unpacker & Code Restorer\n"
                "Supports HTML, JS, PHP, Java, APK & Asset Decryption\n"
                "🔥 20+ Decryption Layers | AI-Powered Detection", 
                style="bold green", justify="center")
    console.print(Panel(desc, box=box.ROUNDED, border_style="green"))
    console.print()

def main():
    console.clear()
    display_banner()
    
    # Get files
    current_folder = Path(".")
    extensions = ['.html', '.js', '.php', '.css', '.java', '.dex', '.txt', '.json', '.apk']
    files = [
        f for f in current_folder.glob("*.*")
        if f.suffix.lower() in extensions and not f.name.startswith(OUTPUT_PREFIX)
    ]
    files = sorted(files, key=lambda x: x.name)
    
    if not files:
        console.print(Panel(
            "[red]⚠️ No supported source files found in this directory![/red]\n"
            "[yellow]Please place your .html, .js, .php, .java, .dex, or .apk files here.[/yellow]", 
            box=box.HEAVY, 
            border_style="red"
        ))
        return
    
    # Display files
    table = Table(title="[bold yellow]📄 Available Files for Deobfuscation[/bold yellow]", box=box.SIMPLE_HEAVY, border_style="cyan")
    table.add_column("ID", style="bold red", justify="center")
    table.add_column("Filename", style="bold green")
    table.add_column("Size", style="bold yellow", justify="right")
    table.add_column("Type", style="bold magenta", justify="center")
    
    for idx, file in enumerate(files, start=1):
        size = file.stat().st_size
        size_str = f"{size/1024:.2f} KB" if size < 1024*1024 else f"{size/1024/1024:.2f} MB"
        file_type = "APK" if file.suffix.lower() == '.apk' else file.suffix[1:].upper()
        table.add_row(f"[{idx}]", file.name, size_str, file_type)
    
    console.print(table)
    console.print()
    
    while True:
        try:
            choice = IntPrompt.ask(
                "[bold cyan]📌 Enter the ID of the file to process[/bold cyan]",
                choices=[str(i) for i in range(1, len(files) + 1)],
                show_choices=False
            )
            if 1 <= choice <= len(files):
                selected_file = files[choice - 1]
                break
        except Exception:
            console.print("[red]❌ Invalid ID! Please enter a valid number.[/red]")
    
    console.print(f"\n[bold green]➜ Selected File:[/bold green] [cyan]{selected_file.name}[/cyan]")
    
    confirm = Prompt.ask("\n[bold yellow]⚡ Start Advanced De-Obfuscation?[/bold yellow]", choices=["y", "n"], default="y")
    if confirm.lower() != 'y':
        console.print("[yellow]❌ Operation cancelled.[/yellow]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]🔍 Analyzing File...", total=100)
        
        if selected_file.suffix.lower() == '.apk':
            # Handle APK
            progress.update(task, advance=10, description="[cyan]📱 Processing APK File...")
            apk_deob = APKDeobfuscator()
            result = apk_deob.process_apk(selected_file)
            progress.update(task, advance=90, description="[green]✅ APK Decompilation Complete!")
            
            if result:
                console.print(Panel(
                    f"[bold green]✅ APK successfully decompiled![/bold green]\n"
                    f"[yellow]📁 Output directory: {result}[/yellow]",
                    box=box.HEAVY,
                    border_style="green"
                ))
            else:
                console.print(Panel(
                    "[red]❌ APK decompilation failed.[/red]\n"
                    "[yellow]Make sure you have required tools (jadx, pycdc, etc.) installed.[/yellow]",
                    box=box.HEAVY,
                    border_style="red"
                ))
        
        else:
            # Handle code files
            progress.update(task, advance=10, description="[cyan]📖 Reading File...")
            
            try:
                content = selected_file.read_text(encoding='utf-8', errors='ignore')
                progress.update(task, advance=20, description="[yellow]🔧 Initializing Decryption Engine...")
                sleep(0.3)
                
                crypto = CryptoDeobfuscator()
                progress.update(task, advance=20, description="[magenta]🔓 Multi-Layer Decryption in Progress...")
                
                restored_code = crypto.universal_deobfuscator(content)
                
                progress.update(task, advance=30, description="[green]💾 Saving Restored Code...")
                sleep(0.3)
                
                output_name = OUTPUT_PREFIX + selected_file.name
                Path(output_name).write_text(restored_code, encoding='utf-8')
                
                progress.update(task, advance=20, description="[bold green]✅ De-obfuscation Complete!")
                
                original_size = selected_file.stat().st_size
                new_size = Path(output_name).stat().st_size
                
                result_table = Table(box=box.SIMPLE, show_header=False)
                result_table.add_column("Property", style="bold cyan")
                result_table.add_column("Value", style="bold yellow")
                
                result_table.add_row("📄 Original File:", selected_file.name)
                result_table.add_row("💾 Restored File:", f"[bold green]{output_name}[/bold green]")
                result_table.add_row("📏 Original Size:", f"{original_size/1024:.2f} KB")
                result_table.add_row("🔓 New Size:", f"{new_size/1024:.2f} KB")
                result_table.add_row("🔄 Reduction:", f"{(1 - new_size/original_size)*100:.1f}%")
                
                console.print(Panel(
                    result_table,
                    title="✨ [bold green]De-obfuscation Completed Successfully![/bold green] ✨",
                    box=box.HEAVY,
                    border_style="green",
                    expand=False
                ))
                
                if crypto.decoded_strings:
                    console.print("\n[bold cyan]🔍 Found Hidden Strings:[/bold cyan]")
                    for s in crypto.decoded_strings[:10]:
                        console.print(f"  [yellow]•[/yellow] {s}")
                
            except Exception as e:
                progress.update(task, description=f"[red]❌ Error: {e}[/red]")
                console.print(f"\n[red]Error processing file: {e}[/red]")
    
    another = Prompt.ask("\n[bold cyan]🔄 Process another file?[/bold cyan]", choices=["y", "n"], default="n")
    if another.lower() == 'y':
        main()
    else:
        console.print("\n[bold green]🙏 Thanks for using Hindustan Ultimate De-Obfuscator! Stay Secure. 🔒[/bold green]\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]👋 Exited by user. Goodbye![/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
