#!/usr/bin/env python3
"""
TikTok Profile Lookup
Extracts profile data from TikTok public pages.
"""
import json
import re
import time
import datetime
from curl_cffi import requests

# TikTok cookie (works better with one)
TIKTOK_COOKIE = "sessionid=b707553e5b1a67c5ed797fb74cdf1aa4"

COUNTRY_CODES = {
    "AF": "Afghanistan", "AX": "\u00c5land Islands", "AL": "Albania", "DZ": "Algeria", "AS": "American Samoa",
    "AD": "Andorra", "AO": "Angola", "AI": "Anguilla", "AQ": "Antarctica", "AG": "Antigua and Barbuda",
    "AR": "Argentina", "AM": "Armenia", "AW": "Aruba", "AU": "Australia", "AT": "Austria", "AZ": "Azerbaijan",
    "BS": "Bahamas", "BH": "Bahrain", "BD": "Bangladesh", "BB": "Barbados", "BY": "Belarus", "BE": "Belgium",
    "BZ": "Belize", "BJ": "Benin", "BM": "Bermuda", "BT": "Bhutan", "BO": "Bolivia",
    "BQ": "Bonaire, Sint Eustatius and Saba", "BA": "Bosnia and Herzegovina", "BW": "Botswana",
    "BV": "Bouvet Island", "BR": "Brazil", "IO": "British Indian Ocean Territory", "BN": "Brunei Darussalam",
    "BG": "Bulgaria", "BF": "Burkina Faso", "BI": "Burundi", "CV": "Cabo Verde", "KH": "Cambodia", "CM": "Cameroon",
    "CA": "Canada", "KY": "Cayman Islands", "CF": "Central African Republic", "TD": "Chad", "CL": "Chile", "CN": "China",
    "CX": "Christmas Island", "CC": "Cocos (Keeling) Islands", "CO": "Colombia", "KM": "Comoros", "CG": "Congo",
    "CD": "Congo, Democratic Republic of the", "CK": "Cook Islands", "CR": "Costa Rica", "CI": "C\u00f4te d'Ivoire",
    "HR": "Croatia", "CU": "Cuba", "CW": "Cura\u00e7ao", "CY": "Cyprus", "CZ": "Czechia", "DK": "Denmark",
    "DJ": "Djibouti", "DM": "Dominica", "DO": "Dominican Republic", "EC": "Ecuador", "EG": "Egypt",
    "SV": "El Salvador", "GQ": "Equatorial Guinea", "ER": "Eritrea", "EE": "Estonia", "SZ": "Eswatini",
    "ET": "Ethiopia", "FK": "Falkland Islands (Malvinas)", "FO": "Faroe Islands", "FJ": "Fiji", "FI": "Finland",
    "FR": "France", "GF": "French Guiana", "PF": "French Polynesia", "TF": "French Southern Territories",
    "GA": "Gabon", "GM": "Gambia", "GE": "Georgia", "DE": "Germany", "GH": "Ghana", "GI": "Gibraltar",
    "GR": "Greece", "GL": "Greenland", "GD": "Grenada", "GP": "Guadeloupe", "GU": "Guam", "GT": "Guatemala",
    "GG": "Guernsey", "GN": "Guinea", "GW": "Guinea-Bissau", "GY": "Guyana", "HT": "Haiti",
    "HM": "Heard Island and McDonald Islands", "VA": "Holy See", "HN": "Honduras", "HK": "Hong Kong",
    "HU": "Hungary", "IS": "Iceland", "IN": "India", "ID": "Indonesia", "IR": "Iran", "IQ": "Iraq", "IE": "Ireland",
    "IM": "Isle of Man", "IL": "Israel", "IT": "Italy", "JM": "Jamaica", "JP": "Japan", "JE": "Jersey",
    "JO": "Jordan", "KZ": "Kazakhstan", "KE": "Kenya", "KI": "Kiribati", "KP": "North Korea", "KR": "South Korea",
    "KW": "Kuwait", "KG": "Kyrgyzstan", "LA": "Laos", "LV": "Latvia", "LB": "Lebanon", "LS": "Lesotho",
    "LR": "Liberia", "LY": "Libya", "LI": "Liechtenstein", "LT": "Lithuania", "LU": "Luxembourg",
    "MO": "Macao", "MG": "Madagascar", "MW": "Malawi", "MY": "Malaysia", "MV": "Maldives", "ML": "Mali",
    "MT": "Malta", "MH": "Marshall Islands", "MQ": "Martinique", "MR": "Mauritania", "MU": "Mauritius",
    "YT": "Mayotte", "MX": "Mexico", "FM": "Micronesia", "MD": "Moldova", "MC": "Monaco", "MN": "Mongolia",
    "ME": "Montenegro", "MS": "Montserrat", "MA": "Morocco", "MZ": "Mozambique", "MM": "Myanmar",
    "NA": "Namibia", "NR": "Nauru", "NP": "Nepal", "NL": "Netherlands", "NC": "New Caledonia", "NZ": "New Zealand",
    "NI": "Nicaragua", "NE": "Niger", "NG": "Nigeria", "NU": "Niue", "NF": "Norfolk Island",
    "MP": "Northern Mariana Islands", "NO": "Norway", "OM": "Oman", "PK": "Pakistan", "PW": "Palau",
    "PS": "Palestine", "PA": "Panama", "PG": "Papua New Guinea", "PY": "Paraguay", "PE": "Peru",
    "PH": "Philippines", "PN": "Pitcairn", "PL": "Poland", "PT": "Portugal", "PR": "Puerto Rico",
    "QA": "Qatar", "RE": "R\u00e9union", "RO": "Romania", "RU": "Russia", "RW": "Rwanda",
    "BL": "Saint Barth\u00e9lemy", "SH": "Saint Helena, Ascension and Tristan da Cunha", "KN": "Saint Kitts and Nevis",
    "LC": "Saint Lucia", "MF": "Saint Martin", "PM": "Saint Pierre and Miquelon",
    "VC": "Saint Vincent and the Grenadines", "WS": "Samoa", "SM": "San Marino",
    "ST": "Sao Tome and Principe", "SA": "Saudi Arabia", "SN": "Senegal", "RS": "Serbia",
    "SC": "Seychelles", "SL": "Sierra Leone", "SG": "Singapore", "SX": "Sint Maarten",
    "SK": "Slovakia", "SI": "Slovenia", "SB": "Solomon Islands", "SO": "Somalia",
    "ZA": "South Africa", "GS": "South Georgia and the South Sandwich Islands",
    "SS": "South Sudan", "ES": "Spain", "LK": "Sri Lanka", "SD": "Sudan", "SR": "Suriname",
    "SJ": "Svalbard and Jan Mayen", "SE": "Sweden", "CH": "Switzerland", "SY": "Syria",
    "TW": "Taiwan", "TJ": "Tajikistan", "TZ": "Tanzania", "TH": "Thailand", "TL": "Timor-Leste",
    "TG": "Togo", "TK": "Tokelau", "TO": "Tonga", "TT": "Trinidad and Tobago", "TN": "Tunisia",
    "TR": "Turkey", "TM": "Turkmenistan", "TC": "Turks and Caicos Islands", "TV": "Tuvalu",
    "UG": "Uganda", "UA": "Ukraine", "AE": "United Arab Emirates", "GB": "United Kingdom",
    "US": "United States", "UM": "United States Minor Outlying Islands", "UY": "Uruguay",
    "UZ": "Uzbekistan", "VU": "Vanuatu", "VE": "Venezuela", "VN": "Vietnam",
    "VG": "Virgin Islands (British)", "VI": "Virgin Islands (U.S.)", "WF": "Wallis and Futuna",
    "EH": "Western Sahara", "YE": "Yemen", "ZM": "Zambia", "ZW": "Zimbabwe"
 }


# Language code to full name mapping
LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
 "it": "Italian", "pt": "Portuguese", "ru": "Russian", "ja": "Japanese",
 "ko": "Korean", "zh": "Chinese", "ar": "Arabic", "hi": "Hindi",
 "tr": "Turkish", "nl": "Dutch", "pl": "Polish", "sv": "Swedish",
 "da": "Danish", "fi": "Finnish", "no": "Norwegian", "cs": "Czech",
 "ro": "Romanian", "hu": "Hungarian", "el": "Greek", "he": "Hebrew",
 "th": "Thai", "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay",
 "tl": "Filipino", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
 "mr": "Marathi", "ur": "Urdu", "sw": "Swahili",
 }


def extract_username_from_input(input_str):
    if not input_str or not isinstance(input_str, str):
        return ""
    clean_input = input_str.strip().lstrip('@')
    url_match = re.search(
        r"(?:https?://)?(?:www\.)?tiktok\.com/@([a-zA-Z0-9_.]+)(?:[/?]|$)",
        clean_input
    )
    return url_match.group(1) if url_match else clean_input


def extract_user_data(html):
    match = re.search(
        r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.+?)</script>',
        html, re.DOTALL
    )

    if not match:
        match = re.search(
            r'<script id="SIGI_STATE" type="application/json">(.+?)</script>',
            html, re.DOTALL
        )

    if not match or not match.group(1):
        raise ValueError("Data script not found (Possible Captcha).")

    json_data = json.loads(match.group(1))

    user_info = None
    stats = None

    if "__DEFAULT_SCOPE__" in json_data:
        user_detail = json_data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail")
        if user_detail:
            user_info = user_detail.get("userInfo", {}).get("user")
            stats = user_detail.get("userInfo", {}).get("stats") or user_detail.get("userInfo", {}).get("statsV2")

    elif "UserModule" in json_data:
        users_dict = json_data["UserModule"]["users"]
        stats_dict = json_data["UserModule"]["stats"]
        if users_dict:
            user_id = list(users_dict.keys())[0]
            user_info = users_dict[user_id]
            stats = stats_dict.get(user_id)

    if not user_info:
        raise ValueError("User info missing.")

    def safe_parse_int(val):
        try:
            return int(val) if val is not None else 0
        except:
            return 0

    final_stats = {
        "followers": f"{safe_parse_int(stats.get('followerCount')):,}",
        "following": f"{safe_parse_int(stats.get('followingCount')):,}",
        "hearts": f"{safe_parse_int(stats.get('heartCount')):,}",
        "videos": f"{safe_parse_int(stats.get('videoCount')):,}",
        "friends": f"{safe_parse_int(stats.get('friendCount')):,}"
    }

    region = user_info.get("region")
    if not region:
        region = user_info.get("location")
    if not region:
        region = "N/A"

    bio_link = user_info.get("bioLink", {}).get("link", "") if isinstance(user_info.get("bioLink"), dict) else ""

    create_time = "N/A"
    if user_info.get("createTime"):
        create_time = datetime.datetime.fromtimestamp(user_info["createTime"]).strftime('%Y-%m-%d %H:%M:%S')

    return {
        "nickname": user_info.get("nickname") or user_info.get("uniqueId"),
        "username": user_info.get("uniqueId"),
        "region": region,
        "language": user_info.get("language", "N/A"),
        "about": user_info.get("signature", "User has no about"),
        "userId": user_info.get("id"),
        "secUid": user_info.get("secUid", "N/A"),
        "bioLink": bio_link,
        "accountCreated": create_time,
        "avatar": user_info.get("avatarLarger", ""),
        "stats": final_stats
    }


def fetch_with_retry(url, base_headers, max_retries=3, use_cookie=False):
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(0.75 * attempt)

            current_headers = base_headers.copy()
            current_headers["User-Agent"] = (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
            )
            current_headers["Accept-Language"] = "en-US,en;q=0.9"

            if use_cookie and TIKTOK_COOKIE:
                current_headers["Cookie"] = TIKTOK_COOKIE

            response = requests.get(url, headers=current_headers, impersonate="chrome110", timeout=10)

            if response.status_code == 404:
                raise requests.exceptions.HTTPError("404 Not Found", response=response)

            response.raise_for_status()
            return response

        except Exception as e:
            if attempt == max_retries - 1:
                raise e

    raise Exception("Failed to fetch from TikTok after multiple attempts.")


def fetch_tiktok_profile(username):
    tiktok_url = f"https://www.tiktok.com/@{username}"
    base_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.tiktok.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
    }

    try:
        response = fetch_with_retry(tiktok_url, base_headers, 1, use_cookie=True)
        return extract_user_data(response.text)
    except Exception as e:
        return None


def format_profile(data):
    """Format profile data as a Discord-friendly string."""
    if not data:
        return "❌ User not found or inaccessible."

    region_code = data.get('region', 'N/A').upper()
    country = COUNTRY_CODES.get(region_code, region_code)
    stats = data.get('stats', {})

    lines = [
        f"**{data.get('nickname', 'N/A')}**",
        f"@{data.get('username', 'N/A')}",
        "",
        f"{get_flag(region_code)} {country} ({region_code})",
        "",
        # Locked region (same as region if not separately available)
        f"Locked Region: {get_flag(region_code)}",
        "",
        f"{country} ({region_code})",
        "",
        f"Language: {LANGUAGE_NAMES.get(data.get('language', '').lower(), data.get('language', 'N/A'))}",
        f"About: {data.get('about', 'User has no about')[:200]}",
        "",
        "**STATS**",
        f"👥 Followers: {stats.get('followers', '0')}",
        f"👣 Following: {stats.get('following', '0')}",
        f"❤️ Hearts: {stats.get('hearts', '0')}",
        f"🎬 Videos: {stats.get('videos', '0')}",
        f"🤝 Friends: {stats.get('friends', '0')}",
    ]

    if data.get('bioLink'):
        lines.append(f"🔗 Bio Link: {data['bioLink']}")

    lines.append(f"📅 Created: {data.get('accountCreated', 'N/A')}")

    return "\n".join(lines)


def get_flag(region_code):
    """Convert region code to flag emoji."""
    if not region_code or len(region_code) != 2:
        return ""
    code = region_code.upper()
    return chr(ord(code[0]) - ord('A') + 0x1F1E6) + chr(ord(code[1]) - ord('A') + 0x1F1E6)


if __name__ == "__main__":
    import sys
    username = sys.argv[1] if len(sys.argv) > 1 else "imdantheman"
    username = extract_username_from_input(username)
    print(f"[*] Looking up @{username}...")
    data = fetch_tiktok_profile(username)
    if data:
        print(format_profile(data))
    else:
        print("[-] Not found")
