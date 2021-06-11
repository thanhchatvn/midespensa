odoo.define('pos_price_checker', function (require) {
"use strict";
    var session = require('web.session');
    var core = require('web.core');
    var screens = require('point_of_sale.screens');
    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var models = require('point_of_sale.models');
    var gui = require('point_of_sale.gui');
    var chrome = require('point_of_sale.chrome')
    var PosPopWidget = require('point_of_sale.popups');
    var devices = require('point_of_sale.BarcodeReader');
    var QWeb = core.qweb;
    var _t = core._t;


    devices.include({
        scan: function(code){
            var current_screen = this.pos.gui.get_current_screen();
            if(current_screen == "customer_screen"){
                var product = this.pos.db.get_product_by_barcode(code);
                this.pos.gui.show_screen('customer_screen','refresh',{"product":product});
            }
            else{
                if (!code) {
                    return;
                }
                var parsed_result = this.barcode_parser.parse_barcode(code);
                if (this.action_callback[parsed_result.type]) {
                    this.action_callback[parsed_result.type](parsed_result);
                } else if (this.action_callback.error) {
                    this.action_callback.error(parsed_result);
                } else {
                    console.warn("Ignored Barcode Scan:", parsed_result);
                }
            }
        },
    });
    var CustomerScreenWidget = PosBaseWidget.extend({
    template: 'CustomerScreenWidget',
	    renderElement:function(options){
	    	var self = this;
	    	this._super(options);
            var availableTags = [];
            if (this.pos.config.allow_price_checker) {
                var products = self.pos.db.product_by_id;
                jQuery.each( products, function( i, val ) {
                  availableTags.push({id:val.id,value:val.display_name});
                });
                $('.searchbox input').autocomplete({
                    source: availableTags,
                    select: function (event, ui) {
                        if(ui != undefined){
                            var product = self.pos.db.get_product_by_id(ui.item.id);
                            self.pos.gui.show_screen('customer_screen','refresh',{"product":product});
                        }
                    }
                });
                $(".searchbox input" ).focusin(function(event) {
                    if(self.pos.config.iface_vkeyboard && self.chrome.widget.keyboard){
                        self.chrome.widget.keyboard.connect($(this));
                    }
                    event.stopPropagation();
                });
                $(".simple_keyboard li").click(function(event){
                    $(".searchbox input").focus();
                    $(".searchbox input").keydown();
                    event.stopPropagation();
                });
            }
	    },
        show: function(options){
            this.options = options || {};
            var self = this;
            this._super(options);
            this.renderElement(options);
        },
        close: function() {
            var self = this;
        },
    });
    var total_ids12 = []
    chrome.Chrome.include({
        build_widgets: function() {
            var self = this;
            this._super();
            if(this.pos.config.allow_price_checker){
                setTimeout(function(){
                	self.gui.show_screen('customer_screen');
                	$(".pos .pos-content").css("top", "0px");
                }, 5);
            }
        },
        load_widgets: function(widgets) {
            this._super(widgets);
            if(this.pos.config.allow_price_checker){
                gui.define_screen({
                     'name': 'customer_screen',
                     'widget': CustomerScreenWidget,
                });
            }
        }
    });
});

