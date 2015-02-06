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

from Crypto.PublicKey import RSA
from openerp.osv import osv, fields

class key_generator(osv.TransientModel):
	_name = 'key.generator'
	_columns = {
		'server_path': fields.char('Key Folder Path', size=256, required=True, help="Typically this would be your root server path, but any folder that allows write access to the system user running OpenERP will work. Example:\n\n/opt/openerp/server"),
		'filename_priv': fields.char('Private Key Name', size=64, required=True),
		'filename_pub': fields.char('Public Key Name', size=64, required=True),
		'key_size': fields.selection([('1024','1024'),
									('2048','2048'),
									('4096','4096'),
									('8192','8192')], 'Key Length in bits', required=True),
	}
	
	def _get_current_path(self, cr, uid, context=None):
		if context is None: context = {}
		import os
		return os.getcwd()
	
	_defaults = {
		'server_path': _get_current_path,
		'key_size': '2048',
	}
	
	# Set the public key to <filename_priv>.pub
	def onchange_private(self, cr, uid, ids, filename_priv, context=None):
		if context is None: context = {}
		res = {}
		
		if not filename_priv:
			res['filename_pub'] = ''
		else:
			res['filename_pub'] = filename_priv + '.pub'
		
		return {'value': res}
	
	#Generate the private/public keys with the given filenames and using the defined
	# key size (default 2048)
	def generate_keys(self, cr, uid, ids, context=None):
		if context is None: context = {}
		if not ids: return {}
		if not isinstance(ids, list): ids = [ids]
		
		wizard_rec = self.browse(cr, uid, ids, context)[0]
		# Make sure the filenames aren't blank or bad
		if wizard_rec.filename_priv == wizard_rec.filename_pub:
			raise osv.except_osv("Error", "The public and private key filenames are identical, please choose different names.")
		
		import os
		# Parse server path and generate full file names
		# If the path doesn't end with a slash, add it
		if not os.path.exists(wizard_rec.server_path):
			raise osv.except_osv("Error", "The path entered does not exist.  Please check the exact spelling and try again.")
		
		file_priv = os.path.join(wizard_rec.server_path, wizard_rec.filename_priv)
		file_pub = os.path.join(wizard_rec.server_path, wizard_rec.filename_pub)
		
		pkey = RSA.generate(int(wizard_rec.key_size))
		pubkey = pkey.publickey()
		
		# Raise OSV exceptions if the files exist - we shouldn't be overwriting an existing RSA key or
		# the data already encrypted using it will be forever lost!
		if os.path.isfile(file_priv):
			raise osv.except_osv('Error', 'The private key already exists.  Please choose a different filename.')
		if os.path.isfile(file_pub):
			raise osv.except_osv('Error', 'The public key already exists.  Please choose a different filename.')
		
		
		try:
			# Create the file, export the key, and set the permissions to Read/Write for the owner ONLY
			f = open(file_priv,'w')
			f.write(pkey.exportKey())
			f.close()
			os.chmod(file_priv, 0600)
			
			# Repeat for public key, though this could arguably be 0644 instead.
			fpub = open(file_pub,'w')
			fpub.write(pubkey.exportKey())
			fpub.close()
			os.chmod(file_pub, 0600)
		except IOError:
			raise osv.except_osv("Error", "IOError raised while writing keys.  Check that the system user running the OpenERP server has write permission on the folder\n\n%s" % wizard_rec.server_path)
		
		rsa_obj = self.pool['rsa.encryption']
		
		# Find any existing active key sets, if none exist, make it the primary set
		make_primary = True
		found_keys = rsa_obj.search(cr, uid, [('primary','=',True)])
		if found_keys:
			make_primary = False
		vals = {
			'name': file_priv,
			'pub_name': file_pub,
			'active': True,
			'primary': make_primary,
		}
		rsa_obj.create(cr, uid, vals, context)
		
		return {
			'name': 'RSA Keys',
			'type': 'ir.actions.act_window',
			'res_model': 'rsa.encryption',
			'view_type': 'form',
			'view_mode': 'tree,form',
		}