odoo.define('bi_pos_currency_rate.button', function (require) {
'use strict';


    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var gui = require('point_of_sale.gui');
    var popups = require('point_of_sale.popups');
    var QWeb = core.qweb;
    var rpc = require('web.rpc');

    var utils = require('web.utils');
    var round_pr = utils.round_precision;

    var _t = core._t;

    var currencystart = screens.PaymentScreenWidget.include({

        renderElement: function() {
            var self = this;
            this._super();
            this.$('#details').hide()
            this.$('#cur').change(function(){
            if($("#cur").prop('checked') == true)
            {
                $('#details').show()
            }
            else
            {
                $('#details').hide()
            }
        });
    },

});

});
   
