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

class res_partner(osv.osv):
	_inherit = 'res.partner'
	_columns = {
		'cim_id': fields.many2one('account.authnet.cim', 'Customer Profile', domain="[('partner_id','=',id)]", help="The Authorize.net payment profile saving all credit cards on file on Authorize.net servers."),
	}
	
	# Launches the wizard to create a customer profile for the CIM
	def create_customer_profile(self, cr, uid, ids, context=None):
		if context is None: context = {}
		
		if len(ids) != 1:
			return {}
		
		partner_rec = self.browse(cr, uid, ids, context)[0]
		if partner_rec.cim_id:
			return {}
		
		# Start the wizard by returning an action dictionary, defaulting in the partner_id
		context['default_partner_id'] = ids[0]
		addrs = self.pool['res.partner'].address_get(cr, uid, ids, ['invoice'])
		# If there's a default invoice address, or if not, default address, pass that as the invoice id
		context['default_invoice_addr_id'] = addrs.get('invoice', False) and addrs['invoice'] or \
											addrs.get('default', False) and addrs['default'] or \
											False
		return {
			'name': 'Create a Customer Profile',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'cim.create.customer.profile',
			'type': 'ir.actions.act_window',
			'target': 'new',
			'context': context,
		}
	
	
	# Launches the wizard to create a payment profile to link to this customer
	def create_payment_profile(self, cr, uid, ids, context=None):
		if context is None: context = {}
		
		if len(ids) != 1:
			return {}
		
		partner_rec = self.browse(cr, uid, ids, context)[0]
		if not partner_rec.cim_id:
			return {}
		
		# Start the wizard by returning an action dictionary, defaulting in the partner_id
		context['default_partner_id'] = ids[0]
		context['default_cim_id'] = partner_rec.cim_id.id
		ctx = dict(context)
		ctx['cc_last_four'] = True
		return {
			'name': 'Register a Payment Profile',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'cim.create.payment.profile',
			'type': 'ir.actions.act_window',
			'target': 'new',
			'context': ctx,
		}