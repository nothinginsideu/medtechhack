import re
import os

vibe_patterns = [
    r'\brounded-xl\b', r'\brounded-2xl\b', r'\brounded-lg\b', r'\brounded-md\b', r'\brounded-sm\b', r'\brounded\b',
    r'\brounded-full\b', r'\brounded-t-lg\b', r'\brounded-b-lg\b', r'\brounded-bl-none\b', r'\brounded-br-none\b',
    r'\bshadow-2xl\b', r'\bshadow-xl\b', r'\bshadow-lg\b', r'\bshadow-md\b', r'\bshadow-sm\b', r'\bshadow\b',
    r'\banimate-in\b', r'\bfade-in\b', r'\bzoom-in-[0-9]+\b', r'\bslide-in-from-[a-z0-9-]+\b',
    r'\bbackdrop-blur-[a-z]+\b',
    r'\bhover:scale-[0-9]+\b', r'\bactive:scale-[0-9]+\b',
    r'\bbg-gradient-to-[a-z]+\b', r'\bfrom-[a-z0-9#-]+\b', r'\bto-[a-z0-9#-]+\b',
    r'\bduration-[0-9]+\b'
]

def remove_vibes(match):
    cls_str = match.group(1)
    for p in vibe_patterns:
        cls_str = re.sub(r'(?<=[\s"\'`])' + p + r'(?=[\s"\'`])', '', cls_str)
        # Also handle edges without relying on lookbehinds that might fail
        cls_str = re.sub(r'\b' + p + r'\b', '', cls_str)
    # clean multiple spaces
    cls_str = re.sub(r' +', ' ', cls_str).strip()
    return f'className="{cls_str}"' if match.string[match.start()+10] == '"' else f'className={{`{cls_str}`}}'

def process(file):
    with open(file, 'r') as f: content = f.read()
    orig = content
    # Replace inside className="..."
    content = re.sub(r'className="([^"]*)"', remove_vibes, content)
    # Replace inside className={`...`}
    content = re.sub(r'className=\{`([^`]*)`\}', remove_vibes, content)
    if content != orig:
        with open(file, 'w') as f: f.write(content)

for root, _, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith('.jsx'): process(os.path.join(root, file))
