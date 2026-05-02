# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "qrcode[pil]==8.0",
# ]
# ///
"""Generate a QR code PNG from a URL."""
import argparse


def main():
    parser = argparse.ArgumentParser(description="Generate a QR code PNG from a URL.")
    parser.add_argument("url", help="URL to encode")
    parser.add_argument("--output", "-o", default="qr_code.png", help="Output PNG file path (default: qr_code.png)")
    parser.add_argument("--box-size", type=int, default=10, metavar="N", help="Pixel size per QR module (default: 10)")
    parser.add_argument("--border", type=int, default=4, metavar="N", help="Border width in QR modules (default: 4)")
    args = parser.parse_args()

    import qrcode

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=args.box_size,
        border=args.border,
    )
    qr.add_data(args.url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(args.output)
    print(f"QR code saved to {args.output}")


if __name__ == "__main__":
    main()
