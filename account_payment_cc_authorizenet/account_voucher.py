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
from lxml import etree
import string
from openerp import netsvc

class account_voucher(osv.osv):
	_inherit = 'account.voucher'
	_columns = {
		'transId': fields.char('Transaction ID', size=128, readonly=True, help="The transaction ID returned by Authorize.net.  Used for voiding a transaction."),
		'error_text': fields.char('Authorization Status', size=128, readonly=True, help="The transaction error details reported by Authorize.net. Left blank if the transaction was successful."),
		'is_approved': fields.boolean('Approved', readonly=True),
		'state': fields.selection(
			[('draft','Draft'),
			('dispute','Error'),
			('cancel','Cancelled'),
			('proforma','Pro-forma'),
			('posted','Posted'),
			], 'Status', readonly=True, size=32, track_visibility='onchange',),
		'cim_id': fields.many2one('account.authnet.cim', 'Customer Profile', domain="[('partner_id','=',partner_id)]"),
		'cim_payment_id': fields.many2one('account.authnet.cim.payprofile', 'Card on File', domain="[('cim_id','=',cim_id)]"),
		'card_type': fields.char('Card Type', size=16, help="The type of card used to pay.  Visa, MasterCard, American Express, etc."),
	}
	
	
	# Set the CC flag to hide/unhide stuff
	def onchange_journal(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
		if not journal_id:
			return False
		res = super(account_voucher, self).onchange_journal(cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context)
		
		# Make sure we only show CIM options if we're really paying with a CC
		if res['value'].get('use_cc', False) and partner_id:
			partner_rec = self.pool['res.partner'].browse(cr, uid, partner_id, context)
			if partner_rec.cim_id:
				res['value']['cim_id'] = partner_rec.cim_id.id
				# Grab the default payment profile
				if partner_rec.cim_id.default_payprofile_id:
					res['value']['cim_payment_id'] = partner_rec.cim_id.default_payprofile_id.id
				# If no default, grab the first profile we find
				elif partner_rec.cim_id.payprofile_ids:
					res['value']['cim_payment_id'] = partner_rec.cim_id.payprofile_ids[0].id
		
		# If it's not using CC payments, erase any previously filled CIM data
		elif not res['value'].get('use_cc', True):
			res['value']['cim_id'] = False
			res['value']['cim_payment_id'] = False
		return res
	
	
	# Prepare an XML request to send validating the transaction
	def _prepare_transaction_request(self, cr, uid, ids, voucher_rec, context=None):
		ctx = dict(context)
		ctx['unmask'] = True
		ref_orders = ''
		ref_credit_memos = ''
		cust_info = {}
		cc_read_fields = ['cc_number', 'cc_cvv', 'cc_exp_month', 'cc_exp_year']
		
		for cr_line in voucher_rec.line_cr_ids:
			if ref_orders:
				ref_orders += ',' + cr_line.move_line_id.move_id.ref
			else:
				ref_orders = cr_line.move_line_id.move_id.ref
		
		for dr_line in voucher_rec.line_dr_ids:
			if ref_credit_memos:
				ref_credit_memos += ',' + dr_line.move_line_id.move_id.ref
			else:
				ref_credit_memos = dr_line.move_line_id.move_id.ref
		
		
		# ------------------------
		# Begin the XML generation
		# ------------------------
		# Format will vary based on if it's a card on file or one-time use local card
		
		# Card on file
		if voucher_rec.cim_payment_id:
			refId = voucher_rec.id
			root = self.pool['account.authnet']._get_xml_header(cr, uid, 'createCustomerProfileTransactionRequest', refId, context)
			
			# Transaction type and amount
			transaction = etree.SubElement(root, 'transaction')
			auth_capture = etree.SubElement(transaction, 'profileTransAuthCapture')
			etree.SubElement(auth_capture, 'amount').text = str(voucher_rec.amount)
			etree.SubElement(auth_capture, 'customerProfileId').text = voucher_rec.cim_id.profile_id
			etree.SubElement(auth_capture, 'customerPaymentProfileId').text = voucher_rec.cim_payment_id.payprofile_id
			
		# One-time use card
		else:
			# Need to gather additional data about the payment first
			# If the invoice address isn't filled in or is missing data, get the company instead
			cust_info['id'] = voucher_rec.invoice_addr_id.id or voucher_rec.partner_id.id
			cust_info['email'] = voucher_rec.invoice_addr_id.email or voucher_rec.partner_id.email or ''
			
			namepart = voucher_rec.invoice_addr_id.name.rpartition(' ')
			cust_info['firstName'] = namepart[0]
			cust_info['lastName'] = namepart[2]
			cust_info['company'] = voucher_rec.partner_id.name
			cust_info['address'] = voucher_rec.invoice_addr_id.street or voucher_rec.partner_id.street or ''
			cust_info['city'] = voucher_rec.invoice_addr_id.city or voucher_rec.partner_id.city or ''
			cust_info['state'] = voucher_rec.invoice_addr_id.state_id.code or voucher_rec.partner_id.state_id.code or ''
			cust_info['zip'] = voucher_rec.invoice_addr_id.zip or voucher_rec.partner_id.zip or ''
			cust_info['country'] = voucher_rec.invoice_addr_id.country_id.name or voucher_rec.partner_id.country_id.name or ''
			
			full_str = string.maketrans('','')
			nodigs = full_str.translate(full_str, string.digits)
			phone_num = voucher_rec.invoice_addr_id.phone or voucher_rec.partner_id.phone or ''
			if phone_num:
				cust_info['phoneNumber'] = str(phone_num).translate(full_str, nodigs)
			fax_num = voucher_rec.invoice_addr_id.fax or voucher_rec.partner_id.fax or ''
			if fax_num:
				cust_info['faxNumber'] = str(fax_num).translate(full_str, nodigs)
			
			
			# Start generating the XML
			refId = voucher_rec.id
			root = self.pool['account.authnet']._get_xml_header(cr, uid, 'createTransactionRequest', refId, context)
			
			# Transaction type and amount
			transaction_req = etree.SubElement(root, 'transactionRequest')
			etree.SubElement(transaction_req, 'transactionType').text = 'authCaptureTransaction'
			etree.SubElement(transaction_req, 'amount').text = str(voucher_rec.amount)
			
			# Payment info
			# Prep info dictionary for the XML tree
			cc_info = self.read(cr, uid, [voucher_rec.id], cc_read_fields, ctx)[0]
			
			pay_type = etree.SubElement(transaction_req, 'payment')
			cc = etree.SubElement(pay_type, 'creditCard')
			etree.SubElement(cc, 'cardNumber').text = cc_info['cc_number']
			etree.SubElement(cc, 'expirationDate').text = cc_info['cc_exp_month'] + '/' + cc_info['cc_exp_year']
			if cc_info['cc_cvv']:
				etree.SubElement(cc, 'cardCode').text = cc_info['cc_cvv']
			del cc_info
			
			# Reference info
			order_ref = etree.SubElement(transaction_req, 'order')
			etree.SubElement(order_ref, 'invoiceNumber').text = ref_orders
			if ref_credit_memos:
				etree.SubElement(order_ref, 'description').text = 'Credit memo(s) applied from: ' + ref_credit_memos
			
			# Customer record, using partner ID as custom id (contact/partner IDs don't overlap anymore in 7.0!)
			cust = etree.SubElement(transaction_req, 'customer')
			etree.SubElement(cust, 'id').text = str(cust_info['id'])
			if cust_info['email']: etree.SubElement(cust, 'email').text = cust_info['email']
			
			# Bill To info
			billto = etree.SubElement(transaction_req, 'billTo')
			etree.SubElement(billto, 'firstName').text = cust_info['firstName']
			if cust_info['lastName']: etree.SubElement(billto, 'lastName').text = cust_info['lastName']
			etree.SubElement(billto, 'company').text = cust_info['company']
			if cust_info['address']: etree.SubElement(billto, 'address').text = cust_info['address']
			if cust_info['city']: etree.SubElement(billto, 'city').text = cust_info['city']
			if cust_info['state']: etree.SubElement(billto, 'state').text = cust_info['state']
			etree.SubElement(billto, 'zip').text = cust_info['zip']
			if cust_info['country']: etree.SubElement(billto, 'country').text = cust_info['country']
			if cust_info.get('phoneNumber', False): etree.SubElement(billto, 'phoneNumber').text = cust_info['phoneNumber']
			if cust_info.get('faxNumber', False): etree.SubElement(billto, 'faxNumber').text = cust_info['faxNumber']
			
			# Define as ecommerce transaction (card not present)
			retail = etree.SubElement(transaction_req, 'retail')
			etree.SubElement(retail, 'marketType').text = '0'
		
#		print etree.tostring(root, pretty_print=True)
		return root
	
	
	# Override the original proforma_voucher method and insert Authorize.net validation code
	def proforma_voucher(self, cr, uid, ids, context=None):
		if context is None: context = {}
		voucher_recs = self.browse(cr, uid, ids)
		valid_ids = []
		wf_service = netsvc.LocalService("workflow")
		
		for voucher_rec in voucher_recs:
			# Make sure there's an amount, $0 payments are worthless!
			if not voucher_rec.amount:
				raise osv.except_osv("Error", "Paid Amount is $0, please enter a payment amount.")
			
			# If this is a CC payment, authenticate with Authorize.net
			if voucher_rec.use_cc:
				
				# Prepare the XML request
				req_xml_obj = self._prepare_transaction_request(cr, uid, ids, voucher_rec, context)
				
				# Send the XML object to Authorize.net and return an XML object of the response
				authnet_obj = self.pool['account.authnet']
				res = authnet_obj._send_request(cr, uid, req_xml_obj, context)
				
				# Parsing will vary depending on if it's a card on file or one-time card
				last_four = False
				if voucher_rec.cim_payment_id:
					res_dict = authnet_obj._parse_payment_gateway_response(cr, uid, res, 'directResponse', context=context)
					approval_code = res_dict['Response Code']
					transId = res_dict['Transaction ID']
					errordesc = res_dict['Response Reason Text']
					card_type = res_dict['Card Type']
					last_four = voucher_rec.cim_payment_id.last_four
				else:
					# Get the transaction approval code
					approval_code = res.xpath('//responseCode')[0].text
					
					transId_loc = res.xpath('//transId')
					transId = transId_loc and transId_loc[0].text or False
					error_loc = res.xpath('//errorText')
					errordesc = error_loc and error_loc[0].text or False
					card_type_loc = res.xpath('//accountType')
					card_type = card_type_loc and card_type_loc[0].text or False
					
				
				if approval_code == '1':
					vals = {
						'is_approved': True,
						'error_text': False,
						'transId': transId,
						'card_type': card_type,
						'last_four': last_four,
					}
					self.write(cr, uid, [voucher_rec.id], vals, context)
					
					# The transaction is approved, schedule the move lines to be created
					valid_ids.append(voucher_rec.id)
				else:
					vals = {
						'is_approved': False,
						'error_text': errordesc,
						'state': 'dispute',
					}
					self.write(cr, uid, [voucher_rec.id], vals, context)
					wf_service.trg_validate(uid, 'account.voucher', voucher_rec.id, 'cc_dispute', cr)
			
			else:
				# If it's not a CC transaction, always add the ID to the valid id list
				valid_ids.append(voucher_rec.id)
		
		# Process the valid id list
		self.action_move_line_create(cr, uid, valid_ids, context=context)
		
		# Trigger workflows on all valid transactions
		for vid in valid_ids:
			wf_service.trg_validate(uid, 'account.voucher', vid, 'proforma_voucher', cr)
		
		return True
	
	
	# Override payment function for direct payment from the invoice popup window
	def button_proforma_voucher(self, cr, uid, ids, context=None):
		context = context or {}
		# Just call the default proforma_voucher function above, will handle non-CC payments too
		self.proforma_voucher(cr, uid, ids, context)
		return {'type': 'ir.actions.act_window_close'}
	
	
	def _prepare_void_request(self, cr, uid, ids, voucher_rec, context=None):
		# Start root tag and add credentials
		refId = voucher_rec.id
		root = self.pool['account.authnet']._get_xml_header(cr, uid, 'createTransactionRequest', refId, context)
		
		# Void request, adding transaction ID to void
		transaction_req = etree.SubElement(root, 'transactionRequest')
		etree.SubElement(transaction_req, 'transactionType').text = 'voidTransaction'
		etree.SubElement(transaction_req, 'refTransId').text = voucher_rec.transId
		
		print etree.tostring(root, pretty_print=True)
		return root
		
	
	# Void a transaction
	# TODO: Ask about CC settlement process
	def void_voucher(self, cr, uid, ids, context=None):
		if not isinstance(ids, list):
			ids = [ids]
		vouchers = self.browse(cr, uid, ids, context)
		wf_service = netsvc.LocalService("workflow")
		
		for voucher_rec in vouchers:
			if voucher_rec.state == 'posted' and voucher_rec.is_approved:
				req_xml_obj = self._prepare_void_request(cr, uid, ids, voucher_rec, context)
				
				# Send the XML object to Authorize.net and return the XML string
				res = self.pool['account.authnet']._send_request(cr, uid, req_xml_obj, context)
				
				# Get the transaction approval code
				approval_code = res.xpath('//responseCode')[0].text
				
				if approval_code == '1':
					vals = {
						'is_approved': False,
						'error_text': False,
						'transId': False,
					}
					self.write(cr, uid, [voucher_rec.id], vals, context)
					
					# Workflow trigger will set the state to "cancelled" and handle the account moves
					wf_service.trg_validate(uid, 'account.voucher', voucher_rec.id, 'cancel_voucher', cr)
				
				# If the transaction is already voided on authorize.net but not the ERP,
				# walk through the same steps
				elif res.xpath('//transactionResponse/messages/message/code')[0].text == '310':
					vals = {
						'is_approved': False,
						'error_text': False,
						'transId': False,
					}
					self.write(cr, uid, [voucher_rec.id], vals, context)
					
					# Workflow trigger will set the state to "cancelled" and handle the account moves
					wf_service.trg_validate(uid, 'account.voucher', voucher_rec.id, 'cancel_voucher', cr)
				
				
				
				# TODO: If the transaction is already settled, generate a refund here
				
				
				
				# If something else went wrong, update the error text and do nothing else
				else:
					errordesc = res.xpath('//errorText')
					
					# Auth.net may have sent an error message or a regular message
					if errordesc:
						errordesc = errordesc[0].text
					else:
						errordesc = res.xpath('//transactionResponse/messages/message/description')[0].text
					vals = {
						'error_text': errordesc,
					}
					self.write(cr, uid, [voucher_rec.id], vals, context)
					
		return False