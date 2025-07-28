"""
Configuration settings for media plan validation
"""

# AI Strategy Validation Prompt Template
AI_STRATEGY_PROMPT = """
Compare this campaign brief with the media plan strategy and evaluate consistency:

CAMPAIGN BRIEF:
Business: {business_description} in {business_location}
Target Market: {target_market}
Objectives: {objectives}
Budget: {budget}
Existing Platforms (for reference only): {platforms}

MEDIA PLAN STRATEGY:
{strategy_text}

Evaluate if the strategy logically matches the brief. Note that platforms listed in the brief are existing user platforms for reference only - the strategy may choose different or additional platforms as appropriate.

Focus on:
1. Does the strategy address the right target audience?
2. Are the chosen platforms appropriate for the business and objectives?
3. Is the strategy realistic for the given budget?
4. Does the overall approach align with the business context and objectives?

Respond with: CONSISTENT, INCONSISTENT, or PARTIALLY_CONSISTENT followed by a brief explanation.
"""

# Currency detection patterns
CURRENCY_PATTERNS = [
    r'[€$£¥₹₽][\s]*[\d,]+\.?\d*',  # €1,000 or $500.00
    r'[\d,]+\.?\d*[\s]*[€$£¥₹₽]',  # 1,000€ or 500.00$
    r'EUR[\s]+[\d,]+\.?\d*',       # EUR 1000
    r'USD[\s]+[\d,]+\.?\d*',       # USD 500
    r'GBP[\s]+[\d,]+\.?\d*',       # GBP 800
]

# Platform/channel keywords for detection
PLATFORM_KEYWORDS = [
    'meta', 'facebook', 'instagram', 'google', 'youtube', 'tiktok',
    'search', 'display', 'programmatic', 'microsoft', 'linkedin',
    'twitter', 'snapchat', 'pinterest'
]

# Objective keywords that might precede budgets
OBJECTIVE_KEYWORDS = [
    'sales', 'traffic', 'awareness', 'leads', 'conversions', 'visits',
    'installs', 'subscriptions', 'engagement', 'reach', 'impressions'
]

# Section detection patterns
STRATEGY_EXPLAINER_PATTERNS = [
    r'2\.\s*strategy\s*explainer',
    r'2\)\s*strategy\s*explainer',
    r'strategy\s*explainer\s*:',
    r'2\s*-\s*strategy\s*explainer'
]

# Table field mappings
TABLE_FIELD_MAPPINGS = {
    'cost_fields': ['cost', 'budget', 'spend', 'total cost', 'investment'],
    'platform_fields': ['platform', 'channel', 'media channel', 'advertising platform'],
    'objective_fields': ['objective', 'goal', 'target', 'kpi', 'campaign objective']
}

# Channel name normalizations
CHANNEL_NORMALIZATIONS = {
    'facebook': 'meta (facebook)',
    'instagram': 'meta (instagram)',
    'meta combined': 'meta (combined)',
    'meta (fb)': 'meta (facebook)',
    'meta (ig)': 'meta (instagram)',
    'google search': 'google search',
    'google display network': 'google display',
    'google responsive display': 'google display',
    'youtube': 'youtube ads',
    'tiktok': 'tiktok ads',
    'microsoft search': 'microsoft search',
    'microsoft audience network': 'microsoft audience'
}

# Validation tolerances
DEFAULT_BUDGET_TOLERANCE = 0.05  # 5%
DEFAULT_DURATION_TOLERANCE_DAYS = 1