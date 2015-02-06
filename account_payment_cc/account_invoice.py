# -*- coding: utf-8 -*-
##############################################################################
#
#	OpenERP, Open Source Management Solution
#	Copyright (C) 2013 Solaris, Inc. (<http://www.solarismed.com>)
#	Copyright (C) 2004-2013 OpenERP SA (<http://www.openerp.com>)
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import osv, fields

class account_invoice(osv.osv):
	_inherit = 'account.invoice'
	_columns = {
		'is_cc_payment': fields.boolean('Use CC Payment'),
	}
	
	
	# Set CC payment flag when a credit card payment term is selected
	def onchange_payment_term_cc(self, cr, uid, ids, payment_term_id):
		# Assume False for CC payments, only set to True if
		# there is a payment term AND the term is a CC term
		res = {'is_cc_payment': False}
		
		if payment_term_id:
			term_rec = self.pool['account.payment.term'].browse(cr, uid, payment_term_id)
			if term_rec.is_cc_term:
				res['is_cc_payment'] = True
		
		return {'value': res}
	
	
	# Opens Pay invoice window - prefill with some CC data and pick a different view
	def invoice_pay_customer(self, cr, uid, ids, context=None):
		if not ids: return []
		context = context or {}
		
		res = super(account_invoice, self).invoice_pay_customer(cr, uid, ids, context)
		inv = self.browse(cr, uid, ids[0], context=context)
		
		# If it's a credit card payment, default the CC payment method and load a new view
		if inv.is_cc_payment:
			# Find all the CC payment journals and pick the first by default
			cc_journal_id = self.pool['account.journal'].search(cr, uid, [('cc_processing','=',True)])
			# Error checking, bail out if we never set a CC journal
			if not cc_journal_id:
				raise osv.except_osv("Error", "There are no credit card processing journals!  Enable CC Processing on a journal before attempting to accept a payment on an invoice with a credit card payment term.")
			res['context']['default_journal_id'] = cc_journal_id[0]
			res['name'] = 'Pay Invoice by Credit Card'
		
		# Otherwise, just get the first cash/bank journal we can
		else:
			journal_ids = self.pool['account.journal'].search(cr, uid, [('type','in',['cash','bank'])])
			if journal_ids:
				res['context']['default_journal_id'] = journal_ids[0]
		
		# Check for a default invoice address. If there's a default invoice
		# address, pass the id to the next screen even if it's not for CC payments.
		# TODO: This should be moved outside of the scope of this module!
		addresses = self.pool['res.partner'].address_get(cr, uid, [inv.partner_id.id], ['invoice'])
		if addresses.get('invoice', False):
			res['context']['default_invoice_addr_id'] = addresses['invoice']
		return res