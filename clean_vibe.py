import os
import re

directories = ['frontend/src/pages', 'frontend/src/components']
vibe_patterns = [
    r'\brounded-xl\b', r'\brounded-2xl\b', r'\brounded-lg\b', r'\brounded-md\b', r'\brounded-sm\b', r'\brounded\b',
    r'\brounded-full\b', r'\brounded-t-lg\b', r'\brounded-b-lg\b', r'\brounded-bl-none\b', r'\brounded-br-none\b',
    r'\bshadow-2xl\b', r'\bshadow-xl\b', r'\bshadow-lg\b', r'\bshadow-md\b', r'\bshadow-sm\b', r'\bshadow\b',
    r'\banimate-in\b', r'\bfade-in\b', r'\bzoom-in-[0-9]+\b', r'\bslide-in-from-[a-z0-9-]+\b',
    r'\bbackdrop-blur-[a-z]+\b',
    r'\bhover:scale-[0-9]+\b', r'\bactive:scale-[0-9]+\b',
    r'\bg-gradient-to-[a-z]+\b', r'\bfrom-[a-z]+-[0-9]+\b', r'\bto-[a-z]+-[0-9]+\b',
    r'\bduration-[0-9]+\b'
]

def clean_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    for pattern in vibe_patterns:
        content = re.sub(pattern + r'\s*', '', content)
        # Also handle if the pattern is at the end of the class string before a quote
        content = re.sub(pattern + r'(?=["\'])', '', content)
        
    # Clean up double spaces that might have been created
    content = re.sub(r'\s{2,}', ' ', content)
    content = content.replace('className=" "', 'className=""')
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Cleaned {filepath}")

for root, _, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith('.jsx') or file.endswith('.js'):
            clean_file(os.path.join(root, file))
