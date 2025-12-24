"""Generate PWA icons from the WAQD icon"""
from PIL import Image
import os

# Get the source icon
source_icon = os.path.join(os.path.dirname(__file__), '../../waqd/assets/gui_base/icon.png')
public_dir = os.path.join(os.path.dirname(__file__), 'public')

# Create public directory if it doesn't exist
os.makedirs(public_dir, exist_ok=True)

# Open source image
img = Image.open(source_icon)

# Generate 192x192
icon_192 = img.resize((192, 192), Image.Resampling.LANCZOS)
icon_192.save(os.path.join(public_dir, 'pwa-192x192.png'))
print("Created pwa-192x192.png")

# Generate 512x512
icon_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
icon_512.save(os.path.join(public_dir, 'pwa-512x512.png'))
print("Created pwa-512x512.png")

# Generate favicon
favicon = img.resize((32, 32), Image.Resampling.LANCZOS)
favicon.save(os.path.join(public_dir, 'favicon.ico'))
print("Created favicon.ico")

print("\nPWA icons generated successfully!")
