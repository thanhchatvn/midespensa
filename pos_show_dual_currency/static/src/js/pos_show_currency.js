odoo.define("pos_show_dual_currency.models", function(require) {
    "use strict";
    var screens = require('point_of_sale.screens');
    screens.OrderWidget.include({
        update_summary: function(){
            var order = this.pos.get_order();
            if (!order.get_orderlines().length) {
                return;
            }
            var total = order ? order.get_total_with_tax() : 0;
            var taxes = order ? total - order.get_total_without_tax() : 0;
            if(this.pos.config.show_dual_currency){
                var total_currency = 0;
                var taxes_currency = 0;
                var rate_company = parseFloat(this.pos.config.rate_company);
                var show_currency_rate = parseFloat(this.pos.config.show_currency_rate);
                if(rate_company > show_currency_rate){
                    total_currency = total * (rate_company / show_currency_rate);
                    taxes_currency = taxes * (rate_company / show_currency_rate);
                }else if(rate_company < show_currency_rate){
                    if(show_currency_rate>0){
                        total_currency = total * (rate_company / show_currency_rate);
                        taxes_currency = taxes * (rate_company / show_currency_rate);
                    }
                }else{
                    total_currency = total;
                    taxes_currency = taxes;
                }
                var total_currency_text = '';
                var taxes_currency_text = '';
                if(this.pos.config.show_currency_position=='before'){
                    total_currency_text = '/'+this.pos.config.show_currency_symbol+' '+this.format_currency_no_symbol(total_currency);
                    taxes_currency_text = '/'+this.pos.config.show_currency_symbol+' '+this.format_currency_no_symbol(taxes_currency);
                }else{
                    total_currency_text = '/'+this.format_currency_no_symbol(total_currency)+' '+this.pos.config.show_currency_symbol;
                    taxes_currency_text = '/'+this.format_currency_no_symbol(taxes_currency)+' '+this.pos.config.show_currency_symbol;
                }

                this.el.querySelector('.summary .total .total_show .value').textContent = this.format_currency(total);
                this.el.querySelector('.summary .total .total_show .value_currency').textContent = total_currency_text;
                this.el.querySelector('.summary .total .subentry .value').textContent = this.format_currency(taxes);
                this.el.querySelector('.summary .total .subentry .value_currency').textContent = taxes_currency_text;
            }else{
                this.el.querySelector('.summary .total .total_show .value').textContent = this.format_currency(total);
                this.el.querySelector('.summary .total .subentry .value').textContent = this.format_currency(taxes);
            }
        }
    });

});