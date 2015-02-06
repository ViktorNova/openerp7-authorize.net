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
import inspect
import re
ENCRYPTED_FIELDS = ['cc_number', 'cc_cvv', 'cc_exp_month', 'cc_exp_year']

class account_voucher(osv.osv):
	_inherit = 'account.voucher'
	_columns = {
		'use_cc': fields.boolean('Use CC'),
#		'use_cc_on_file': fields.boolean('Use Card on File'),
#		'card_id': fields.many2one('res.partner.bank', 'Card on File'),
		'invoice_addr_id': fields.many2one('res.partner', 'Invoice Address', domain="['|',('partner_id','=',parent_id),('partner_id','=',id)]"),
		'last_four': fields.char('Paid with card ending', size=4, readonly=True),
		'cc_number': fields.char('CC Number', size=512),
		'cc_cvv': fields.char('CVV', size=512),
		'cc_exp_month': fields.char('Expiration Month', size=512),
		'cc_exp_year': fields.char('Expiration Year', size=512),
	}
	
	
	# Set the CC flag to hide/unhide stuff
	def onchange_journal(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
		if not journal_id:
			return False
		res = super(account_voucher, self).onchange_journal(cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context)
		journal_rec = self.pool['account.journal'].browse(cr, uid, journal_id)
		if journal_rec.cc_processing:
			res['value']['use_cc'] = True
#			card_ids = self.pool['res.partner.bank'].search(cr, uid, [('partner_id','=',partner_id),('state','=','cc')])
#			if card_ids:
#				res['value']['use_cc_on_file'] = True
#				res['value']['card_id'] = card_ids[0]
				
		else:
			res['value']['use_cc'] = False
#			res['value']['use_cc_on_file'] = False
#			res['value']['card_id'] = False
		
		# Make sure we get the journal's default debit account
		account_id = journal_rec.default_debit_account_id.id or journal_rec.default_credit_account_id.id
		if account_id:
			res['value']['account_id'] = account_id
		return res
	
	
	# Check their default payment term and load up CC payment method if applicable
	def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
		if not journal_id:
			return {}
		
		# MEDIOCRE OPTIMIZATION TRICK - could be done better than this
		# Inspect the call stack. If onchange_journal called this function, that means we likely
		# have the partner and changing it again is useless, so just skip it.
		if inspect.stack()[1][3] == 'onchange_journal':
			return {}
		if not partner_id:
			return {'value': {
						'line_dr_ids': [],
						'line_cr_ids': [],
						'amount': 0.0,
					}}
		if context is None:
			context = {}
		res = super(account_voucher, self).onchange_partner_id(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context)
		
		# Check the partner's default payment term, load the first CC journal if that's found
		partner_rec = self.pool['res.partner'].browse(cr, uid, partner_id)
		if partner_rec.property_payment_term and partner_rec.property_payment_term.is_cc_term:
			cc_journal_id = self.pool['account.journal'].search(cr, uid, [('cc_processing','=',True)])[0]
			res['value']['journal_id'] = cc_journal_id
		
		# Check for a default invoice address
		addrs = self.pool['res.partner'].address_get(cr, uid, [partner_rec.id], ['invoice'])
		
		# If there's a default invoice address, or if not, default address, pass that as the invoice id
		res['value']['invoice_addr_id'] = addrs.get('invoice', False) and addrs['invoice'] or \
											addrs.get('default', False) and addrs['default'] or \
											False
		return res
	
	
	# Inherit the line writing function and expand it to clear CC data after completion.
	# The proforma_voucher function that calls it will be the insertion point for CC validation code
	def action_move_line_create(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		super(account_voucher, self).action_move_line_create(cr, uid, ids, context)
		
		# If the record had one-time-use CC data, we can clear it now.  It should have
		# already validated/failed from the proforma_voucher function, so we don't have
		# to worry about deleting CC data prematurely.
		voucher_recs = self.browse(cr, uid, ids, context)
		for voucher in voucher_recs:
			# Used a CC and there is a cc_number (wasn't in some way on file)
			if voucher.use_cc and voucher.cc_number:
				vals = {
					'last_four': voucher.cc_number[-4:],
					'cc_number': False,
					'cc_cvv': False,
					'cc_exp_month': False,
					'cc_exp_year': False,
				}
				self.write(cr, uid, [voucher.id], vals, context)
		return True
	
	
	# Encrypt data for temporary storage (before validating)
	def create(self, cr, uid, values, context=None):
		if context is None: context = {}
		
		# Only do cleaning if it's a CC processing journal, otherwise strip any leftover data
		journal_rec = self.pool['account.journal'].browse(cr, uid, values['journal_id'])
		if journal_rec.cc_processing:
			# Strip out any non-digit characters first
			for field in ENCRYPTED_FIELDS:
				if not values[field]:
					del values[field]
				else:
					values[field] = re.sub(r'\D', '', values[field])
			values = self.pool['rsa.encryption'].rsa_create(cr, uid, values, ENCRYPTED_FIELDS, context)
		else:
			for field in ENCRYPTED_FIELDS:
				if field in values: del values[field]
		return super(account_voucher, self).create(cr, uid, values, context)
	
	
	# Don't write masked values to the database
	def write(self, cr, uid, ids, values, context=None):
		if context is None: context = {}
		if not isinstance(ids, list): ids = [ids]
		values = self.pool['rsa.encryption'].rsa_write(cr, uid, values, ENCRYPTED_FIELDS, context)
		return super(account_voucher, self).write(cr, uid, ids, values, context)

	
	# Mask data when reading
	# Use context['unmask'] = True before making read() call to return fully unmasked values
	# OR, use context['cc_last_four'] = True to return the unmasked last 4 digits of the CC number
	def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
		if context is None: context = {}
		values = super(account_voucher, self).read(cr, uid, ids, fields, context, load)
		
		ctx = {}
		ctx.update(context)
		ctx['cc_last_four'] = True
		return self.pool['rsa.encryption'].rsa_read(cr, uid, values, ENCRYPTED_FIELDS, ctx)
	
	# Delete any potential CC data when copying
	def copy(self, cr, uid, id, defaults, context=None):
		if context is None: context = {}
		defaults = self.pool['rsa.encryption'].rsa_copy(cr, uid, defaults, ENCRYPTED_FIELDS, context)
		return super(account_voucher, self).copy(cr, uid, id, defaults, context)