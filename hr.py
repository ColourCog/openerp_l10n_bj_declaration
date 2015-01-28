#-*- coding:utf-8 -*-
from openerp.osv import fields, osv

import openerp.addons.decimal_precision as dp

class res_company(osv.osv):
    _inherit = 'res.company'

    _columns = {
        "cnss_number": fields.char("CNSS number", size=256),
        "insae_number": fields.char("INSAE number", size=256),
        "ifu_number": fields.char("IFU number", size=256),
        "activity": fields.char('Activity', size=256),
        "other_name": fields.char('Other Name', size=256),
    }
res_company()

class hr_employee(osv.osv):
    _inherit = "hr.employee"

    _columns = {
        "cnss_number": fields.char("CNSS number", size=256),
        "ifu_number": fields.char("IFU number", size=256),
    }

hr_employee()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
