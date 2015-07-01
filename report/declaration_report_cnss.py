# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.report import report_sxw


class declaration_report_cnss(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(declaration_report_cnss, self).__init__(
                cr,
                uid,
                name,
                context=context)
        self.localcontext.update({
            'time': time,
            'subset': self._get_rule_subset,
            'merge': self._merge_rule_subsets,
            'sum_line': self._sum_line,
            'totals': self._get_totals,
            'reformat': self._reformat,
        })

    def _reformat(self, obj, patt):
        return datetime.strptime(obj, '%d/%m/%Y').strftime(patt)

    def _merge_rule_subsets(self, obj, code):
        return zip(
            self._get_rule_subset(obj, code),
            range(1, len(self._get_rule_subset(obj, code))+1)
            )

    def _get_rule_subset(self, obj, code):
        return [i for i in obj if i.rule_id.code == code]

    def _sum_line(self, obj, attr):
        return sum([getattr(i, attr) for i in obj])

    def _get_totals(self, obj):
        res = {}
        for o in obj:
            # initialise
            if not res.get(o.rule_id.name):
                res[o.rule_id.name] = 0
            res[o.rule_id.name] += o.total
        return res.items()


report_sxw.report_sxw(
    'report.declaration.cnss',
    'declaration.report',
    'addons/l10n_bj_declaration/report/declaration_report_cnss.rml',
    parser=declaration_report_cnss,
    header="external")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
