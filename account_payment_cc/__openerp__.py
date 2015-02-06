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

{
	'name': 'Credit Card Payments',
	'version': '0.2',
	'depends': [
		'sale',
		'account',
		'account_voucher',
		'rsa_encryption',
	],
	'author': 'Solaris',
	'website': 'http://solarismed.com',
	'category': 'Solaris Custom',
	'complexity': 'normal',
	'description': """The foundation for CC API usage.  *DOES NOT PROCESS CREDIT CARDS BY ITSELF!*  That must be supplemented with an additional module adding connectivity to the desired payment processor.

Uses PKCS#1 v1.5 recommendations for storing data securely.  Follows PCI recommendations of encrypting the card number, cvv, expiration month, and expiration year.  Can save cards to contacts within a company or use a card one time on a voucher.  Card data is scrubbed after validating the voucher for security reasons.

Currently the module requires private and public certificates (PEM or DER) in the server folder named 'cc_priv' and 'cc_pub' respectively.  Advise you use chmod 600 on your private certificate for security.""",
	'init_xml': [
		'account_data.xml',
	],
	'update_xml': [
		'account_view.xml',
		'account_invoice_view.xml',
		'account_journal_view.xml',
		'account_voucher_view.xml',
		'sale_order_view.xml'
#		'res_partner_bank_view.xml',
	],
	'data': [],
	'demo': [],
	'test': [],
	'installable': True,
	'application': False,
}