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
	'name': 'Authorize.Net API',
	'version': '0.4',
	'depends': [
		'account_voucher',
		'account_payment_cc',
	],
	'author': 'Solaris',
	'website': 'http://solarismed.com',
	'category': 'Solaris Custom',
	'complexity': 'normal',
	'description': """
Provides Authorize.Net API access for credit card payments.  Can enter card info directly or use
information on file to avoid entering CC information.

This module uses the Python urllib3 library (see documentation: https://pypi.python.org/pypi/urllib3 for more info).
To install this in Ubuntu, use:

sudo apt-get install python-urllib3

If you're using an older version of Ubuntu that doesn't have urllib3 in the repository, you must download the source
code and install it.  Here are the steps to do that:

cd /tmp

wget https://pypi.python.org/packages/source/u/urllib3/urllib3-1.7.tar.gz

tar xf urllib-1.7.tar.gz

cd urllib-1.7

sudo python setup.py install

Restart the OpenERP server once this is done and you should be able to install this module.
	""",
	'init_xml': [],
	'update_xml': [
		'wizard/create_customer_profile_view.xml',
		'wizard/create_payment_profile_view.xml',
		'account_voucher_workflow.xml',
		'account_view.xml',
		'account_voucher_view.xml',
		'res_partner_view.xml',
		'authorizenet_api_view.xml',
		'res_user_data.xml',
		'security/ir.model.access.csv',
	],
	'data': [],
	'demo': [],
	'test': [],
	'installable': True,
	'application': False,
}