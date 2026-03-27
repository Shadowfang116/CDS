import re
p = r"C:\\Users\\fahad\\Desktop\\bank-diligence-platform\\bank-diligence-platform\\backend\\app\\services\\dossier_autofill.py"
with open(p, 'r', encoding='utf-8') as f:
    text = f.read()
# Replace any pattern combined_text = '\n' split across lines
text = re.sub(r"combined_text\s*=\s*'\s*\r?\n\s*'\.join\(([^\)]*)\)", r"combined_text = '\n'.join(\1)", text, flags=re.M)
with open(p, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
print('done')
