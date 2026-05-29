#!/usr/bin/env python3
"""
Lightweight OCR-based TikTok username extractor for Fameswap screenshots.
Uses tesseract to extract text from images, then finds TikTok usernames.
"""
import re
import os
import subprocess


def ocr_image(image_path):
    """Run tesseract OCR on an image and return extracted text."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    result = subprocess.run(
        ["tesseract", image_path, "stdout"],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip()


def is_valid_tiktok_username(s):
    """Check if a string looks like a valid TikTok username."""
    return bool(re.match(r'^[a-zA-Z0-9_.]{2,30}$', s))


def extract_usernames_from_text(text):
    """
    Parse TikTok usernames from Fameswap-style OCR output.
    Strategy: Find 'followers' lines, then look up for the username.
    """
    found = set()

    # Pass 1: explicit @ mentions
    for match in re.finditer(r'@([a-zA-Z0-9_.]+)', text):
        uname = match.group(1)
        if is_valid_tiktok_username(uname):
            found.add(uname)

    lines = text.split('\n')
    noise_words = {'app.fameswap.com', 'ee', 'followers', 'fameswap'}

    # Pass 2: find "followers" lines as anchors, then look up
    follower_idxs = [i for i, line in enumerate(lines) if 'followers' in line.strip().lower()]

    for idx in follower_idxs:
        for offset in range(1, 4):
            check_idx = idx - offset
            if check_idx < 0:
                break
            candidate = lines[check_idx].strip()
            if not candidate or len(candidate) < 3:
                continue
            if candidate.lower() in noise_words:
                continue
            # Skip pure noise lines
            if re.match(r'^[\s\d\-\.\|><\(\)\[\]{}_=+\'\"!@#%^&*,;:?]+$', candidate):
                continue
            if re.match(r'^\d+[\.:]?\d*\s*$', candidate):
                continue

            # Clean leading noise (including Unicode chars)
            cleaned = re.sub(r'^[\d\s\-\.\|><\(\)\[\]{}_=+\'\"!@#%^&*,;:?\u00ab\u00bb\u2018\u2019\u201c\u201d\u2013\u2014\u00a2\\]+', '', candidate)            
            # Extract first valid username-like token
            first_token = re.match(r'[a-zA-Z][a-zA-Z0-9_.]+', cleaned)
            if first_token:
                cleaned = first_token.group()
            else:
                cleaned = ''
            cleaned = cleaned.strip().rstrip('.')

            if is_valid_tiktok_username(cleaned) and len(cleaned) >= 3:
                found.add(cleaned)
                break

    # Pass 3: catch any remaining username-like tokens
    for line in lines:
        s = line.strip()
        if not s or len(s) < 4:
            continue
        if any(nw in s.lower() for nw in noise_words):
            continue
        # Skip lines that are mostly noise
        cleaned = re.sub(r'^[\d\s\-\.\|><\(\)\[\]{}_=+\'\"!@#%^&*,;:?\u00ab\u00bb\u2018\u2019\u201c\u201d\u2013\u2014\u00a2\\]+', '', s)
        # Extract first token
        first_token = re.match(r'[a-zA-Z][a-zA-Z0-9_.]+', cleaned)
        if first_token:
            cleaned = first_token.group()
        else:
            cleaned = ''
        cleaned = cleaned.strip().rstrip('.')
        if is_valid_tiktok_username(cleaned) and len(cleaned) >= 4:
            found.add(cleaned)

    return list(found)


def parse_fameswap_image(image_path):
    """Full pipeline: OCR image -> extract usernames."""
    if not os.path.exists(image_path):
        return {'error': f'File not found: {image_path}', 'usernames': [], 'count': 0}

    raw_text = ocr_image(image_path)
    usernames = extract_usernames_from_text(raw_text)

    return {
        'usernames': usernames,
        'raw_text': raw_text,
        'count': len(usernames)
    }


def format_fameswap_results(results_list):
    """Format TikTok profile results for Discord output, US accounts first."""
    if not results_list:
        return "No accounts found in image."

    us_accounts = []
    non_us_accounts = []
    errors = []
    # Skip failed lookups silently in the list (track count only)
    errors = len([d for d in results_list if d.get('error')])
    valid = [d for d in results_list if not d.get('error')]
    us_accounts = [d for d in valid if d.get('region') == 'US']
    non_us = [d for d in valid if d.get('region', '') != 'US']

    def fmt_account(i, d):
        nickname = d.get('nickname', 'N/A')
        username = d.get('username', 'unknown')
        region = d.get('region', '')
        stats = d.get('stats', {})
        flag = ""
        if region and len(region) == 2:
            flag = (chr(ord(region[0].upper()) - ord('A') + 0x1F1E6) +
                    chr(ord(region[1].upper()) - ord('A') + 0x1F1E6))
        followers = stats.get('followers', '?')
        hearts = stats.get('hearts', '?')
        about = d.get('about', '')
        if about:
            about = about.replace('\n', ' ').replace('\r', '').strip()[:40]
            if len(about) == 40:
                about = about[:37] + '...'
        line = f"  {flag} **{nickname}** (@{username}) — 👥 {followers} ❤️ {hearts}"
        if about:
            line += f" · _{about}_"
        return line

    lines = []
    if us_accounts:
        lines.append(f"**🇺🇸 US Accounts**")
        for i, d in enumerate(us_accounts, 1):
            lines.append(fmt_account(i, d))
        lines.append("")

    if non_us:
        lines.append(f"**🌍 Others**")
        for i, d in enumerate(non_us, 1):
            lines.append(fmt_account(i, d))
        lines.append("")

    # Single clean summary line
    total = len(valid)
    parts = [f"📊 **{total}** accounts"]
    if len(us_accounts) == total:
        parts.append("all US")
    elif us_accounts:
        parts.append(f"**{len(us_accounts)}** US")
    if non_us:
        parts.append(f"**{len(non_us)}** other")
    if errors:
        parts.append(f"**{errors}** failed OCR")
    lines.append(" · ".join(parts))

    return "\n".join(lines).strip()


if __name__ == "__main__":
    import sys
    from tiktok_lookup import fetch_tiktok_profile

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path or not os.path.exists(path):
        print("Usage: python3 fameswap_ocr.py <image_path>")
        sys.exit(1)

    result = parse_fameswap_image(path)
    print("OCR Raw Text:")
    print(result['raw_text'])
    print()
    print(f"Extracted ({result['count']}): {result['usernames']}")
    print()

    print("Looking up...")
    results = []
    for u in result['usernames']:
        data = fetch_tiktok_profile(u)
        if data:
            data['username'] = u
        else:
            data = {'username': u, 'error': 'Not found'}
        results.append(data)

    print(format_fameswap_results(results))
