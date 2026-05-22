"""
Extract bill data from petrol pump bill images using Tesseract OCR.
Uses regex patterns to parse Indian petrol pump bill fields.
"""

import re
from PIL import Image, ImageEnhance, ImageOps
import pytesseract


def extract_text_from_image(image_path: str) -> list[str]:
    """Extract all text lines from an image using Tesseract OCR."""
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)

    # Red channel to remove pink background
    red = img.split()[0]
    red = ImageEnhance.Contrast(red).enhance(2.5)
    red = ImageEnhance.Sharpness(red).enhance(2.0)

    # Grayscale with high contrast
    gray = img.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(3.0)

    text_red = pytesseract.image_to_string(red, lang="eng", config="--psm 6")
    text_gray = pytesseract.image_to_string(gray, lang="eng", config="--psm 6")

    lines_red = [l.strip() for l in text_red.split("\n") if l.strip()]
    lines_gray = [l.strip() for l in text_gray.split("\n") if l.strip()]

    return lines_red + lines_gray


def _parse_date(lines: list[str], full_text: str) -> str | None:
    for line in lines:
        match = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", line)
        if match:
            day, month, year = match.groups()
            if len(year) == 2:
                year = "20" + year
            return f"{day.zfill(2)}/{month.zfill(2)}/{year}"

    match = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", full_text)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = "20" + year
        return f"{day.zfill(2)}/{month.zfill(2)}/{year}"

    return None


def _parse_vehicle_no(lines: list[str], full_text: str) -> str | None:
    pattern = r"[A-Z]{2}\s*\d{1,2}\s*[A-Z]{1,3}\s*\d{4}"
    for line in lines:
        upper = line.upper()
        match = re.search(pattern, upper)
        if match:
            return re.sub(r"\s+", "", match.group())

    match = re.search(pattern, full_text.upper())
    if match:
        return re.sub(r"\s+", "", match.group())

    return None


def _parse_fuel_type(full_text: str) -> str | None:
    upper = full_text.upper()
    if any(kw in upper for kw in ["H.S.D", "HSD", "H S D", "DIESEL", "HIGH SPEED"]):
        return "HSD"
    elif any(kw in upper for kw in ["M.S.", "MS ", "PETROL", "MOTOR SPIRIT"]):
        return "MS"
    elif any(kw in upper for kw in ["XP", "EXTRA PREMIUM", "XTRA"]):
        return "XP"
    return None


def _parse_litres(lines: list[str]) -> float | None:
    for line in lines:
        lower = line.lower()
        if any(kw in lower for kw in ["ltr", "litr", "ltrs", "litres", "liters"]):
            numbers = re.findall(r"(\d+\.?\d*)", line)
            for num_str in numbers:
                num = float(num_str)
                if 0.5 < num < 50000:
                    return num

    for line in lines:
        match = re.search(r"(\d{1,4}\.\d{1,2})", line)
        if match:
            num = float(match.group(1))
            if 0.5 < num < 10000:
                return num

    return None


def _parse_amounts(lines: list[str]) -> tuple[float | None, float | None, float | None]:
    """Returns (fuel_amount, cash_to_driver, total_bill)."""
    all_amounts = []
    for line in lines:
        cleaned = line.replace(",", "").replace("\u20b9", "").replace("Rs", "").replace("rs", "")
        numbers = re.findall(r"(\d{3,}\.?\d*)", cleaned)
        for num_str in numbers:
            num = float(num_str)
            if num >= 100:
                all_amounts.append(num)

    fuel_amount = None
    cash_to_driver = None
    total_bill = None

    for line in lines:
        lower = line.lower()
        cleaned = line.replace(",", "")

        if any(kw in lower for kw in ["total", "amt", "amount"]):
            numbers = re.findall(r"(\d{3,}\.?\d*)", cleaned)
            if numbers:
                total_bill = float(numbers[-1])

        if any(kw in lower for kw in ["cash", "nkd", "nkad", "nakad", "nakdi"]):
            numbers = re.findall(r"(\d{3,}\.?\d*)", cleaned)
            if numbers:
                cash_to_driver = sum(float(n) for n in numbers)

    if fuel_amount is None and all_amounts:
        remaining = [a for a in all_amounts if a != total_bill]
        if remaining:
            fuel_amount = max(remaining)

    if total_bill and fuel_amount and cash_to_driver is None:
        diff = total_bill - fuel_amount
        if diff > 0:
            cash_to_driver = diff

    if total_bill is None and fuel_amount:
        total_bill = fuel_amount + (cash_to_driver or 0)

    return fuel_amount, cash_to_driver, total_bill


def _parse_party_name(lines: list[str]) -> str | None:
    skip_keywords = [
        "bharat", "petroleum", "indian oil", "hindustan",
        "corp", "ltd", "pump", "filling", "station",
        "credit", "memo", "bill", "receipt", "invoice",
        "date", "no.", "sr.", "s.no", "sl.",
        "vill", "village", "nh-", "national highway",
        "punjab", "haryana", "delhi", "rajasthan",
        "dealer", "service", "resort",
    ]

    for line in lines[:8]:
        lower = line.lower().strip()
        if len(lower) < 2:
            continue
        if any(kw in lower for kw in skip_keywords):
            continue
        if re.match(r"^[\d\s/\-.,|:;]+$", lower):
            continue
        if 2 <= len(line.strip()) <= 30:
            return line.strip().upper()

    return None


def extract_bill_data(image_path: str) -> dict:
    """Extract structured data from a petrol pump bill image."""
    lines = extract_text_from_image(image_path)
    full_text = " ".join(lines)

    date = _parse_date(lines, full_text)
    vehicle_no = _parse_vehicle_no(lines, full_text)
    fuel_type = _parse_fuel_type(full_text)
    litres = _parse_litres(lines)
    fuel_amount, cash_to_driver, total_bill = _parse_amounts(lines)
    party_name = _parse_party_name(lines)

    rate_per_litre = None
    if litres and fuel_amount and litres > 0:
        rate_per_litre = round(fuel_amount / litres, 2)

    return {
        "date": date,
        "party_name": party_name,
        "vehicle_no": vehicle_no,
        "fuel_type": fuel_type,
        "litres": litres,
        "rate_per_litre": rate_per_litre,
        "fuel_amount": fuel_amount,
        "cash_to_driver": cash_to_driver or 0,
        "total_bill": total_bill,
        "notes": None,
        "raw_text": lines,
    }
