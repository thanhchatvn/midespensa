odoo.define('l10n_ve_fiscal_printer.models', function (require) {
"use strict";

var models = require('point_of_sale.models');
var core = require('web.core');
var screens = require('point_of_sale.screens');
var gui = require('point_of_sale.gui');

var _t = core._t;

models.load_fields('res.partner',['cedula','rif']);
models.load_fields('account.tax',['aliquot_type']);
models.load_fields('pos.payment.method',['hka_printer_id']);

var _super = models.Order;
models.Order = models.Order.extend({
    export_for_printing: function(){
        var json = _super.prototype.export_for_printing.apply(this,arguments);
        var client  = this.get('client');

        this.orderlines.each(function(line){
            for(var orderline in json.orderlines){
                if(json.orderlines[orderline].product_name == line.product.display_name){
                    json.orderlines[orderline].barcode = line.product.barcode
                    json.orderlines[orderline].default_code = line.product.default_code
                    json.orderlines[orderline].taxes = line.get_taxes()
                }
            }
            for(var orderline in json.orderlines){
                if(json.orderlines[orderline].product_name == line.product.display_name){
                    json.orderlines[orderline].barcode = line.product.barcode
                    json.orderlines[orderline].default_code = line.product.default_code
                    json.orderlines[orderline].taxes = line.get_taxes()
                }
            }
        });

        if (this.get_client()) {
            json.customerve = {
                client:     client ? client.name : null ,
                vat:        client ? client.vat : null ,
                dni:        client ? client.cedula : null ,
                rif:        client ? client.rif : null ,
                street:     client ? client.street : null ,
                city:       client ? client.city : null ,
                state_id:       client ? client.state_id : null ,
                country_id:     client ? client.country_id : null ,
                phone:      client ? client.phone : null ,
                email:      client ? client.email : null ,
            };
        }
        return json;
    },

});

var _superPaymentline = models.Paymentline.prototype;
models.Paymentline = models.Paymentline.extend({
    export_for_printing: function(){
        var json = _superPaymentline.export_for_printing.apply(this,arguments);
        json.hka_printer_id = this.payment_method.hka_printer_id
        return json;
    },
});

/*Validate Required Client*/
screens.PaymentScreenWidget.include({
    validate_order: function(options) {
        var client = this.pos.get_order().get_client()

        if (!client){
            this.gui.show_popup('error',{
                'title': _t('No se puede confirmar un pedido'),
                'body':  _t('Seleccione un cliente para este pedido.'),
                cancel: function () {
                    this.gui.show_screen('clientlist');
                },
            });
            return;
        } else if (!client.vat){
            this.gui.show_popup('error',{
                'title': _t('No se puede confirmar el pedido'),
                'body':  _t('Por favor Agregue el RIF al cliente.'),
                cancel: function () {
                    this.gui.show_screen('clientlist');
                },
            });

            return;
        }
        return this._super(options);
    }
});


});