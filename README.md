# openerp-authorize.net
Straightforward credit card processing for OpenERP via Authorize.net API, that actually works

Currently works great for OpenERP 7!

This was cloned from Brett Lehr's code here: https://code.launchpad.net/~brett-lehrer

After a long time of searching, trying various modules, and failing, this is the first and only way I have ever managed to implement credit card processing into OpenERP, so I copied it into my own repo here for safe keeping


##How to set it up
*These steps may be out of order, as I'm writing this from memory. I will update with proper instructions soon*

###Install all the modules.
Note that the RSA Encryption module requires something installed on your OS, install it either through the package manager or through pip (I can't remember what I did)

###Generate RSA Keys
**Settings > Security > Generate New Keys**
This is used to encrypt the credit card information stored on your server

###Add auth.net credentials 
**Accounting > CC API Credentials**
You should use an authorize.net sandbox account to start out with, and then switch over to the real one once you're sure everything is properly configured. 

###Set default income account for credit card transactions
I can't remember where to do this



