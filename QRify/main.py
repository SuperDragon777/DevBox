#!/usr/bin/env python3

import qrcode
import argparse
import sys
from pathlib import Path

def generate_qr(data, output, size=10, error_correction='M', fg_color='black', bg_color='white'):
    error_map = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H
    }
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=error_map.get(error_correction.upper(), qrcode.constants.ERROR_CORRECT_M),
        box_size=size,
        border=4,
    )
    
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color=fg_color, back_color=bg_color)
    img.save(output)
    
    return output

def main():
    parser = argparse.ArgumentParser(
        description='Generate QR codes from text or URLs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Hello World"
  python main.py "https://github.com" -o github.png
  python main.py "My QR Code" -s 15 -e H
  python main.py "Text" --fg-color blue --bg-color yellow
  
Error Correction Levels:
  L - Low (7%)
  M - Medium (15%) [default]
  Q - Quartile (25%)
  H - High (30%)
        """
    )
    
    parser.add_argument('data', help='Text or URL to encode')
    parser.add_argument('-o', '--output', default='qrcode.png', help='Output file (default: qrcode.png)')
    parser.add_argument('-s', '--size', type=int, default=10, help='Box size (default: 10)')
    parser.add_argument('-e', '--error', choices=['L', 'M', 'Q', 'H'], default='M', help='Error correction level (default: M)')
    parser.add_argument('--fg-color', default='black', help='Foreground color (default: black)')
    parser.add_argument('--bg-color', default='white', help='Background color (default: white)')
    
    args = parser.parse_args()
    
    try:
        output_path = generate_qr(
            args.data,
            args.output,
            args.size,
            args.error,
            args.fg_color,
            args.bg_color
        )
        print(f"✓ QR code generated: {output_path}")
        print(f"  Data: {args.data}")
        print(f"  Size: {args.size}")
        print(f"  Error correction: {args.error}")
        
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()