"""Supporting references, not a claim to implement every SAT error condition."""
RULES = {
    'F01': {'sources': ['cfdi40', 'cfdi33', 'matrix40', 'matrix33'],
            'sat40': ['CFDI40205', 'CFDI40211', 'CFDI40221'], 'sat33': ['CFDI33183', 'CFDI33189', 'CFDI33195']},
    'F02': {'sources': ['cfdi40', 'cfdi33', 'matrix40', 'matrix33'],
            'sat40': ['CFDI40203', 'CFDI40211'], 'sat33': ['CFDI33181', 'CFDI33189']},
    'F03': {'sources': ['local10', 'cfdi40', 'cfdi33', 'standard40', 'standard33'],
            'sat40': ['CFDI40119'], 'sat33': ['CFDI33118']},
    'F04': {'sources': ['cfdi40', 'cfdi33', 'matrix40', 'matrix33'],
            'sat40': ['CFDI40177', 'CFDI40178', 'CFDI40184'], 'sat33': ['CFDI33157', 'CFDI33158', 'CFDI33166']},
    'F05': {'sources': ['cfdi40', 'cfdi33', 'matrix40', 'matrix33'],
            'sat40': ['CFDI40209', 'CFDI40205', 'CFDI40211', 'CFDI40221'],
            'sat33': ['CFDI33187', 'CFDI33183', 'CFDI33189', 'CFDI33195']},
    'F06': {'sources': ['types', 'standard40', 'standard33', 'catalog40', 'catalog33', 'faq40'],
            'sat40': ['CFDI40107', 'CFDI40108', 'CFDI40111', 'CFDI40167', 'CFDI40180', 'CFDI40186'],
            'sat33': ['CFDI33106', 'CFDI33107', 'CFDI33110', 'CFDI33149', 'CFDI33161', 'CFDI33169']},
    'CAT': {'sources': ['catalog40', 'catalog33'],
            'sat40': ['CFDI40179', 'CFDI40185', 'CFDI40219'], 'sat33': ['CFDI33159', 'CFDI33167', 'CFDI33193']},
    'SCOPE': {'sources': [], 'sat40': [], 'sat33': []},
}


def reference(rule, version):
    entry = RULES[rule]
    suffix = '40' if version == '4.0' else '33'
    return {'matrix_rule': rule, 'source_ids': [s for s in entry['sources'] if not s.endswith('33' if suffix == '40' else '40')],
            'supporting_sat_codes': entry['sat'+suffix]}
