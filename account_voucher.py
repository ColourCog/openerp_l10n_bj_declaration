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

from openerp.osv import osv,fields
from openerp.tools.translate import _
from lxml import etree

## Overloading amount_to_text here because CFA has no cents,

to_19_fr = ( u'zéro',  'un',   'deux',  'trois', 'quatre',   'cinq',   'six',
          'sept', 'huit', 'neuf', 'dix',   'onze', 'douze', 'treize',
          'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf' )
tens_fr  = ( 'vingt', 'trente', 'quarante', 'Cinquante', 'Soixante', 'Soixante-dix', 'Quatre-vingt', 'Quatre-vingt Dix')
denom_fr = ( '',
          'Mille',     'Millions',         'Milliards',       'Billions',       'Quadrillions',
          'Quintillion',  'Sextillion',      'Septillion',    'Octillion',      'Nonillion',
          'Décillion',    'Undecillion',     'Duodecillion',  'Tredecillion',   'Quattuordecillion',
          'Sexdecillion', 'Septendecillion', 'Octodecillion', 'Icosillion', 'Vigintillion' )

def _convert_nn_fr(val):
    """ convert a value < 100 to French
    """
    if val < 20:
        return to_19_fr[val]
    for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens_fr)):
        if dval + 10 > val:
            if dcap in ['Soixante-dix', 'Quatre-vingt Dix']:
                if val % 10:
                    return tens_fr[tens_fr.index(dcap)-1] + ' ' + to_19_fr[10 + val % 10]
            if val % 10:
                return dcap + '-' + to_19_fr[val % 10]
            return dcap

def _convert_nnn_fr(val):
    """ convert a value < 1000 to french
    
        special cased because it is the level that kicks 
        off the < 100 special case.  The rest are more general.  This also allows you to
        get strings in the form of 'forty-five hundred' if called directly.
    """
    word = ''
    (mod, rem) = (val % 100, val // 100)
    if rem > 0:
        # we don't say 'un Cent'
        m = {'un':''}
        word = m.get(to_19_fr[rem], to_19_fr[rem]) + ' Cent'
        if mod > 0:
            word += ' '
    if mod > 0:
        word += _convert_nn_fr(mod)
    return word

def french_number(val):
    if val < 100:
        return _convert_nn_fr(val)
    if val < 1000:
         return _convert_nnn_fr(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom_fr))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            ret = _convert_nnn_fr(l) + ' ' + denom_fr[didx]
            if r > 0:
                ret = ret + ', ' + french_number(r)
            return ret

def amount_to_text_fr(number, currency):
    number = '%.2f' % number
    units_name = currency
    list = str(number).split('.')
    start_word = french_number(abs(int(list[0])))
    end_word = french_number(int(list[1]))
    cents_number = int(list[1])
    cents_name = (cents_number > 1) and ' Cents' or ' Cent'
    final_result = start_word +' '+units_name
    return final_result


class account_voucher(osv.osv):
    _inherit='account.voucher'
    _name='account.voucher'

    def _amount_to_text(self, cr, uid, amount, currency_id, context=None):
        currency = self.pool['res.currency'].browse(cr, uid, currency_id, context=context)
        if currency.name.upper() == 'EUR':
            currency_name = 'Euro'
        elif currency.name.upper() == 'USD':
            currency_name = 'Dollars'
        elif currency.name.upper() == 'BRL':
            currency_name = 'reais'
        elif currency.name.upper() == 'XOF':
            currency_name = 'Francs CFA'
        else:
            currency_name = currency.name
        #TODO : generic amount_to_text is not ready yet, otherwise language (and country) and currency can be passed
        #amount_in_word = amount_to_text(amount, context=context)
        return amount_to_text_fr(amount, currency=currency_name)

    def write(self, cr, uid, ids, vals, context=None):
        voucher_obj = self.pool.get('account.voucher')
        voucher = voucher_obj.browse(cr, uid, ids, context=context)[0]
        vals["amount_in_word"] = self._amount_to_text(cr, uid, voucher.amount, voucher.company_id.currency_id.id, context=context)
        voucher_id = super(account_voucher, self).write(cr, uid, ids, vals, context=context)
        return voucher_id

account_voucher()
