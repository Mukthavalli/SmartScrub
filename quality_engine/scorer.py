def compute_score(analysis: dict) -> dict:
    """
    Compute overall quality score (0-100) and 5 dimension scores.
    Fully schema-agnostic — works on any dataset.
    """
    rows = analysis['shape']['rows']
    cols = analysis['shape']['cols']
    total_cells = analysis['total_cells']

    # ── 1. Completeness (30%) ──────────────────────────────────────────────
    missing_pct = analysis['missing']['pct']
    completeness = max(0.0, 100 - missing_pct * 5.0) # More strict: 20% missing = 0 score

    # ── 2. Uniqueness (20%) ───────────────────────────────────────────────
    dup_pct = analysis['duplicates']['pct']
    uniqueness = max(0.0, 100 - dup_pct * 4.0)

    # ── 3. Validity (20%) ────────────────────────────────────────────────
    type_issues = analysis.get('type_issues', 0)
    empty_col_count = len(analysis.get('empty_columns', []))
    validity_penalty = (type_issues / cols * 60) + (empty_col_count / cols * 40) if cols else 0
    validity = max(0.0, 100 - validity_penalty)

    # ── 4. Consistency (15%) ─────────────────────────────────────────────
    inconsistencies = analysis.get('inconsistencies', 0)
    consistency_penalty = (inconsistencies / cols * 80) if cols else 0
    consistency = max(0.0, 100 - consistency_penalty)

    # ── 5. Accuracy (15%) ────────────────────────────────────────────────
    outlier_count = analysis.get('outliers', 0)
    outlier_pct = (outlier_count / rows * 100) if rows else 0
    accuracy = max(0.0, 100 - outlier_pct * 8.0) # More strict: 12.5% outliers = 0 score

    # ── Weighted Overall & Bottleneck Penalty ──────────────────────────────
    weighted_overall = (
        completeness * 0.30 +
        uniqueness * 0.20 +
        validity * 0.20 +
        consistency * 0.15 +
        accuracy * 0.15
    )

    # Introduce a bottleneck penalty: if any single quality dimension is very poor, 
    # it drags down the overall score by up to 15% of the deficit.
    min_dim = min(completeness, uniqueness, validity, consistency, accuracy)
    bottleneck_penalty = (100 - min_dim) * 0.15
    overall = max(0.0, weighted_overall - bottleneck_penalty)

    def grade(score):
        if score >= 92: return ('Excellent', '#00e676')
        if score >= 78: return ('Good', '#69f0ae')
        if score >= 55: return ('Fair', '#ffab40')
        if score >= 35: return ('Poor', '#ff7043')
        return ('Critical', '#f44336')

    overall_r = round(overall, 1)
    label, color = grade(overall_r)

    return {
        'overall': overall_r,
        'label': label,
        'color': color,
        'dimensions': {
            'Completeness': round(completeness, 1),
            'Uniqueness': round(uniqueness, 1),
            'Validity': round(validity, 1),
            'Consistency': round(consistency, 1),
            'Accuracy': round(accuracy, 1),
        }
    }
