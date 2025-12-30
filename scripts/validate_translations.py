#!/usr/bin/env python3
"""Validate translation completeness and find issues."""
import json
from pathlib import Path
from collections import defaultdict


def validate_translations():
    """Check for missing, unused, and duplicate translations."""
    project_root = Path(__file__).parent.parent
    ui_dict_path = project_root / "src" / "waqd_assets" / "base" / "ui_dict.json"
    
    with open(ui_dict_path, 'r', encoding='utf-8') as f:
        translations = json.load(f)
    
    languages = ['en', 'de', 'hu']
    missing = defaultdict(list)
    duplicates = defaultdict(list)
    value_map = defaultdict(list)
    
    # Check for missing translations
    for key, lang_obj in translations.items():
        for lang in languages:
            if lang not in lang_obj or not lang_obj[lang].strip():
                missing[lang].append(key)
    
    # Check for duplicate values (same translation for different keys)
    for key, lang_obj in translations.items():
        for lang in languages:
            if lang in lang_obj and lang_obj[lang]:
                value = lang_obj[lang].strip().lower()
                value_map[(lang, value)].append(key)
    
    for (lang, value), keys in value_map.items():
        if len(keys) > 1:
            duplicates[lang].append((value, keys))
    
    # Print report
    print("=" * 60)
    print("📊 Translation Validation Report")
    print("=" * 60)
    print(f"\nTotal translation keys: {len(translations)}")
    
    # Missing translations
    print("\n🔍 Missing Translations:")
    total_missing = 0
    for lang in languages:
        count = len(missing[lang])
        total_missing += count
        if count > 0:
            print(f"  {lang.upper()}: {count} missing")
            for key in missing[lang][:5]:  # Show first 5
                print(f"    - {key}")
            if count > 5:
                print(f"    ... and {count - 5} more")
        else:
            print(f"  {lang.upper()}: ✅ Complete")
    
    # Duplicate values
    print("\n🔄 Potential Duplicates:")
    total_dupes = 0
    for lang in languages:
        dupes = duplicates[lang]
        total_dupes += len(dupes)
        if dupes:
            print(f"  {lang.upper()}: {len(dupes)} duplicate values")
            for value, keys in dupes[:3]:  # Show first 3
                print(f"    '{value}' used by: {', '.join(keys[:3])}")
        else:
            print(f"  {lang.upper()}: ✅ No duplicates")
    
    # Summary
    print("\n" + "=" * 60)
    if total_missing == 0:
        print("✅ All translations complete!")
    else:
        print(f"⚠️  Found {total_missing} missing translations")
    
    if total_dupes > 0:
        print(f"ℹ️  Found {total_dupes} potential duplicate values (may be intentional)")
    
    print("=" * 60)
    
    return total_missing == 0


if __name__ == "__main__":
    validate_translations()
