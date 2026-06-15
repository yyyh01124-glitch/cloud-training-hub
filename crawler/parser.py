import json
from app.extensions import db
from app.models import CrawlerData


def parse_and_save(results, config):
    """Save crawled results to database, skipping duplicates."""
    count = 0
    for item in results:
        existing = CrawlerData.query.filter_by(data_hash=item.get('data_hash', '')).first()
        if existing:
            continue

        keywords_matched = []
        if config.keywords:
            title = item.get('title', '')
            for kw in config.keywords.split(','):
                if kw.strip().lower() in title.lower():
                    keywords_matched.append(kw.strip())

        raw_json = None
        try:
            raw_json = json.dumps(item, ensure_ascii=False)
        except Exception:
            raw_json = json.dumps({'title': item.get('title', '')}, ensure_ascii=False)

        data = CrawlerData(
            config_id=config.id,
            title=item.get('title', '')[:500],
            url=item.get('url', '')[:1000],
            summary=item.get('summary', '')[:2000],
            source_type=item.get('source_type', config.source_type),
            keywords_matched=','.join(keywords_matched)[:300] if keywords_matched else '',
            raw_data=raw_json,
            pub_date=item.get('pub_date', '')[:50],
            data_hash=item.get('data_hash', '')[:64]
        )
        db.session.add(data)
        count += 1

    if count > 0:
        db.session.commit()
    return count
