"""Review the completeness of a user-verified journal profile, never certify it."""
from __future__ import annotations

from datetime import date
from urllib.parse import urlparse


def review_profile(profile, *, today=None):
    if not isinstance(profile, dict):
        raise ValueError("Journal profile must be a JSON object.")
    today = today or date.today()
    errors, warnings = [], []
    for key in ("journal", "article_type", "stage"):
        if not isinstance(profile.get(key), str) or not profile[key].strip():
            errors.append(f"Specify {key}.")
    urls = profile.get("source_urls", [])
    if not isinstance(urls, list):
        errors.append("source_urls must be an array of HTTPS URL strings.")
        urls = []
    if not urls:
        warnings.append("No official source URLs recorded; treat this as a planning profile.")
    for url in urls:
        if not isinstance(url, str) or urlparse(url).scheme != "https" or not urlparse(url).netloc:
            errors.append(f"Source must be a complete HTTPS URL: {url}")
    checked = profile.get("checked_on")
    if checked:
        try:
            checked_date = date.fromisoformat(checked)
            age = (today - checked_date).days
            if age < 0:
                errors.append("checked_on cannot be in the future.")
            elif age > 90:
                warnings.append(f"Source record is {age} days old; recheck before submission.")
        except (TypeError, ValueError):
            errors.append("checked_on must use YYYY-MM-DD.")
    else:
        warnings.append("Official requirements have no verification date.")
    for key in ("width_mm", "height_mm", "min_font_pt"):
        value = profile.get(key)
        if value is None:
            warnings.append(f"No {key} recorded; choose this from the exact journal/stage instructions.")
        elif isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value < 10000:
            errors.append(f"{key} must be a positive finite number.")
    formats = profile.get("submission_formats", [])
    if not isinstance(formats, list):
        errors.append("submission_formats must be an array of strings.")
        formats = []
    if not formats:
        warnings.append("Submission formats are unspecified. SVG remains the editable master.")
    elif "svg" not in [str(x).lower() for x in formats]:
        warnings.append("Keep the SVG master and submit a permitted companion format; SVG is not listed for submission.")
    if profile.get("status") != "source-checked":
        warnings.append("Profile is a planning aid, not a source-checked production instruction.")
    if profile.get("conflicting_sources") and not profile.get("resolution"):
        errors.append("Conflicting official requirements need a recorded stage-specific resolution.")
    return {"passed": not errors, "errors": errors, "warnings": warnings,
            "scope": "Profile field validation only; sources were not fetched or certified by this command.",
            "journal_acceptance": "not-certified", "profile": profile}
