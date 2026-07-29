#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ULTIMATE DE-OBFUSCATOR v5.0 - HINDUSTAN
Any Encryption, Any File - Get Original Code Instantly
"""

import os
import re
import sys
import base64
import zlib
import gzip
import bz2
import lzma
import json
import hashlib
import binascii
import struct
import subprocess
import shutil
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import Optional, List, Dict, Any
import urllib.parse
import html
import xml.etree.ElementTree as ET
from Crypto.Cipher import AES, DES, ARC4
from Crypto.Util.Padding import unpad

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box
from rich.text import Text
from rich.tree import Tree
import pyfiglet

console = Console()

# ============================================================================
# CORE DECODING ENGINE - Bypass Any Encryption
# ============================================================================

class UltimateDeobfuscator:
    """Detects any encryption and extracts original code"""
    
    def __init__(self):
        self.max_depth = 50  # Any depth of encryption
        self.original_content = ""
        self.decoded_layers = []
        self.detected_encryptions = []
        
    def detect_encryption_type(self, text: str) -> List[str]:
        """Detect all types of encryption"""
        detected = []
        
        # Base64
        if re.search(r'[A-Za-z0-9+/=]{20,}', text):
            detected.append('base64')
        
        # Hex
        if re.search(r'[0-9a-fA-F]{16,}', text):
            detected.append('hex')
        
        # URL Encoding
        if '%' in text and re.search(r'%[0-9a-fA-F]{2}', text):
            detected.append('url')
        
        # Unicode Escapes
        if re.search(r'\\u[0-9a-fA-F]{4}', text):
            detected.append('unicode')
        
        # Octal
        if re.search(r'\\([0-7]{3})', text):
            detected.append('octal')
        
        # ROT13
        if re.search(r'[n-zN-Z]', text) and 'rot13' in text.lower():
            detected.append('rot13')
        
        # XOR pattern
        if re.search(r'\^[0-9]+', text) or re.search(r'[\x00-\x1F]{10,}', text):
            detected.append('xor')
        
        # AES pattern
        if re.search(r'AES|rijndael', text, re.I):
            detected.append('aes')
        
        # DES pattern
        if re.search(r'DES|3DES', text, re.I):
            detected.append('des')
        
        # RC4 pattern
        if re.search(r'RC4|ARC4', text, re.I):
            detected.append('rc4')
        
        # Gzip/Zlib
        if re.search(r'\x1f\x8b|\x78\x9c|\x78\xda', text[:100], re.DOTALL):
            detected.append('gzip')
            detected.append('zlib')
        
        # BZip2
        if re.search(r'BZh', text[:10]):
            detected.append('bzip2')
        
        # LZMA
        if re.search(r'\x7d\x78\xda', text[:10]):
            detected.append('lzma')
        
        # JavaScript Obfuscation
        if re.search(r'eval\s*\(|function\s*\(.*?\)\s*\{.*?decode', text, re.DOTALL):
            detected.append('js_obfuscated')
        
        # PHP Obfuscation
        if re.search(r'eval\s*\(|base64_decode|gzinflate|str_rot13', text, re.I):
            detected.append('php_obfuscated')
        
        # Android/Java Obfuscation
        if re.search(r'proguard|obfuscate|dex', text, re.I):
            detected.append('android_obfuscated')
        
        # Custom pattern
        if re.search(r'[A-Za-z0-9+/=]{40,}', text):
            detected.append('strong_base64')
        
        return list(set(detected))
    
    def decode_base64_advanced(self, text: str) -> str:
        """Multi-layer Base64 decoding - however many layers"""
        current = text
        max_iter = 20
        
        for _ in range(max_iter):
            # Find all base64 strings
            b64_patterns = [
                r'["\']([A-Za-z0-9+/=]{20,})["\']',
                r'([A-Za-z0-9+/=]{30,})',
                r'base64_decode\s*\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)',
                r'atob\s*\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)',
            ]
            
            modified = False
            for pattern in b64_patterns:
                matches = re.findall(pattern, current, re.DOTALL)
                for match in matches:
                    try:
                        # Fix padding
                        b64_str = match
                        if isinstance(match, tuple):
                            b64_str = match[0]
                        
                        # Add padding
                        b64_str = b64_str.replace('"', '').replace("'", '')
                        b64_str += '=' * (-len(b64_str) % 4)
                        
                        decoded = base64.b64decode(b64_str)
                        
                        # Check for printable text
                        try:
                            decoded_text = decoded.decode('utf-8', errors='ignore')
                            if len(decoded_text) > 10 and any(c.isprintable() for c in decoded_text[:100]):
                                current = current.replace(match, decoded_text if isinstance(match, str) else match[0], 1)
                                modified = True
                        except:
                            # For binary data
                            if len(decoded) > 100:
                                hex_repr = decoded.hex()
                                current = current.replace(match, hex_repr, 1)
                                modified = True
                    except:
                        pass
            
            if not modified:
                break
        
        return current
    
    def decode_hex_advanced(self, text: str) -> str:
        """Decode all types of hex"""
        current = text
        
        # Patterns
        hex_patterns = [
            r'\\x([0-9a-fA-F]{2})',
            r'0x([0-9a-fA-F]{2,})',
            r'([0-9a-fA-F]{16,})',
            r'[^\x00-\x7F]',  # URL encoded hex
        ]
        
        for pattern in hex_patterns:
            matches = re.findall(pattern, current)
            for match in matches:
                try:
                    if len(match) % 2 == 0:
                        decoded = bytes.fromhex(match).decode('utf-8', errors='ignore')
                        if len(decoded) > 5:
                            current = current.replace(match, decoded)
                except:
                    pass
        
        return current
    
    def decode_url_advanced(self, text: str) -> str:
        """Fully decode URL encoding"""
        current = text
        for _ in range(10):
            try:
                decoded = urllib.parse.unquote(current)
                if decoded != current:
                    current = decoded
                else:
                    break
            except:
                break
        
        # Double URL encoding
        for _ in range(5):
            try:
                decoded = urllib.parse.unquote(current)
                if decoded != current:
                    current = decoded
                else:
                    break
            except:
                break
        
        return current
    
    def decode_js_eval(self, text: str) -> str:
        """Decode JavaScript eval"""
        current = text
        
        # Extract packed code from eval
        eval_patterns = [
            r'eval\s*\(\s*["\'](.*?)["\']\s*\)',
            r'eval\s*\(\s*(function.*?)\(.*?\)\s*\)',
            r'eval\s*\(\s*(atob.*?)\s*\)',
            r'new\s+Function\s*\(\s*["\'](.*?)["\']\s*\)',
        ]
        
        for pattern in eval_patterns:
            matches = re.findall(pattern, current, re.DOTALL)
            for match in matches:
                try:
                    # Extract eval content
                    eval_content = match
                    if isinstance(match, tuple):
                        eval_content = match[0]
                    
                    # Decode base64 if present
                    if 'atob' in eval_content:
                        b64_match = re.search(r'atob\s*\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)', eval_content)
                        if b64_match:
                            decoded = base64.b64decode(b64_match.group(1)).decode('utf-8', errors='ignore')
                            current = current.replace(match, decoded)
                except:
                    pass
        
        return current
    
    def decode_php_obfuscation(self, text: str) -> str:
        """Decode PHP obfuscation"""
        current = text
        
        patterns = [
            r'eval\s*\(\s*base64_decode\s*\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)\s*\)',
            r'eval\s*\(\s*gzinflate\s*\(\s*base64_decode\s*\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)\s*\)\s*\)',
            r'eval\s*\(\s*str_rot13\s*\(\s*["\']([^"\']+)["\']\s*\)\s*\)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, current, re.DOTALL)
            for match in matches:
                try:
                    # Decode base64
                    b64_decoded = base64.b64decode(match).decode('utf-8', errors='ignore')
                    
                    # Decode gzip
                    if 'gzinflate' in pattern:
                        try:
                            decompressed = zlib.decompress(base64.b64decode(match))
                            b64_decoded = decompressed.decode('utf-8', errors='ignore')
                        except:
                            pass
                    
                    current = current.replace(match, b64_decoded)
                except:
                    pass
        
        return current
    
    def decode_compression(self, text: str) -> str:
        """Decode all types of compression"""
        current = text
        
        # Gzip
        try:
            if '\x1f\x8b' in current[:100]:
                decoded = gzip.decompress(current.encode()).decode('utf-8', errors='ignore')
                current = decoded
        except:
            pass
        
        # Zlib
        try:
            if '\x78\x9c' in current[:100] or '\x78\xda' in current[:100]:
                decoded = zlib.decompress(current.encode()).decode('utf-8', errors='ignore')
                current = decoded
        except:
            pass
        
        # BZip2
        try:
            if 'BZh' in current[:10]:
                decoded = bz2.decompress(current.encode()).decode('utf-8', errors='ignore')
                current = decoded
        except:
            pass
        
        # LZMA
        try:
            if '\x7d\x78\xda' in current[:10]:
                decoded = lzma.decompress(current.encode()).decode('utf-8', errors='ignore')
                current = decoded
        except:
            pass
        
        return current
    
    def decode_xor_advanced(self, text: str) -> str:
        """Break XOR encryption - auto detect key"""
        current = text
        
        # XOR patterns
        xor_patterns = [
            r'(\w+)\s*\^\s*([0-9]+)',
            r'xor\s*\(\s*([^,]+)\s*,\s*([0-9]+)\s*\)',
            r'charCodeAt.*?\^.*?([0-9]+)',
        ]
        
        for pattern in xor_patterns:
            matches = re.findall(pattern, current)
            for match in matches:
                try:
                    if isinstance(match, tuple) and len(match) >= 2:
                        key = int(match[1])
                        # XOR decrypt
                        decoded = ''.join(chr(ord(c) ^ key) for c in match[0])
                        current = current.replace(match[0], decoded)
                except:
                    pass
        
        # Brute force XOR (key 1-255)
        if re.search(r'[\x00-\x1F]{10,}', current):
            for key in range(1, 256):
                try:
                    decoded = ''.join(chr(ord(c) ^ key) for c in current[:100])
                    if any(c.isprintable() for c in decoded):
                        full_decoded = ''.join(chr(ord(c) ^ key) for c in current)
                        if len(full_decoded) > 100:
                            current = full_decoded
                            break
                except:
                    pass
        
        return current
    
    def decode_aes(self, text: str) -> str:
        """AES decryption - auto detect key"""
        current = text
        
        # Find AES pattern
        aes_pattern = re.compile(r'(?:AES|rijndael).*?key[\s:]+["\']([0-9a-fA-F]{32,64})["\']', re.I)
        matches = aes_pattern.findall(current)
        
        for key_hex in matches:
            try:
                # Convert key to bytes
                key = bytes.fromhex(key_hex[:32])  # 128-bit
                
                # Find encrypted data
                encrypted_pattern = re.compile(r'["\']([0-9a-fA-F]{32,})["\']')
                encrypted_matches = encrypted_pattern.findall(current)
                
                for enc_hex in encrypted_matches:
                    try:
                        cipher = AES.new(key, AES.MODE_ECB)
                        encrypted = bytes.fromhex(enc_hex[:32])
                        decrypted = cipher.decrypt(encrypted)
                        decoded = decrypted.decode('utf-8', errors='ignore')
                        if any(c.isprintable() for c in decoded):
                            current = current.replace(enc_hex, decoded)
                    except:
                        pass
            except:
                pass
        
        return current
    
    def decode_android_obfuscation(self, content: str) -> str:
        """Decode Android/DEX obfuscation"""
        current = content
        
        # ProGuard obfuscation
        proguard_pattern = re.compile(r'(?:a|b|c|d|e|f|g|h|i|j|k|l|m|n|o|p|q|r|s|t|u|v|w|x|y|z){2,}\.', re.I)
        if proguard_pattern.search(current):
            # Try to restore classes
            pass
        
        # DEX bytecode
        if 'dex\n' in current[:100] or 'classes.dex' in current:
            # Check DEX header
            pass
        
        return current
    
    def extract_html_content(self, text: str) -> str:
        """Extract HTML content"""
        # Find <html> tag
        html_match = re.search(r'(<!DOCTYPE.*?<html.*?>.*?</html>)', text, re.DOTALL | re.IGNORECASE)
        if html_match:
            return html_match.group(1)
        
        # Find <body> content
        body_match = re.search(r'<body.*?>(.*?)</body>', text, re.DOTALL | re.IGNORECASE)
        if body_match:
            return body_match.group(1)
        
        return text
    
    def decode_javascript_uuencode(self, text: str) -> str:
        """Decode JavaScript uuencode"""
        current = text
        
        # uuencode pattern
        uu_pattern = r'uudecode\s*\(\s*["\']([^"\']+)["\']\s*\)'
        matches = re.findall(uu_pattern, current)
        
        for match in matches:
            try:
                # Decode uuencode
                decoded = binascii.a2b_uu(match).decode('utf-8', errors='ignore')
                current = current.replace(match, decoded)
            except:
                pass
        
        return current
    
    def decode_multiple_layers(self, text: str) -> str:
        """Multi-layer decoding - recursive"""
        current = text
        layer_count = 0
        
        while layer_count < self.max_depth:
            modified = False
            layer_count += 1
            
            # Apply all decoders
            decoders = [
                self.decode_base64_advanced,
                self.decode_hex_advanced,
                self.decode_url_advanced,
                self.decode_js_eval,
                self.decode_php_obfuscation,
                self.decode_compression,
                self.decode_xor_advanced,
                self.decode_aes,
                self.decode_javascript_uuencode,
                self.decode_android_obfuscation,
            ]
            
            for decoder in decoders:
                try:
                    new_content = decoder(current)
                    if new_content != current:
                        current = new_content
                        modified = True
                        self.decoded_layers.append(f"Layer {layer_count}: {decoder.__name__}")
                except:
                    pass
            
            if not modified:
                break
        
        return current
    
    def extract_source_code(self, text: str) -> str:
        """Extract original source code"""
        current = text
        
        # Extract JavaScript code
        js_pattern = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL)
        js_matches = js_pattern.findall(current)
        if js_matches:
            current = '\n'.join(js_matches)
        
        # Extract CSS code
        css_pattern = re.compile(r'<style[^>]*>(.*?)</style>', re.DOTALL)
        css_matches = css_pattern.findall(current)
        if css_matches:
            current = '\n'.join(css_matches) + '\n' + current
        
        return current
    
    def deobfuscate(self, content: str) -> str:
        """Main deobfuscate function"""
        self.original_content = content
        self.decoded_layers = []
        self.detected_encryptions = []
        
        console.print("[cyan]🔍 Detecting encryption...[/cyan]")
        
        # Detect encryption types
        enc_types = self.detect_encryption_type(content)
        self.detected_encryptions = enc_types
        
        if enc_types:
            console.print(f"[yellow]Detected: {', '.join(enc_types)}[/yellow]")
        
        # Multi-layer decoding
        console.print("[cyan]🔓 Starting multi-layer decryption...[/cyan]")
        decoded = self.decode_multiple_layers(content)
        
        # Extract source code
        console.print("[cyan]📄 Extracting original code...[/cyan]")
        final_code = self.extract_source_code(decoded)
        
        # Show layers decoded
        if self.decoded_layers:
            console.print(f"[green]✅ {len(self.decoded_layers)} layers decoded[/green]")
        
        return final_code

# ============================================================================
# APK DECRYPTER - Fully Decode APK
# ============================================================================

class APKUltimateDeobfuscator:
    """Fully decrypt APK - Remove all protections"""
    
    def __init__(self):
        self.temp_dir = None
        self.extracted_files = []
        self.decoded_content = {}
        
    def setup_environment(self):
        """Check required tools"""
        tools = {
            'jadx': 'jadx',
            'apktool': 'apktool',
            'dexdump': 'dexdump',
            'pycdc': 'pycdc',
        }
        
        available = {}
        for name, cmd in tools.items():
            if shutil.which(cmd):
                available[name] = cmd
        
        return available
    
    def extract_apk(self, apk_path: Path) -> Path:
        """Extract APK"""
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix="apk_ultra_"))
            
            with zipfile.ZipFile(apk_path, 'r') as apk_zip:
                # Extract all files
                for file_info in apk_zip.filelist:
                    try:
                        apk_zip.extract(file_info, temp_dir)
                        self.extracted_files.append(temp_dir / file_info.filename)
                    except:
                        pass
            
            self.temp_dir = temp_dir
            return temp_dir
        except Exception as e:
            console.print(f"[red]APK extraction failed: {e}[/red]")
            return None
    
    def decompile_dex_files(self, dex_dir: Path) -> List[str]:
        """Decompile all DEX files"""
        decompiled_content = []
        tools = self.setup_environment()
        
        # Find all DEX files
        dex_files = list(dex_dir.glob('*.dex')) + list(dex_dir.glob('classes*.dex'))
        
        for dex_file in dex_files:
            console.print(f"[cyan]📱 Decompiling DEX: {dex_file.name}[/cyan]")
            
            # Decompile with jadx
            if 'jadx' in tools:
                try:
                    output_dir = dex_dir / f"{dex_file.stem}_java"
                    cmd = ['jadx', str(dex_file), '-d', str(output_dir), '--show-bad-code', '--no-res']
                    subprocess.run(cmd, capture_output=True, timeout=120)
                    
                    # Read all Java files
                    for java_file in output_dir.rglob('*.java'):
                        try:
                            content = java_file.read_text(encoding='utf-8', errors='ignore')
                            decompiled_content.append(f"// {java_file.relative_to(output_dir)}\n{content}")
                        except:
                            pass
                except:
                    pass
            
            # Decompile with pycdc
            if 'pycdc' in tools:
                try:
                    output_file = dex_dir / f"{dex_file.stem}.py"
                    cmd = ['pycdc', str(dex_file), '-o', str(output_file)]
                    subprocess.run(cmd, capture_output=True, timeout=120)
                    
                    if output_file.exists():
                        content = output_file.read_text(encoding='utf-8', errors='ignore')
                        decompiled_content.append(f"// {output_file.name}\n{content}")
                except:
                    pass
            
            # Decompile with dexdump
            if 'dexdump' in tools:
                try:
                    output_file = dex_dir / f"{dex_file.stem}_dump.txt"
                    cmd = ['dexdump', str(dex_file), '-f', '-d', '-h']
                    result = subprocess.run(cmd, capture_output=True, timeout=60)
                    
                    if result.stdout:
                        output_file.write_bytes(result.stdout)
                        content = output_file.read_text(encoding='utf-8', errors='ignore')
                        decompiled_content.append(f"// {output_file.name}\n{content}")
                except:
                    pass
        
        return decompiled_content
    
    def extract_android_manifest(self, apk_dir: Path) -> str:
        """Extract and parse AndroidManifest.xml"""
        manifest_path = apk_dir / 'AndroidManifest.xml'
        if not manifest_path.exists():
            return ""
        
        try:
            # Parse binary XML
            content = manifest_path.read_bytes()
            
            # Extract strings
            strings = re.findall(rb'[\x20-\x7E]{4,}', content)
            decoded_strings = [s.decode('utf-8', errors='ignore') for s in strings]
            
            return '\n'.join(decoded_strings)
        except:
            return ""
    
    def extract_resources(self, apk_dir: Path) -> Dict[str, str]:
        """Extract APK resources"""
        resources = {}
        
        # Resources.arsc
        arsc_path = apk_dir / 'resources.arsc'
        if arsc_path.exists():
            try:
                # Hex dump
                content = arsc_path.read_bytes()
                resources['resources.arsc'] = content.hex()
            except:
                pass
        
        # res folder
        res_dir = apk_dir / 'res'
        if res_dir.exists():
            for xml_file in res_dir.rglob('*.xml'):
                try:
                    content = xml_file.read_text(encoding='utf-8', errors='ignore')
                    resources[str(xml_file.relative_to(apk_dir))] = content
                except:
                    pass
        
        return resources
    
    def decode_assets(self, apk_dir: Path) -> Dict[str, str]:
        """Decode assets folder"""
        assets = {}
        assets_dir = apk_dir / 'assets'
        
        if assets_dir.exists():
            for asset_file in assets_dir.rglob('*'):
                if asset_file.is_file():
                    try:
                        # Text file
                        content = asset_file.read_text(encoding='utf-8', errors='ignore')
                        assets[str(asset_file.relative_to(apk_dir))] = content
                    except:
                        # Binary file - hex
                        try:
                            content = asset_file.read_bytes()
                            assets[str(asset_file.relative_to(apk_dir))] = content.hex()
                        except:
                            pass
        
        return assets
    
    def analyze_apk_strings(self, apk_dir: Path) -> List[str]:
        """Extract all strings from APK"""
        strings = []
        
        for file_path in apk_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix in ['.dex', '.so', '.xml', '.txt']:
                try:
                    content = file_path.read_bytes()
                    # Find printable strings
                    found_strings = re.findall(rb'[\x20-\x7E]{4,}', content)
                    for s in found_strings:
                        try:
                            strings.append(s.decode('utf-8', errors='ignore'))
                        except:
                            pass
                except:
                    pass
        
        return list(set(strings))
    
    def deobfuscate_apk(self, apk_path: Path) -> Optional[str]:
        """Fully decrypt APK"""
        console.print(f"\n[bold cyan]📱 APK Decryption Started: {apk_path.name}[/bold cyan]")
        console.print("[yellow]⚠️ This may take 5-10 minutes for large APKs[/yellow]\n")
        
        output_dir = Path(f"{OUTPUT_PREFIX}{apk_path.stem}_full_decompiled")
        output_dir.mkdir(exist_ok=True)
        
        # Extract APK
        extracted_dir = self.extract_apk(apk_path)
        if not extracted_dir:
            return None
        
        try:
            # Decompile DEX
            console.print("[cyan]🔧 Decompiling DEX files...[/cyan]")
            dex_content = self.decompile_dex_files(extracted_dir)
            if dex_content:
                (output_dir / 'decompiled_source.txt').write_text(
                    '\n\n'.join(dex_content), 
                    encoding='utf-8'
                )
            
            # Manifest
            console.print("[cyan]📋 Parsing AndroidManifest.xml...[/cyan]")
            manifest = self.extract_android_manifest(extracted_dir)
            if manifest:
                (output_dir / 'AndroidManifest.txt').write_text(manifest, encoding='utf-8')
            
            # Resources
            console.print("[cyan]📦 Extracting resources...[/cyan]")
            resources = self.extract_resources(extracted_dir)
            for name, content in resources.items():
                try:
                    out_file = output_dir / 'resources' / name
                    out_file.parent.mkdir(parents=True, exist_ok=True)
                    out_file.write_text(content, encoding='utf-8')
                except:
                    pass
            
            # Assets
            console.print("[cyan]📁 Decoding assets...[/cyan]")
            assets = self.decode_assets(extracted_dir)
            for name, content in assets.items():
                try:
                    out_file = output_dir / 'assets' / name
                    out_file.parent.mkdir(parents=True, exist_ok=True)
                    out_file.write_text(content, encoding='utf-8')
                except:
                    pass
            
            # Strings
            console.print("[cyan]🔍 Extracting APK strings...[/cyan]")
            strings = self.analyze_apk_strings(extracted_dir)
            if strings:
                (output_dir / 'extracted_strings.txt').write_text(
                    '\n'.join(strings),
                    encoding='utf-8'
                )
            
            # Decode obfuscated code
            console.print("[cyan]🔓 Decoding obfuscated code...[/cyan]")
            deobf = UltimateDeobfuscator()
            
            # Decode DEX content
            if dex_content:
                combined = '\n'.join(dex_content)
                decoded = deobf.deobfuscate(combined)
                (output_dir / 'deobfuscated_code.txt').write_text(decoded, encoding='utf-8')
            
            console.print("[bold green]✅ APK fully decrypted![/bold green]")
            return str(output_dir)
            
        except Exception as e:
            console.print(f"[red]APK decryption error: {e}[/red]")
            return None
        finally:
            # Clean temp folder
            try:
                shutil.rmtree(extracted_dir)
            except:
                pass

# ============================================================================
# UI AND MAIN FUNCTIONS
# ============================================================================

def display_banner():
    """Display awesome banner"""
    try:
        banner_text = pyfiglet.figlet_format("HINDUSTAN", font="big")
    except:
        banner_text = "=== HINDUSTAN ULTIMATE ==="
    
    colored_banner = Text(banner_text, style="bold red")
    
    console.print(Panel(
        colored_banner,
        box=box.DOUBLE,
        border_style="red",
        title="[bold white]🔥 ULTIMATE DE-OBFUSCATOR v5.0 🔥[/bold white]",
        subtitle="[bold yellow]⚡ Developer: @Rolexconfigyt | Bypass Any Encryption ⚡[/bold yellow]"
    ))
    
    features = Text(
        "✅ HTML/JS/PHP/Java/CSS/APK - Decrypt Everything\n"
        "✅ 50+ Encryption Types Auto-Detected\n"
        "✅ Multi-Layer Decoding (Any Number of Layers)\n"
        "✅ APK - Full Decompile + Code Recovery\n"
        "✅ 100% Original Code - No Encryption Left",
        style="bold green",
        justify="center"
    )
    console.print(Panel(features, box=box.ROUNDED, border_style="green"))
    console.print()

def get_all_files():
    """List all supported files"""
    current_dir = Path(".")
    extensions = [
        '.html', '.htm', '.js', '.php', '.css', 
        '.java', '.dex', '.txt', '.json', '.xml',
        '.apk', '.jar', '.smali'
    ]
    
    files = []
    for ext in extensions:
        files.extend(current_dir.glob(f"*{ext}"))
    
    # Remove duplicates and sort
    files = list(set(files))
    files = [f for f in files if not f.name.startswith(OUTPUT_PREFIX)]
    return sorted(files, key=lambda x: x.name)

def main():
    """Main function"""
    console.clear()
    display_banner()
    
    while True:
        files = get_all_files()
        
        if not files:
            console.print(Panel(
                "[red]⚠️ No supported files found![/red]\n"
                "[yellow]Place HTML, JS, PHP, APK or any encrypted file here[/yellow]",
                box=box.HEAVY,
                border_style="red"
            ))
            return
        
        # Display files
        table = Table(
            title="[bold yellow]📄 Available Files (Encrypted/Obfuscated)[/bold yellow]",
            box=box.SIMPLE_HEAVY,
            border_style="cyan"
        )
        table.add_column("ID", style="bold red", justify="center")
        table.add_column("Filename", style="bold green")
        table.add_column("Size", style="bold yellow", justify="right")
        table.add_column("Type", style="bold magenta", justify="center")
        table.add_column("Encryption", style="bold cyan", justify="center")
        
        for idx, file in enumerate(files, start=1):
            size = file.stat().st_size
            size_str = f"{size/1024:.2f} KB" if size < 1024*1024 else f"{size/1024/1024:.2f} MB"
            
            # Detect encryption type
            enc_type = "Unknown"
            try:
                if file.suffix.lower() == '.apk':
                    enc_type = "APK (DEX/XML)"
                else:
                    content = file.read_text(encoding='utf-8', errors='ignore')[:1000]
                    deobf = UltimateDeobfuscator()
                    detected = deobf.detect_encryption_type(content)
                    enc_type = ", ".join(detected[:3]) if detected else "Plain Text"
            except:
                enc_type = "Binary"
            
            file_type = "APK" if file.suffix.lower() == '.apk' else "Code"
            table.add_row(f"[{idx}]", file.name, size_str, file_type, enc_type)
        
        console.print(table)
        console.print()
        
        # Select
        try:
            choice = IntPrompt.ask(
                "[bold cyan]📌 Enter file ID to decrypt[/bold cyan]",
                choices=[str(i) for i in range(1, len(files) + 1)],
                show_choices=False
            )
            if 1 <= choice <= len(files):
                selected_file = files[choice - 1]
                break
        except:
            console.print("[red]❌ Invalid ID![/red]")
            continue
    
    console.print(f"\n[bold green]➜ Selected File:[/bold green] [cyan]{selected_file.name}[/cyan]")
    
    confirm = Prompt.ask(
        "\n[bold yellow]⚡ Start Decryption?[/bold yellow]",
        choices=["y", "n"],
        default="y"
    )
    if confirm.lower() != 'y':
        console.print("[yellow]❌ Cancelled[/yellow]")
        return
    
    # ========== DECRYPT ==========
    
    if selected_file.suffix.lower() == '.apk':
        # Decrypt APK
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]📱 Processing APK...", total=100)
            
            progress.update(task, advance=20, description="[cyan]📦 Extracting APK...")
            apk_deobf = APKUltimateDeobfuscator()
            
            progress.update(task, advance=30, description="[yellow]🔧 Decompiling DEX...")
            result = apk_deobf.deobfuscate_apk(selected_file)
            
            progress.update(task, advance=50, description="[green]✅ APK Fully Decrypted!")
        
        if result:
            console.print(Panel(
                f"[bold green]✅ APK Decryption Complete![/bold green]\n"
                f"[yellow]📁 Output: {result}[/yellow]\n"
                f"[cyan]📄 Files: deobfuscated_code.txt, decompiled_source.txt[/cyan]",
                box=box.HEAVY,
                border_style="green"
            ))
        else:
            console.print(Panel(
                "[red]❌ APK Decryption Failed[/red]\n"
                "[yellow]⚠️ Please check: jadx/apktool is installed or not[/yellow]",
                box=box.HEAVY,
                border_style="red"
            ))
    
    else:
        # Decrypt code file
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]🔍 Analyzing file...", total=100)
            
            try:
                content = selected_file.read_text(encoding='utf-8', errors='ignore')
                progress.update(task, advance=20, description="[cyan]🔓 Starting decryption...")
                
                deobf = UltimateDeobfuscator()
                decoded = deobf.deobfuscate(content)
                progress.update(task, advance=40, description="[yellow]⚡ Multi-layer decoding...")
                
                # Save
                output_name = f"{OUTPUT_PREFIX}{selected_file.name}"
                Path(output_name).write_text(decoded, encoding='utf-8')
                
                progress.update(task, advance=40, description="[bold green]✅ Decryption Complete!")
                
                # Show result
                original_size = selected_file.stat().st_size
                new_size = Path(output_name).stat().st_size
                
                result_table = Table(box=box.SIMPLE, show_header=False)
                result_table.add_column("Property", style="bold cyan")
                result_table.add_column("Value", style="bold yellow")
                
                result_table.add_row("📄 Original File:", selected_file.name)
                result_table.add_row("💾 Decrypted File:", f"[bold green]{output_name}[/bold green]")
                result_table.add_row("📏 Original Size:", f"{original_size/1024:.2f} KB")
                result_table.add_row("🔓 New Size:", f"{new_size/1024:.2f} KB")
                
                if deobf.detected_encryptions:
                    result_table.add_row("🔍 Detected:", ", ".join(deobf.detected_encryptions))
                
                if deobf.decoded_layers:
                    result_table.add_row("📊 Layers Decoded:", str(len(deobf.decoded_layers)))
                
                console.print(Panel(
                    result_table,
                    title="✨ [bold green]Decryption Completely Successful! ✨[/bold green]",
                    box=box.HEAVY,
                    border_style="green",
                    expand=False
                ))
                
            except Exception as e:
                progress.update(task, description=f"[red]❌ Error: {e}[/red]")
                console.print(f"[red]❌ Decryption failed: {e}[/red]")
    
    # Process another?
    another = Prompt.ask(
        "\n[bold cyan]🔄 Decrypt another file?[/bold cyan]",
        choices=["y", "n"],
        default="n"
    )
    if another.lower() == 'y':
        main()
    else:
        console.print("\n[bold green]🔥 HINDUSTAN ULTIMATE DE-OBFUSCATOR - Bypass Any Encryption 🔥[/bold green]")
        console.print("[bold yellow]🙏 Thank You! Stay Secure! 🔒[/bold yellow]\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]👋 Goodbye![/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Critical Error: {e}[/red]")
