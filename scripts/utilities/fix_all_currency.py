#!/usr/bin/env python3
"""
Comprehensive script to fix all currency references from $ to ₹
"""
import os
import re
import glob

def fix_currency_in_file(file_path):
    """Fix currency references in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Pattern 1: ₹amount (but not ${} template literals)
        # Look for $ followed by numbers or variables, but not followed by {
        pattern1 = r'\$(?!\{)(\d+(?:\.\d+)?|\w+)'
        matches1 = re.findall(pattern1, content)
        if matches1:
            content = re.sub(pattern1, r'₹\1', content)
            changes_made.append(f"Fixed $ currency symbols: {len(matches1)} instances")
        
        # Pattern 2: "INR" currency code
        if 'INR' in content and 'currency' in content.lower():
            content = content.replace("'INR'", "'INR'")
            content = content.replace('"INR"', '"INR"')
            changes_made.append("Fixed USD currency codes")
        
        # Pattern 3: Comments with $ references
        pattern3 = r'(#.*)\$(\d+(?:\.\d+)?)'
        matches3 = re.findall(pattern3, content)
        if matches3:
            content = re.sub(pattern3, r'\1₹\2', content)
            changes_made.append(f"Fixed $ in comments: {len(matches3)} instances")
        
        # Pattern 4: "rupee" or "rupee" words
        if 'rupee' in content.lower():
            content = re.sub(r'\bdollar\b', 'rupee', content, flags=re.IGNORECASE)
            content = re.sub(r'\bDollar\b', 'Rupee', content)
            content = re.sub(r'\bDOLLAR\b', 'RUPEE', content)
            changes_made.append("Fixed rupee/rupee words")
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return changes_made
        
        return []
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []

def main():
    """Main function to fix all currency references"""
    print("🔧 Fixing All Currency References to Rupees...")
    print("=" * 60)
    
    # File patterns to check
    file_patterns = [
        '**/*.py',
        '**/*.html',
        '**/*.js',
        '**/*.css',
        '**/*.md',
        '**/*.txt'
    ]
    
    # Directories to exclude
    exclude_dirs = {
        'env', '.git', '__pycache__', 'node_modules', 
        '.pytest_cache', 'logs', 'logs_archive'
    }
    
    total_files_processed = 0
    total_files_changed = 0
    
    for pattern in file_patterns:
        for file_path in glob.glob(pattern, recursive=True):
            # Skip if in excluded directory
            if any(excluded in file_path for excluded in exclude_dirs):
                continue
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                continue
            
            total_files_processed += 1
            changes = fix_currency_in_file(file_path)
            
            if changes:
                total_files_changed += 1
                print(f"✅ {file_path}")
                for change in changes:
                    print(f"   - {change}")
    
    print("\n" + "=" * 60)
    print(f"📊 Summary:")
    print(f"   Files processed: {total_files_processed}")
    print(f"   Files changed: {total_files_changed}")
    print(f"   ✅ All currency references converted to Rupees (₹)")

if __name__ == "__main__":
    main()
