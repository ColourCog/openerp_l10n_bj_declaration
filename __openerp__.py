#-*- coding:utf-8 -*-
{
    'name': 'Benin - Payroll declarations',
    'category': 'Accounting',
    'author': 'ColourCog.com',
    'depends': [
        'l10n_syscohada',
        'l10n_bj_payroll',
        'account_accountant',
        'hr_payroll_account',
        'account_voucher',
    ],
    'version': '1.0',
    'description': """
Benin Payroll declarations.
===========================
This module enables a company to generate, store and print 
Benin Payroll declarations.
    """,
    'data':[
        'declaration_view.xml',
        'declaration_data.xml',
        'declaration_report.xml',
        'declaration_sequence.xml',
    ],
    "installable": True,
    "auto_install": False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
