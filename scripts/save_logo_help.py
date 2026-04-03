"""
Save the LawnOps logo image to the static folder.
Since right-click doesn't work, you can:
1. Open this image in a new browser tab and save from there
2. Or use this script to download a placeholder
"""

import urllib.request
import os

# Path where the image should go
image_path = r"d:\python-lawn\static\lawnops_logo.png"

# The image needs to be manually saved here.
# If you can open this image in your browser:
# Try pressing F12 (DevTools), go to Network tab, reload page, find the image request,
# right-click the URL and open in new tab, then save from there.

print(f"Please save your LawnOps image to: {image_path}")
print("\nAlternative method:")
print("1. Open Paint or any image editor")
print("2. Take a screenshot of the logo (Win+Shift+S)")
print("3. Paste and save as PNG to the path above")
print(f"\nFile exists: {os.path.exists(image_path)}")
if os.path.exists(image_path):
    print(f"File size: {os.path.getsize(image_path)} bytes")
