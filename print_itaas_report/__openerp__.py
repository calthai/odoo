# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Print ITAAS Report',
    'version' : '1.0',
    'price' : 'Free',
    'currency': 'THB',
    'category': 'MISC',
    'summary' : 'Print Report',
    'description': """
                Report:
                    - Creating Report
Tags:
Report
            """,
    "author": "IT as a Service Co., Ltd.",
    'website' : 'www.itaas.co.th',
    'depends' : ['product','stock','capelda_extended'],
    'data' : ['report/report_picking_operation.xml',
              'report/report_deliveryslip_slip.xml',

              ],

    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
