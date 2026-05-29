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
    """Format TikTok profile results like /tiktok — beautiful per-account blocks."""
    if not results_list:
        return "No accounts found in image."

    errors = len([d for d in results_list if d.get('error')])
    valid = [d for d in results_list if not d.get('error')]
    us = [d for d in valid if d.get('region') == 'US']
    non_us = [d for d in valid if d.get('region', '') != 'US']

    # Collect profile blocks using format_profile from tiktok_lookup
    # but with a compact header line instead of the full format
    blocks = []
    section_num = 1

    def profile_compact(d):
        """Build a compact profile block similar to /tiktok."""
        flag = get_flag(d.get('region', ''))
        nick = d.get('nickname', 'N/A')
        user = d.get('username', 'unknown')
        stats = d.get('stats', {})
        about = d.get('about', '')
        created = d.get('accountCreated', '')

        lines = []
        # Compact listing number with flag and nickname
        lines.append(f"**{nick}**")
        lines.append(f"@{user} {flag}")
        lines.append("")
        lines.append(f"👥 Followers: {stats.get('followers', '0')}")
        lines.append(f"❤️ Hearts: {stats.get('hearts', '0')}")
        if about:
            # Truncate bio for compact view
            about_line = about.replace('\n', ' ').replace('\r', '')[:100]
            if len(about_line) == 100:
                about_line = about_line[:97] + '...'
            lines.append(f"📝 {about_line}")
        if created:
            lines.append(f"📅 Created: {created}")
        return "\n".join(lines)

    blocks.append("**📸 Fameswap Scan**\n")

    # US accounts first
    if us:
        blocks.append("**🇺🇸 United States**\n")
        for d in us:
            blocks.append(profile_compact(d))
            blocks.append("")
        blocks.append("")

    # Non-US
    if non_us:
        blocks.append("**🌍 Other Countries**\n")
        for d in non_us:
            blocks.append(profile_compact(d))
            blocks.append("")
        blocks.append("")

    # Summary
    stats_line = f"**📊 {len(valid)}** accounts"
    if us:
        stats_line += f" · **{len(us)}** US"
    if non_us:
        stats_line += f" · **{len(non_us)}** other"
    if errors:
        stats_line += f" · **{errors}** lookup failed"
    blocks.append(stats_line)

    return "\n".join(blocks).strip()

def get_flag(region_code):
    if not region_code or len(region_code) != 2:
        return ""
    code = region_code.upper()
    return chr(ord(code[0]) - ord('A') + 0x1F1E6) + chr(ord(code[1]) - ord('A') + 0x1F1E6)


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
