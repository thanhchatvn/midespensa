odoo.define('l10n_ve_fiscal_printer.fiscal_report', function (require) {
"use strict";

var models = require('point_of_sale.models');
var PosScreenWidget = require('point_of_sale.screens');
var rpc = require('web.rpc');
var gui = require('point_of_sale.gui');


var core = require('web.core');
var _t = core._t;

var printerDocNumber = 'kkkk';
PosScreenWidget.ReceiptScreenWidget.include({
    template: 'ReceiptScreenWidgetNew',
    renderElement: function() {
        var self = this;
        this._super();
        var order = self.pos.get_order();

        this.$('.button.print_fiscal').click(function(){
            if (!self._locked) {
                self.print_fiscal();
            }
        });
        this.$('.button.re-print-fiscal').click(function(){
            if (!self._locked) {
                self.re_print_document();
            }
        });
    },
    re_print_document: function() {
    },

    print_fiscal: function() {
        var self = this;
        var order = this.pos.get_order();
        var data = this.get_receipt_render_env()
        data.orderlines.order = null


        var params = {
            data: data.receipt
        }
        var jsonParams = JSON.stringify(params)

        console.log('order.return_ref')
        console.log(order.return_ref)
        console.log('order.return_ref')
        if (!order.return_ref){
            if (!('customerve' in params['data'])){
                self.gui.show_popup('confirm',{
                    'title': _t('Please select the Customer'),
                    'body': _t('You need to select the customer before you can invoice an order.'),
                    confirm: function(){
                        self.gui.show_screen('clientlist');
                    },
                });
            } else {
                console.log('Factura Fiscal')
                var url_invoive = 'http://127.0.0.1:8081/invoice/customer'
                var http = new XMLHttpRequest()
                http.open("POST", url_invoive)
                http.send(jsonParams)

                http.onreadystatechange = function(){
                    if(this.readyState == 4 && this.status == 200){
                        var resultado = JSON.parse(this.responseText)
                        if ('Success' in resultado){
                            $('.button.print_fiscal').hide()
                            order.printer_doc_number = resultado.Success.currentInvoiceNumber
//                            order.init_from_JSON(order)
                            self.gui.show_popup('confirm',{
                                'title': _t('Recibo Impreso'),
                                'body':  _t('Factura impresa correctamente.'),
                                confirm: function(){
                                    $('.button.print_fiscal').show()
                                    self.pos.get_order().finalize();
                                },
                                cancel: function(){
                                    $('.button.print_fiscal').show()
    //                                $('.button.re-print-fiscal').removeClass('oe_hidden');
                                },
                            });
                        }else{
                            $('.button.print_fiscal').show()
                            $('.button.re-print-fiscal').addClass('oe_hidden');
                        }
                        console.log(resultado)

                    } else {
                        self.gui.show_popup("error", {
                           'title': _t("No se puede conectar con la APP"),
                           'body':  _t("Sin conexión a la aplicación de la impresora."),
                        });
                    }
                }
            }
        } else {
            console.log('Nota de cretido')
            if (!('customerve' in params['data'])){
                self.gui.show_popup('confirm',{
                    'title': _t('Please select the Customer'),
                    'body': _t('You need to select the customer before you can invoice an order.'),
                    confirm: function(){
                        self.gui.show_screen('clientlist');
                    },
                });
            } else {
                var url_credit_note = 'http://127.0.0.1:8081/invoice/credit_note'
                var http = new XMLHttpRequest()
                http.open("POST", url_credit_note)
                http.send(jsonParams)

                http.onreadystatechange = function(){
                    if(this.readyState == 4 && this.status == 200){
                        var resultado = JSON.parse(this.responseText)
                        if ('Success' in resultado){
                            $('.button.print_fiscal').hide()
                            order.printer_doc_number = resultado.Success.currentInvoiceNumber
//                            order.init_from_JSON(order)
                            self.gui.show_popup('confirm',{
                                'title': _t('Recibo Impreso'),
                                'body':  _t('Recibo impresa correctamente.'),
                                confirm: function(){
                                    $('.button.print_fiscal').show()
                                    self.pos.get_order().finalize();
                                },
                                cancel: function(){
                                    $('.button.print_fiscal').show()
    //                                $('.button.re-print-fiscal').removeClass('oe_hidden');
                                },
                            });
                        }else{
                            $('.button.print_fiscal').show()
                            $('.button.re-print-fiscal').addClass('oe_hidden');
                        }
                        console.log(resultado)

                    } else {
                        self.gui.show_popup("error", {
                           'title': _t("No se puede conectar con la APP"),
                           'body':  _t("Sin conexión a la aplicación de la impresora."),
                        });
                    }
                }
            }
        }

   },
    finalize: function(){
        var client = this.get_client();
        if ( client ) {
            client.loyalty_points = this.get_new_total_points();
            // The client list screen has a cache to avoid re-rendering
            // the client lines, and so the point updates may not be visible ...
            // We need a better GUI framework !
            this.pos.gui.screen_instances.clientlist.partner_cache.clear_node(client.id);
        }
        _super.prototype.finalize.apply(this,arguments);
    },
});

// TODO Save Printer Document Number
//var _super_order = models.Order.prototype;
//models.Order = models.Order.extend({
//    initialize: function(attributes, options) {
//        var self = this;
//        this.printer_doc_number = undefined;
//        _super_order.initialize.apply(this, arguments);
//    },
//    export_as_JSON: function() {
//        var data = _super_order.export_as_JSON.apply(this, arguments);
//        data.printer_doc_number = self.printerDocNumber;
//        return data;
//    },
//    init_from_JSON: function(json) {
//        this.printer_doc_number = json.printer_doc_number;
//        _super_order.init_from_JSON.call(this, json);
//    },
//
//});

});
