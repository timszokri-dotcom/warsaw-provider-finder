"""Step 1: download mapped Warsaw car-repair locations from Overpass."""
import csv
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
ENDPOINT = 'https://overpass-api.de/api/interpreter'


def main():
    query = (ROOT / 'query.overpassql').read_text()
    request = urllib.request.Request(
        ENDPOINT,
        data=urllib.parse.urlencode({'data': query}).encode('utf-8'),
        headers={'User-Agent': 'WarsawProviderFinder/0.1 (educational research)',
                 'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST',
    )
    print('Requesting mapped car-repair locations in Warsaw...', flush=True)
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = json.load(response)

    # Save the source before transforming it, including diagnostic responses.
    output = ROOT / 'data'
    output.mkdir(exist_ok=True)
    (output / 'raw_response.json').write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    if payload.get('remark'):
        raise ValueError('Overpass reported a problem: ' + payload['remark'])
    elements = payload['elements']
    boundaries = [item for item in elements if item['type'] == 'area']
    if len(boundaries) != 1:
        raise ValueError('Expected exactly one Warsaw administrative area')

    rows, seen = [], set()
    for item in elements:
        if item['type'] == 'area':
            continue
        tags = item.get('tags', {})
        if tags.get('shop') != 'car_repair':
            raise ValueError('Unexpected business category')
        key = (item['type'], item['id'])
        if key in seen:
            raise ValueError('Duplicate OSM object')
        seen.add(key)
        location = item if item['type'] == 'node' else item.get('center', {})
        lat, lon = location.get('lat'), location.get('lon')
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('Missing or invalid coordinates')
        rows.append({
            'osm_type': item['type'], 'osm_id': item['id'],
            'name': tags.get('name', ''), 'latitude': lat, 'longitude': lon,
            'street': tags.get('addr:street', ''),
            'house_number': tags.get('addr:housenumber', ''),
            'postcode': tags.get('addr:postcode', ''),
            'phone': tags.get('contact:phone') or tags.get('phone', ''),
            'website': tags.get('contact:website') or tags.get('website', ''),
            'opening_hours': tags.get('opening_hours', ''),
            'osm_url': 'https://www.openstreetmap.org/%s/%s' % key,
        })
    if not rows:
        raise ValueError('No locations returned; inspect raw_response.json')
    with (output / 'providers.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        'mapped_locations': len(rows),
        'with_name': sum(bool(r['name']) for r in rows),
        'with_phone': sum(bool(r['phone']) for r in rows),
        'with_website': sum(bool(r['website']) for r in rows),
        'source_timestamp': payload.get('osm3s', {}).get('timestamp_osm_base'),
        'boundary': boundaries[0],
    }
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != 'boundary'}, indent=2))
    print('Saved data/raw_response.json, data/providers.csv, and data/summary.json')


if __name__ == '__main__':
    main()
