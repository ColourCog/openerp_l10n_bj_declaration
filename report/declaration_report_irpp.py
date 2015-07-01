# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from datetime import datetime
from openerp.report import report_sxw

class declaration_report_irpp(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(declaration_report_irpp, self).__init__(cr, uid, name, context=context)
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
        
    def _merge_rule_subsets(self, obj, code, ocode):
        return zip(
            self._get_rule_subset(obj, code),
            self._get_rule_subset(obj, ocode),
            range(1,len(self._get_rule_subset(obj, ocode))+1)
            )
        
    def _get_rule_subset(self, obj, code):
        return [i for i in obj if i.rule_id.code == code]
    
    def _sum_line(self, obj, attr):
        return sum([getattr(i, attr) for i in obj])
    
    def _get_totals(self, obj):
        res = {}
        for o in obj:
            #initialise
            if not res.get(o.rule_id.name):
                res[o.rule_id.name] = 0
            res[o.rule_id.name] += o.total
        return res.items()    

report_sxw.report_sxw(
    'report.declaration.irpp', 
    'declaration.report', 
    'addons/l10n_bj_declaration/report/declaration_report_irpp.rml', 
    parser=declaration_report_irpp, 
    header="external")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

