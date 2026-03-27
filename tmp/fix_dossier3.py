import re
p = r"C:\\Users\\fahad\\Desktop\\bank-diligence-platform\\bank-diligence-platform\\backend\\app\\services\\dossier_autofill.py"
with open(p, 'r', encoding='utf-8') as f:
    s = f.read()
# Fix .replace("<broken newline>", ...)
s = re.sub(r"\.replace\(\s*\"\s*\r?\n\s*\"\s*,", '.replace("\\n",', s)
s = re.sub(r"\.replace\(\s*\"\s*\r?\n\s*\"\s*\)", '.replace("\\n","")', s)
# Fix CR patterns
s = re.sub(r"\.replace\(\s*\"\s*\r\s*\"\s*,", '.replace("\\r",', s)
s = re.sub(r"\.replace\(\s*\"\s*\r\s*\"\s*\)", '.replace("\\r","")', s)
with open(p, 'w', encoding='utf-8', newline='\n') as f:
    f.write(s)
print('fixed replace patterns')
