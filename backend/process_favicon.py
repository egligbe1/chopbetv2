import os
from PIL import Image

source_png = r"C:\Users\EmmanuelGligbe\.gemini\antigravity\brain\00a24962-0de8-4f7f-8cf6-54b508c7b729\chopbet_favicon_1775773239550.png"
public_dir = r"c:\Users\EmmanuelGligbe\Downloads\Projects\chop_bet2\chopbetv2\frontend\public"
app_dir = r"c:\Users\EmmanuelGligbe\Downloads\Projects\chop_bet2\chopbetv2\frontend\app"

img = Image.open(source_png)

# Save as ico in public
img.save(os.path.join(public_dir, "favicon.ico"), format="ICO", sizes=[(32, 32)])

# Save as png in app for Next.js metadata
img.save(os.path.join(app_dir, "icon.png"))
img.save(os.path.join(public_dir, "icon.png"))

print("Favicon assets generated successfully.")
