import os
import json


def generate_suggestions(analysis: dict, scores: dict) -> list:
    """
    Generate AI/smart suggestions. Uses Gemini API if key is set,
    otherwise falls back to rich rule-based suggestions.
    """
    gemini_key = os.environ.get('GEMINI_API_KEY', '')
    if gemini_key:
        try:
            return _gemini_suggestions(analysis, scores, gemini_key)
        except Exception:
            pass
    return _rule_based_suggestions(analysis, scores)


def _gemini_suggestions(analysis: dict, scores: dict, api_key: str) -> list:
    import urllib.request
    summary = {
        'rows': analysis['shape']['rows'],
        'cols': analysis['shape']['cols'],
        'missing_pct': analysis['missing']['pct'],
        'duplicate_pct': analysis['duplicates']['pct'],
        'outliers': analysis['outliers'],
        'type_issues': analysis['type_issues'],
        'overall_score': scores['overall'],
        'score_label': scores['label'],
        'top_issues': [
            {'column': c['name'], 'issues': [i['type'] for i in c['issues']]}
            for c in sorted(analysis['columns'], key=lambda x: x['issue_count'], reverse=True)[:5]
            if c['issue_count'] > 0
        ]
    }

    prompt = f"""You are a data quality expert. Analyze this dataset quality summary and provide 5 concise, actionable suggestions:

Dataset Summary: {json.dumps(summary, indent=2)}

Respond with a JSON array of exactly 5 objects, each with:
- "priority": "High"/"Medium"/"Low"
- "category": short category name
- "suggestion": one-sentence actionable recommendation

Only output valid JSON array, no other text."""

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode('utf-8')

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')

    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode())

    text = result['candidates'][0]['content']['parts'][0]['text']
    # Clean markdown code fences if any
    text = text.strip().strip('```json').strip('```').strip()
    suggestions = json.loads(text)
    return suggestions[:5]


def _rule_based_suggestions(analysis: dict, scores: dict) -> list:
    suggestions = []
    dims = scores['dimensions']

    # Missing values
    if dims['Completeness'] < 80:
        worst_missing = sorted(
            [c for c in analysis['columns'] if c['missing_pct'] > 0],
            key=lambda x: x['missing_pct'], reverse=True
        )[:2]
        cols_str = ', '.join([f"'{c['name']}' ({c['missing_pct']}%)" for c in worst_missing])
        suggestions.append({
            'priority': 'High',
            'category': 'Missing Data',
            'suggestion': f"Address missing values — worst columns: {cols_str}. Use median imputation for numerics and mode for categoricals."
        })

    # Duplicates
    if analysis['duplicates']['count'] > 0:
        suggestions.append({
            'priority': 'High',
            'category': 'Duplicates',
            'suggestion': f"Remove {analysis['duplicates']['count']} duplicate row(s) ({analysis['duplicates']['pct']}%). Use the Auto-Fix feature to clean them instantly."
        })

    # Outliers
    if analysis['outliers'] > 0:
        outlier_cols = [c['name'] for c in analysis['columns'] if c['outlier_count'] > 0]
        suggestions.append({
            'priority': 'Medium',
            'category': 'Outliers',
            'suggestion': f"Investigate {analysis['outliers']} outlier(s) in column(s): {', '.join(outlier_cols[:3])}. Consider capping or removal depending on business context."
        })

    # Type issues
    if analysis['type_issues'] > 0:
        mixed_cols = [c['name'] for c in analysis['columns'] if c['type_issues'] > 0]
        suggestions.append({
            'priority': 'High',
            'category': 'Data Types',
            'suggestion': f"Column(s) {', '.join(mixed_cols[:3])} contain mixed data types. Standardize to a single type to prevent analysis errors."
        })

    # Inconsistency
    if analysis['inconsistencies'] > 0:
        inc_cols = [c['name'] for c in analysis['columns'] if c['inconsistency_count'] > 0]
        suggestions.append({
            'priority': 'Medium',
            'category': 'Consistency',
            'suggestion': f"Standardize format variations in column(s): {', '.join(inc_cols[:3])}. Examples: unify 'Male/male/M' to a single format."
        })

    # Empty / constant columns
    if analysis['empty_columns']:
        suggestions.append({
            'priority': 'Medium',
            'category': 'Empty Columns',
            'suggestion': f"Drop {len(analysis['empty_columns'])} empty column(s): {', '.join(analysis['empty_columns'][:3])}. They add no analytical value."
        })

    # Overall excellent
    if scores['overall'] >= 90:
        suggestions.append({
            'priority': 'Low',
            'category': 'Great Quality!',
            'suggestion': "Your dataset has excellent quality. Consider documenting the data dictionary and setting up automated quality checks to maintain this standard."
        })

    # Pad to 3 suggestions minimum
    if not suggestions:
        suggestions.append({
            'priority': 'Low',
            'category': 'General',
            'suggestion': "Dataset looks generally clean. Review column naming conventions and add metadata documentation for better maintainability."
        })

    return suggestions[:6]
