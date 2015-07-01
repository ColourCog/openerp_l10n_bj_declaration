#-*- coding:utf-8 -*-
import time
from datetime import datetime
from dateutil import relativedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class declaration_report_line(osv.osv):
    _name = 'declaration.report.line'
    _order = "name"
    _columns = {
        'declaration_id': fields.many2one('declaration.report', 'Declaration', ondelete='cascade'),
        'name' : fields.char('Name', size=256, select=True, readonly=True),
        'employee_id' : fields.many2one('hr.employee', 'Employee'),
        'rule_id' : fields.many2one('hr.salary.rule', 'Rule'),
        'account_id': fields.many2one('account.account', 'Debit Account'),
        'gross' : fields.float('Gross', digits_compute=dp.get_precision('Account')),
        'total' : fields.float('Amount', digits_compute=dp.get_precision('Account')),

    }

declaration_report_line()


class declaration_report(osv.osv):
    _name = 'declaration.report'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Benin Payroll Declaration'
    _track = {
        'state': {
          'declaration_report.mt_declaration_confirmed': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'confirmed',
          'declaration_report.mt_declaration_paid': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'paid',
        },
    }

    def _get_currency(self, cr, uid, context=None):
        res = False
        cur_obj = self.pool.get('res.currency')
        currency_ids = cur_obj.search(cr, uid, [("name","=","XOF")], context=context)
        return currency_ids[0]

    _columns = {
        'name' : fields.char('Name', size=64, select=True, readonly=True),
        'partner_id': fields.related('prep_id', 'partner_id', type='many2one', string='Due to', relation='res.partner', readonly=True),
        'prep_id': fields.many2one('declaration.prep', 'Settings', required=True),
        'bank_id': fields.many2one('res.partner.bank', 'Payment Bank', required=True),
        'line_ids':fields.one2many('declaration.report.line', 'declaration_id', 'Payslip Lines'),
        'format': fields.related('prep_id', 'format', type='char', string='Printout format', relation='declaration.prep', readonly=True),
        'move_id': fields.many2one('account.move', 'Transfer to Supplier Account', readonly=True),
        'voucher_id': fields.many2one('account.voucher', 'Payment voucher', readonly=True),
        'amount' : fields.float('Amount due', digits_compute=dp.get_precision('Account'), readonly=True),
        'date_from': fields.date('Date From', required=True),
        'date_to': fields.date('Date To', required=True),
        'date_confirm' : fields.date('Date', select=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'user_id': fields.many2one('res.users', 'User', required=True),
        'state': fields.selection([
                ('draft', 'Draft'),
                ('confirmed', 'Confirmed'),
                ('transferred', 'Transferred'),
                ('waiting', 'Draft Payment'),
                ('paid', 'Paid'),
                ],
                'Status', readonly=True, track_visibility='onchange'),
    }

    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'hr.employee', context=c),
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'date_to': lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
        'currency_id': _get_currency,
        'state': 'draft',
        'user_id': lambda cr, uid, id, c={}: id,
    }

    def create(self, cr, uid, vals, context=None):
        if vals.get('name','/') == '/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'declaration.report') or '/'
        return super(declaration_report, self).create(cr, uid, vals, context=context)

    def compute_lines(self, cr, uid, ids, context=None):
        """
        For each register, we need to iterate through the statement lines
        and keep only the pertinent ones.
        From there, we build a dictionary of values that we need to do the rest.
        """
        report_line_obj = self.pool.get('declaration.report.line')
        report_obj = self.pool.get('declaration.report')
        payslip_line = self.pool.get('hr.payslip.line')
        payslip_lines = []
        res = []
        total = 0.0
        # TODO: We need a dictionnary that maps the gross to the slip_id
        for declaration in self.browse(cr, uid, ids, context=context):
            cr.execute("SELECT hp.id,pl.total from hr_payslip_line AS pl "\
                        "LEFT JOIN hr_payslip AS hp on (pl.slip_id = hp.id) "\
                        "WHERE pl.code = 'GROSS'"\
                        "AND (hp.date_from >= %s) AND (hp.date_to <= %s) "\
                        "AND hp.state = 'done' "\
                        "ORDER BY pl.slip_id, pl.sequence",
                        (declaration.date_from, declaration.date_to))
            gross_map = {x[0]:x[1] for x in cr.fetchall()}
            # clean existing report_line:
            old_line_ids = report_line_obj.search(cr, uid, [('declaration_id', '=', declaration.id)], context=context)
#            old_slipline_ids
            if old_line_ids:
                report_line_obj.unlink(cr, uid, old_line_ids, context=context)
            for register in declaration.prep_id.register_ids:
                cr.execute("SELECT pl.id from hr_payslip_line as pl "\
                                "LEFT JOIN hr_payslip AS hp on (pl.slip_id = hp.id) "\
                                "WHERE (hp.date_from >= %s) AND (hp.date_to <= %s) "\
                                "AND pl.register_id = %s "\
                                "AND hp.state = 'done' "\
                                "ORDER BY pl.slip_id, pl.sequence",
                                (declaration.date_from, declaration.date_to, register.id))
                payslip_lines = [x[0] for x in cr.fetchall()]
                for line in payslip_line.browse(cr, uid, payslip_lines):
                    res.append({
                        'declaration_id': declaration.id,
                        'name': line.employee_id.name,
                        'employee_id': line.employee_id.id,
                        'rule_id': line.salary_rule_id.id,
                        'account_id': line.salary_rule_id.account_credit.id,
                        'gross': gross_map.get(line.slip_id.id, 0.0),
                        'total': line.total,
                    })
                    total += line.total
            lines = [(0,0,line) for line in res]
            self.write(cr, uid, [declaration.id], {'line_ids': lines, 'amount':total,}, context=context)
        return True

    def confirm_report(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'date_confirm': time.strftime('%Y-%m-%d')}, context=context)
        self._receipt_create(cr, uid, ids, context)
        self._voucher_create(cr, uid, ids, context)
        return self.write(cr, uid, ids, {'state': 'confirmed', 'date_confirm': time.strftime('%Y-%m-%d')}, context=context)

    def make_draft(self, cr, uid, ids, context=None):
        '''Remove any unpaid voucher and move created and reset to draft'''
        move_obj = self.pool.get('account.move')
        voucher_obj = self.pool.get('account.voucher')
        for declaration in self.browse(cr, uid, ids, context=context):
            if declaration.move_id:
                move_obj.unlink(cr, uid, [declaration.move_id.id], context=context)
            if declaration.voucher_id:
                voucher_obj.unlink(cr, uid, [declaration.voucher_id.id], context=context)
        return self.write(cr, uid, ids, {'state': 'draft', 'date_confirm': None}, context=context)

    def _get_paid_declarations(self, cr, uid, ids, context=None):
        res = { this.id : True for this in self.browse(cr, uid, ids, context=context)
                if this.voucher_id.state == 'posted' and this.move_id.state == 'posted'}
        return res.keys()

    def condition_paid(self, cr, uid, ids, context=None):
        ok = True
        for l in self.browse(cr, uid, ids, context=context):
            if l.voucher_id.state != 'posted':
                ok = False
        return ok

    def _move_get(self, cr, uid, declaration_id, context=None):
        '''
        This method prepare the creation of the account move related to the given declaration.

        :param declaration_id: Id of declaration for which we are creating account_move.
        :return: mapping between fieldname and value of account move to create
        :rtype: dict
        '''
        journal_obj = self.pool.get('account.journal')
        declaration = self.browse(cr, uid, declaration_id, context=context)
        company_id = declaration.company_id.id
        date = declaration.date_confirm
        ref = declaration.name
        journal_id = False
        if not declaration.prep_id.journal_id:
            raise osv.except_osv(_('Error!'), _("No declaration journal found."))
        journal_id = declaration.prep_id.journal_id.id
        return self.pool.get('account.move').account_move_prepare(cr, uid, journal_id, date=date, ref=ref, company_id=company_id, context=context)

    def _receipt_create(self, cr, uid, ids, context=None):
        """Create accounting entries for this declaration"""
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        return_ids = []
        for declaration in self.browse(cr, uid, ids, context=context):
            if declaration.move_id:
                continue

            #create the move that will contain the accounting entries
            move_id = move_obj.create(cr, uid, self._move_get(cr, uid, declaration.id, context=context), context=context)

            lml = []
            amount = 0.0
            # compact debit lines
            m = {}
            for line in declaration.line_ids:
                if not m.get(line.rule_id.id):
                    m[line.rule_id.id] = {
                        'name': line.rule_id.name,
                        'move_id': move_id,
                        'partner_id': declaration.prep_id.partner_id.id,
                        'account_id': line.account_id.id,
                        'date_maturity': declaration.date_confirm,
                        'debit':0.0,
                        'credit':0.0,
                        'quantity':1,
                        }
                m[line.rule_id.id]['debit'] += line.total
                amount += line.total
            # create the move lines
            first_line = {
                    'name': declaration.name,
                    'move_id': move_id,
                    'partner_id': declaration.prep_id.partner_id.id,
                    'account_id': declaration.prep_id.account_id.id,
                    'date_maturity': declaration.date_confirm,
                    'credit': amount,
                    'debit': 0.0,
                    } #credit
            first_line_id = move_line_obj.create(cr, uid, first_line)
            # now balance it
            for o in m.keys():
                move_line_obj.create(cr, uid, m[o]) # debit
            # post the journal entry if 'Skip 'Draft' State for Manual Entries' is checked
            journal_id = move_obj.browse(cr, uid, move_id, context).journal_id
            if journal_id.entry_posted:
                move_obj.button_validate(cr, uid, [move_id], context)
            return_ids.append(
                self.write(cr, uid, ids, {'move_id': move_id, 'state': 'transferred'}, context=context))
        return return_ids

    def _voucher_create(self, cr, uid, ids, context=None):
        ctx = context.copy()
        ctx.update({'account_period_prefer_normal': True})
        voucher_obj = self.pool.get('account.voucher')
        move_line_obj = self.pool.get('account.move.line')
        journal_obj = self.pool.get('account.journal')
        period_obj = self.pool.get('account.period')
        for declaration in self.browse(cr, uid, ids, context=context):
            if declaration.voucher_id:
                continue
            if not declaration.move_id:
                continue
            voucher = {
                'journal_id': declaration.bank_id.journal_id.id,
                'company_id': declaration.company_id.id,
                'partner_id': declaration.prep_id.partner_id.id,
                'type':'payment',
                'name': declaration.prep_id.name,
                'account_id': declaration.bank_id.journal_id.default_credit_account_id.id,
                'amount': declaration.amount,
                'date': declaration.date_confirm,
                'date_due': declaration.date_confirm,
                'period_id': period_obj.find(
                    cr,
                    uid,
                    inv.date_confirm,
                    context=ctx)[0],
                }
            # Define the voucher line
            lml = []
            for move_line_id in declaration.move_id.line_id:
                if move_line_id.credit > 0:
                    lml.append({
                        'name': move_line_id.name,
                        'move_line_id': move_line_id.id,
                        'reconcile': True,
                        'amount': move_line_id.credit,
                        'account_id': declaration.prep_id.account_id.id,
                        'type': move_line_id.credit and 'dr' or 'cr',
                        })
            lines = [(0,0,x) for x in lml]
            voucher['line_ids'] = lines
            voucher_id = voucher_obj.create(cr, uid, voucher, context=context)
            self.write(cr, uid, [declaration.id], {'voucher_id': voucher_id}, context=context)
            move_id = voucher_obj.browse(cr, uid, voucher_id, context=context).move_id.id
            # post the journal entry if 'Skip 'Draft' State for Manual Entries' is checked
            if declaration.bank_id.journal_id.entry_posted:
                move_obj.button_validate(cr, uid, [move_id], context)

    def action_view_voucher(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing account.move of given loan ids.
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        declaration = self.browse(cr, uid, ids[0], context=context)
        assert declaration.voucher_id
        try:
            dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
        except ValueError, e:
            view_id = False
        result = {
            'name': _('Declaration Payment'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': declaration.voucher_id.id,
        }
        return result

    def print_report(self, cr, uid, ids, context=None):
        report_map = {
            'cnss': 'declaration.cnss',
            'irpp': 'declaration.irpp',
            'aib': 'declaration.aib',
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_map.get(context.get('format')),
            'datas': {
                    'model':'declaration.report',
                    'id': ids and ids[0] or False,
                    'ids': ids and ids or [],
                    'report_type': 'pdf'
                },
            'nodestroy': True
        }

declaration_report()

class declaration_prep(osv.osv):
    _name = 'declaration.prep'
    _description = 'Benin Payroll Declaration Settings'

    _columns = {
        "name": fields.char('Name', size=256, required=True),
        'partner_id':fields.many2one('res.partner', 'Partner', required=True, help=_("Who we are paying")),
        'account_id': fields.many2one('account.account', 'Credit Account', required=True,
            domain="[('type', '=', 'payable')]", help=_("The payable account to use")),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, help = "The journal used to record declarations."),
        'format': fields.selection([
                ('cnss', 'CNSS'),
                ('irpp', 'IRPP'),
                ('aib', 'AIB'),
                ],
                'Printout Format',
                help=_('Select the format to use when printing this type of declaration'),
                required=True),
        'register_ids': fields.many2many(
            'hr.contribution.register',
            'declaration_prep_register_rel',
            'prep_id', 'register_id', string='Associated registers',
            domain="[('partner_id', '=', partner_id)]",
            help=_("The registers where concerned payslip lines are kept")),
    }
declaration_prep()

class contrib_register(osv.osv):

    _inherit = 'hr.contribution.register'

    _columns = {
        'prep_ids': fields.many2many(
            'declaration.prep',
            'declaration_prep_register_rel',
            'register_id', 'prep_id', string='Associated Declaration Settings'),
    }
contrib_register()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
