#!/usr/bin/env python3
"""Test validator with actual extracted value from database."""
import sys
sys.path.insert(0, '/app')

from app.services.extractors.validators import is_probably_name_line

# Test with the actual extracted value
test_name = "کاشف زابد"

print(f"Testing: {test_name!r}")
print(f"Length: {len(test_name)}")

# Check character codes
print("Character codes:")
for i, c in enumerate(test_name[:10]):
    print(f"  [{i}] {c!r} -> U+{ord(c):04X}")

# Test letter ratio (replicate the function)
def compute_letter_ratio(text: str) -> float:
    s2 = "".join(ch for ch in text if not ch.isspace())
    if not s2:
        return 0.0
    letters = sum(1 for ch in s2 if ch.isalpha())
    return letters / len(s2)

ratio = compute_letter_ratio(test_name)
print(f"Letter ratio: {ratio:.2f}")

# Test validator
result = is_probably_name_line(test_name)
print(f"\nValidator result: {result}")

# Check Arabic detection
def is_arabic_char(char: str) -> bool:
    code_point = ord(char)
    arabic_unicode_ranges = [
        (0x0600, 0x06FF),  # Arabic block
        (0x0750, 0x077F),  # Arabic Supplement
        (0x08A0, 0x08FF),  # Arabic Extended-A
        (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
        (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
    ]
    return any(start <= code_point <= end for start, end in arabic_unicode_ranges)

has_arabic = any(is_arabic_char(c) for c in test_name)
has_latin = any('A' <= c <= 'Z' or 'a' <= c <= 'z' for c in test_name)
print(f"has_arabic: {has_arabic}")
print(f"has_latin: {has_latin}")
print(f"is_pure_arabic_script: {has_arabic and not has_latin}")

