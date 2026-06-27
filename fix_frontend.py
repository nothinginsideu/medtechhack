import re

# 1. Fix useServiceFilters.js
path = 'frontend/src/hooks/useServiceFilters.js'
with open(path, 'r') as f: content = f.read()
# Remove the strict queryWords filter block
content = re.sub(r'// If user searched for a specific clinic name.*?return true;\n\s+}\);\n', 'return true;\n        });\n', content, flags=re.DOTALL)
with open(path, 'w') as f: f.write(content)

# 2. Fix AdminDashboard.jsx
path = 'frontend/src/pages/AdminDashboard.jsx'
with open(path, 'r') as f: content = f.read()
# Remove green ping animation block
content = re.sub(r'<span className="relative flex h-2 w-2">.*?</span>\s*В реальном времени', 'В реальном времени', content, flags=re.DOTALL)
content = re.sub(r'<span className="h-2 w-2 rounded-full bg-\[#9CA3AF\]"></span>\s*Нет соединения', 'Нет соединения', content, flags=re.DOTALL)
with open(path, 'w') as f: f.write(content)

# 3. Fix ClientHome.jsx
path = 'frontend/src/pages/ClientHome.jsx'
with open(path, 'r') as f: content = f.read()

# Add React hooks
content = content.replace("import React, { useState } from 'react';", "import React, { useState, useRef, useEffect } from 'react';")
content = content.replace("import { Search, Loader2, TrendingUp, X, MapPin, Building2, Phone } from 'lucide-react';", "import { Search, Loader2, TrendingUp, X, MapPin, Building2, Phone } from 'lucide-react';") # Sparkles removed!

# Add chat logic
chat_logic = """    }
  ]);
  
  const chatContainerRef = useRef(null);
  const messagesEndRef = useRef(null);
  const isUserScrolledUp = useRef(false);

  useEffect(() => {
    if (!isUserScrolledUp.current && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, chatLoading]);

  const handleChatScroll = () => {
    if (!chatContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
    isUserScrolledUp.current = scrollHeight - scrollTop - clientHeight > 50;
  };"""
content = content.replace("    }\n  ]);", chat_logic)
content = content.replace("setChatLoading(true);", "setChatLoading(true);\n    isUserScrolledUp.current = false;")

# Remove Emojis from quick tags
content = content.replace("'🩸 Общий анализ крови (ОАК)'", "'Общий анализ крови (ОАК)'")
content = content.replace("'🧠 МРТ головного мозга'", "'МРТ головного мозга'")
content = content.replace("'🩺 Приём терапевта'", "'Приём терапевта'")
content = content.replace("'🤰 УЗИ'", "'УЗИ'")
content = content.replace("'🦠 ПЦР тест'", "'ПЦР тест'")
content = content.replace("'🦷 Консультация стоматолога'", "'Консультация стоматолога'")

# Remove empty state huge icon and grey text
content = content.replace('h-8 w-8 text-[#D1D5DB]', 'h-6 w-6 text-[#9CA3AF]')
content = content.replace('text-[#374151] font-medium', 'text-[#6B7280] font-medium text-sm')
content = content.replace('text-[#6B7280] text-sm mt-1', 'text-[#9CA3AF] text-xs mt-1')
content = content.replace('Попробуйте изменить параметры запроса', 'Проверьте правильность написания или попробуйте изменить фильтры')

# Add scroll handler to chat container
content = content.replace('className="flex-1 p-4 overflow-y-auto space-y-4 bg-[#F9FAFB]/50"', 'className="flex-1 p-4 overflow-y-auto space-y-4 bg-[#F9FAFB]/50" ref={chatContainerRef} onScroll={handleChatScroll}')
content = content.replace('<span>ИИ анализирует ваши симптомы и ищет прайсы...</span>\n              </div>\n            )}', '<span>ИИ анализирует ваши симптомы и ищет прайсы...</span>\n              </div>\n            )}\n            <div ref={messagesEndRef} />')

# Update Chat Assistant Button (No Sparkles, plain text, strict blue)
old_btn = """<button
          onClick={() => setIsChatOpen(!isChatOpen)}
          className="bg-gradient-to-r from-[#2563EB] to-[#1D4ED8] hover:scale-105 active:scale-95 text-white p-4 rounded-full shadow-2xl flex items-center justify-center transition-all cursor-pointer border border-[#3B82F6] font-semibold"
        >
          {isChatOpen ? <X size={20} /> : (
            <div className="flex items-center gap-2">
              <span>🩺 ИИ-Ассистент</span>
            </div>
          )}
        </button>"""
new_btn = """<button
          onClick={() => setIsChatOpen(!isChatOpen)}
          className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white px-5 py-3 shadow flex items-center justify-center transition-colors cursor-pointer font-medium text-sm border border-[#2563EB]"
        >
          {isChatOpen ? <X size={18} /> : (
            <div className="flex items-center gap-2">
              <span>Ассистент</span>
            </div>
          )}
        </button>"""
content = content.replace(old_btn, new_btn)

# Remove the green ping
content = content.replace('<div className="w-2 h-2 bg-[#10B981] rounded-full animate-ping"></div>', '')

# Remove resident toggle rounding and make strict
content = content.replace('className="flex items-center bg-[#F3F4F6] border border-[#E5E7EB] rounded-md p-1 shrink-0"', 'className="flex items-center bg-[#F9FAFB] border border-[#E5E7EB] p-1 shrink-0"')

with open(path, 'w') as f: f.write(content)

# STRIP ALL VIBE CLASSES FROM ALL FILES
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

def clean_vibe(filepath):
    with open(filepath, 'r') as f: text = f.read()
    orig = text
    for p in vibe_patterns:
        # replace matching classes carefully without messing up newlines
        text = re.sub(r'(\s+)' + p + r'(?=\s|["\'])', r'\1', text)
        text = re.sub(r'(["\'])' + p + r'(\s+)', r'\1', text)
        text = re.sub(r'(["\'])' + p + r'(["\'])', r'\1\2', text)
    
    text = re.sub(r'\s{2,}(?=[a-zA-Z0-9_-])', ' ', text)
    text = text.replace('className=" "', 'className=""')
    
    if text != orig:
        with open(filepath, 'w') as f: f.write(text)

for root, _, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith('.jsx') or file.endswith('.js'):
            clean_vibe(os.path.join(root, file))
