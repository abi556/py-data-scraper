"""
Post-processing utilities for scraped tourism data.

Handles:
  1. Deduplication  – same business appearing under multiple service-type searches
  2. Location filter – removes results whose GPS coords fall outside the Arba Minch area
  3. Junk filter     – removes entries that are clearly not business names (e.g. descriptions)
  4. Merge with existing cleaned data – skip entries already in cleaned JSON
  5. Format output like cleaned JSON – with sources object combining data from different sources
"""

import logging
import re
import unicodedata
import json
import os
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger("PostProcess")

# ---------------------------------------------------------------------------
# Arba Minch bounding box (generous ~50 km radius)
#   Centre ≈ 6.03°N, 37.55°E
#   Includes Dorze (6.18°N), Lake Chamo, Nechisar NP, surrounding kebeles
# ---------------------------------------------------------------------------
ARBA_MINCH_LAT_MIN = 5.80
ARBA_MINCH_LAT_MAX = 6.35
ARBA_MINCH_LON_MIN = 37.25
ARBA_MINCH_LON_MAX = 37.85

# Service types that MUST be inside the Arba Minch area
LOCATION_STRICT_TYPES = {
    'hotels', 'hotel', 'motels', 'motel',
    'resorts', 'resort', 'lodges', 'lodge',
    'guest house', 'pension',
    'restaurants', 'restaurant',
    'accommodation', 'attraction',
    'cafe', 'shopping',  # Local businesses should be in Arba Minch
}

# Service types where wider locations are acceptable (e.g. Addis Ababa)
# car rental, tour agency, boat rental, helicopter ride, etc.
# These are NOT in the strict set, so they pass through.


# ---------------------------------------------------------------------------
# Coordinate extraction from Google Maps links
# ---------------------------------------------------------------------------
_COORD_RE = re.compile(r'!3d(-?[\d.]+)!4d(-?[\d.]+)')


def extract_coords_from_link(link: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) from a Google Maps link, or None."""
    if not link:
        return None
    m = _COORD_RE.search(link)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            return None
    return None


def is_in_arba_minch_area(lat: float, lon: float) -> bool:
    """Check if coordinates fall within the Arba Minch bounding box."""
    return (ARBA_MINCH_LAT_MIN <= lat <= ARBA_MINCH_LAT_MAX and
            ARBA_MINCH_LON_MIN <= lon <= ARBA_MINCH_LON_MAX)


# ---------------------------------------------------------------------------
# Name normalisation (for dedup)
# ---------------------------------------------------------------------------
def _normalise_name(name: str) -> str:
    """
    Lower-case, strip whitespace, remove leading numbering ("1. "),
    collapse multiple spaces, normalize common spelling variations.
    """
    s = name.strip().lower()
    # Remove leading "1. ", "2. " etc. (TripAdvisor numbering)
    s = re.sub(r'^\d+\.\s*', '', s)
    # Remove content in parentheses (Amharic alternate names)
    s = re.sub(r'\(.*?\)', '', s)
    # Normalise unicode
    s = unicodedata.normalize('NFKC', s)
    # Normalize common spelling variations for Arba Minch (standardize to "arbaminch" - no space)
    s = s.replace('arba minch', 'arbaminch')
    s = s.replace('arbminch', 'arbaminch')
    # Collapse whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    # Remove common suffixes that don't affect uniqueness
    s = re.sub(r'\s+(hotel|resort|lodge|restaurant|tour|agency|guide)\s*$', '', s)
    return s


# ---------------------------------------------------------------------------
# Junk detection
# ---------------------------------------------------------------------------
_JUNK_PATTERNS = [
    # TripAdvisor descriptions captured as names (long sentences)
    lambda n: len(n) > 100,
    # Starts with common description words
    lambda n: any(n.lower().startswith(w) for w in [
        'located in', 'nestled', 'perched', 'luxurious', 'centrally',
        'featuring', 'offering', 'a ', 'this '
    ]),
    # Contains multiple sentence-ending punctuation
    lambda n: n.count('.') >= 3,
]


def _is_junk_name(name: str) -> bool:
    """Return True if the name looks like a description, not a business name."""
    for check in _JUNK_PATTERNS:
        if check(name):
            return True
    return False


# ---------------------------------------------------------------------------
# Load existing cleaned data
# ---------------------------------------------------------------------------
def load_existing_cleaned_data(filepath: str = "data/arbaminch_tourism_cleaned.json") -> Dict[str, Dict]:
    """
    Load existing cleaned JSON and return a dict keyed by normalized name.
    Returns empty dict if file doesn't exist.
    """
    if not os.path.exists(filepath):
        logger.info(f"  No existing cleaned data found at {filepath}")
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        logger.info(f"  Loaded {len(existing)} existing entries from {filepath}")
        
        # Index by normalized name
        indexed = {}
        for item in existing:
            name = item.get('name', '')
            key = _normalise_name(name)
            if key:
                indexed[key] = item
        return indexed
    except Exception as e:
        logger.warning(f"  Error loading existing data: {e}")
        return {}


# ---------------------------------------------------------------------------
# Main post-processing pipeline
# ---------------------------------------------------------------------------
def deduplicate_and_filter(data: List[Dict], existing_data: Optional[Dict[str, Dict]] = None) -> Tuple[List[Dict], Dict[str, Dict]]:
    """
    1. Remove junk entries (descriptions captured as names)
    2. Remove location-strict entries outside Arba Minch
    3. Skip entries already in existing cleaned data
    4. Deduplicate and merge by normalised name
    5. Format output like cleaned JSON with sources object

    Returns a new list in the cleaned JSON format.
    """
    before_count = len(data)
    
    if existing_data is None:
        existing_data = load_existing_cleaned_data()

    # --- Pass 1: remove junk names ---
    cleaned = []
    junk_count = 0
    for item in data:
        name = item.get('name', '')
        if _is_junk_name(name):
            junk_count += 1
            logger.debug(f"  Junk removed: {name[:60]}...")
            continue
        # Clean leading numbering from TripAdvisor names (e.g. "1. Haile Resort")
        stripped = re.sub(r'^\d+\.\s*', '', name).strip()
        if stripped != name:
            item = {**item, 'name': stripped}
        cleaned.append(item)

    if junk_count:
        logger.info(f"  Removed {junk_count} junk entries (descriptions, not names)")

    # --- Pass 2: location filtering ---
    location_filtered = []
    location_removed = 0
    for item in cleaned:
        stype = item.get('type', '').lower()
        link = item.get('link', '')
        source = item.get('source', '')

        # Filter by GPS coordinates for strict location types
        # Check any link that contains Google Maps coordinates (even if source is different)
        if stype in LOCATION_STRICT_TYPES and 'google.com/maps' in link:
            coords = extract_coords_from_link(link)
            if coords:
                lat, lon = coords
                if not is_in_arba_minch_area(lat, lon):
                    location_removed += 1
                    logger.debug(f"  Out of area: {item.get('name')} ({lat:.2f}, {lon:.2f}) [{source}]")
                    continue
        
        # For other sources (Expedia, Agoda, Booking.com, etc.), they're already filtered
        # by the search query, but we still check if they have Google Maps links
        location_filtered.append(item)

    if location_removed:
        logger.info(f"  Removed {location_removed} entries outside Arba Minch area")

    # --- Pass 3: Separate new entries from updates to existing ---
    new_entries = []
    updates_to_existing: Dict[str, Dict] = {}
    skipped_existing = 0
    
    for item in location_filtered:
        key = _normalise_name(item.get('name', ''))
        if not key:
            continue
        
        # Check if already in existing cleaned data
        if key in existing_data:
            # Check if this is a new source for an existing entry
            source = item.get('source', '')
            existing_entry = existing_data[key]
            existing_sources = existing_entry.get('sources', {})
            
            if source not in existing_sources:
                # New source for existing entry - add to updates
                if key not in updates_to_existing:
                    updates_to_existing[key] = {
                        'name': item.get('name', ''),
                        'types': [],
                        'sources': {}
                    }
                updates_to_existing[key]['sources'][source] = _extract_source_data(item)
                item_type = item.get('type', '')
                if item_type and item_type not in updates_to_existing[key]['types']:
                    updates_to_existing[key]['types'].append(item_type)
                logger.debug(f"  New source '{source}' for existing: {item.get('name')}")
            else:
                skipped_existing += 1
                logger.debug(f"  Skipping duplicate source: {item.get('name')} from {source}")
            continue
        
        new_entries.append(item)
    
    if skipped_existing:
        logger.info(f"  Skipped {skipped_existing} entries with duplicate sources")
    if updates_to_existing:
        logger.info(f"  Found {len(updates_to_existing)} existing entries with new sources to merge")

    # --- Pass 4: Merge and format like cleaned JSON ---
    # Group by normalized name and merge into cleaned JSON format
    merged: Dict[str, Dict] = {}
    
    for item in new_entries:
        key = _normalise_name(item.get('name', ''))
        if not key:
            continue
        
        name = item.get('name', '').strip()
        item_type = item.get('type', '')
        source = item.get('source', '')
        
        if key not in merged:
            # Create new entry in cleaned format
            merged[key] = {
                'name': name,
                'types': [item_type] if item_type else [],
                'sources': {}
            }
            
            # Add category if present
            category = item.get('category', '')
            if category and category not in ('', 'N/A', 'No reviews', 'Sponsored'):
                merged[key]['categories'] = [category]
        
        # Add/update source information
        if source not in merged[key]['sources']:
            merged[key]['sources'][source] = {}
        
        source_data = merged[key]['sources'][source]
        
        # Add link
        if item.get('link'):
            source_data['link'] = item.get('link')
        
        # Add rating
        rating = item.get('rating', '')
        if rating and rating != 'N/A':
            source_data['rating'] = rating
        
        # Add price (for Booking.com, Expedia, Agoda)
        price = item.get('price', '')
        if price and price != 'N/A':
            source_data['price'] = price
        
        # Add review_score (for Booking.com)
        review_score = item.get('review_score', '')
        if review_score and review_score != 'N/A':
            source_data['review_score'] = review_score
        
        # Add address
        address = item.get('address', '')
        if address and address != 'N/A' and address != 'Arba Minch':
            source_data['address'] = address
        
        # Merge types
        if item_type and item_type not in merged[key]['types']:
            merged[key]['types'].append(item_type)
        
        # Merge categories
        category = item.get('category', '')
        if category and category not in ('', 'N/A', 'No reviews', 'Sponsored'):
            if 'categories' not in merged[key]:
                merged[key]['categories'] = []
            if category not in merged[key]['categories']:
                merged[key]['categories'].append(category)
    
    # Convert to list and clean up empty categories
    result = []
    for key, entry in merged.items():
        # Remove empty categories array
        if 'categories' in entry and not entry['categories']:
            del entry['categories']
        result.append(entry)
    
    # Count duplicates within new data
    dup_count = len(new_entries) - len(merged)
    if dup_count:
        logger.info(f"  Merged {dup_count} duplicate entries from new data")

    # Summary
    total_removed = junk_count + location_removed + skipped_existing + dup_count
    logger.info("-" * 40)
    logger.info(f"  CLEANING SUMMARY:")
    logger.info(f"    Initial entries: {before_count}")
    logger.info(f"    Junk removed: {junk_count}")
    logger.info(f"    Out-of-area removed: {location_removed}")
    logger.info(f"    Already in cleaned data: {skipped_existing}")
    logger.info(f"    Duplicates merged: {dup_count}")
    logger.info(f"    New unique entries: {len(result)}")
    logger.info(f"    Total removed/skipped: {total_removed}")
    logger.info("-" * 40)
    
    return result, updates_to_existing


def _extract_source_data(item: Dict) -> Dict:
    """Extract source-specific data from an item."""
    source_data = {}
    
    if item.get('link'):
        source_data['link'] = item.get('link')
    
    rating = item.get('rating', '')
    if rating and rating != 'N/A':
        source_data['rating'] = rating
    
    price = item.get('price', '')
    if price and price != 'N/A':
        source_data['price'] = price
    
    review_score = item.get('review_score', '')
    if review_score and review_score != 'N/A':
        source_data['review_score'] = review_score
    
    address = item.get('address', '')
    if address and address not in ('N/A', 'Arba Minch'):
        source_data['address'] = address
    
    return source_data


def _richness_score(item: Dict) -> int:
    """Score how many useful fields an entry has populated."""
    score = 0
    for key in ['name', 'rating', 'price', 'address', 'review_score',
                 'reviews', 'category', 'link', 'cuisine']:
        val = item.get(key, '')
        if val and str(val) not in ('N/A', '', 'Unknown', 'Unknown Property'):
            score += 1
    return score


