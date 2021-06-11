odoo.define('bi_pos_currency_rate.pos_data', function (require) {
"use strict";

var ajax = require('web.ajax');
var BarcodeParser = require('barcodes.BarcodeParser');
var PosDB = require('point_of_sale.DB');
var devices = require('point_of_sale.devices');
var concurrency = require('web.concurrency');
var core = require('web.core');
var field_utils = require('web.field_utils');
var rpc = require('web.rpc');
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');
var models = require('point_of_sale.models');
var screens = require('point_of_sale.screens');
var popups = require('point_of_sale.popups');
var QWeb = core.qweb;
var _t = core._t;
var Mutex = concurrency.Mutex;
var round_di = utils.round_decimals;
var round_pr = utils.round_precision;

	models.load_models({
		model: 'res.currency',
		fields: ['name','symbol','position','rounding','rate','rate_in_company_currency'],
		domain: null, 
		loaded: function(self, poscurrency){
			self.poscurrency = poscurrency;
		},
	});


	var OrderSuper = models.Order;
	models.Order = models.Order.extend({
		init: function(parent,options){
			this._super(parent,options);
			this.currency_amount = this.currency_amount || "";
			this.currency_symbol = this.currency_symbol || "";
			this.currency_name = this.currency_name || "";
			this.recipet = this.recipet || "";
		},
		set_symbol: function(currency_symbol){
			this.currency_symbol = currency_symbol;
			this.trigger('change',this);
		},

		set_curamount: function(currency_amount){
			this.currency_amount = currency_amount;
			this.trigger('change',this);
		},
		set_curname: function(currency_name){
			this.currency_name = currency_name;
			this.trigger('change',this);
		},
		set_inrecipt: function(recipet){
			this.recipet = recipet;
			this.trigger('change',this);
		},

		get_curamount: function(currency_amount){
			return this.currency_amount;
		},
		get_symbol: function(currency_symbol){
			return this.currency_symbol;
		},
		get_curname: function(currency_name){
			return this.currency_name;
		},
		get_inrecipt: function(recipet){
			return this.recipet;
		},

		export_as_JSON: function() {
			var self = this;
			var loaded = OrderSuper.prototype.export_as_JSON.call(this);
			loaded.currency_amount = self.get_curamount() || 0.0;
			loaded.currency_symbol = self.get_symbol() || false;
			loaded.currency_name = self.get_curname() || false;
			loaded.recipet = self.get_inrecipt()|| false;
			return loaded;
		},

		init_from_JSON: function(json){
			OrderSuper.prototype.init_from_JSON.apply(this,arguments);
			this.currency_amount = json.currency_amount || "";
			this.currency_symbol = json.currency_symbol || "";
			this.currency_name = json.currency_name || "";
			this.recipet = json.recipet || "";
		},

	});

	var PaymentSuper = models.Paymentline;
	models.Paymentline = models.Paymentline.extend({
		init: function(parent,options){
			this._super(parent,options);
			this.currency_amount = this.currency_amount || "";
			this.currency_name = this.currency_name || "";
		},

		export_as_JSON: function() {
			var self = this;
			var loaded = PaymentSuper.prototype.export_as_JSON.call(this);
			loaded.currency_amount = this.order.currency_amount || 0.0;
			loaded.currency_name = this.order.currency_name || false;
			return loaded;
		},

		init_from_JSON: function(json){
			PaymentSuper.prototype.init_from_JSON.apply(this,arguments);
			this.currency_amount = json.currency_amount || "";
			this.currency_name = json.currency_name || "";
		},
	});



	


	screens.PaymentScreenWidget.include({

		init: function(parent, options) {
			this._super(parent, options);
		},
		events: {
			'change .drop-currency':  'change_currency',
			'click  .button-getamount' : 'update_amount',
			'change   .reciptclass' : 'change_config'
		},
	   	show: function(){
			var self = this;
			this._super();
			$('#pos_amount').on('focus', function() {
				$('body').off(this.keyboard_handler);
				$('body').off(this.keyboard_keydown_handler);    
				window.document.body.removeEventListener('keypress', self.keyboard_handler);
				window.document.body.removeEventListener('keydown', self.keyboard_keydown_handler);
			});
			$('#pos_amount').on('change', function() {
				$('body').keypress(this.keyboard_handler);
				$('body').keydown(this.keyboard_keydown_handler);    
				window.document.body.addEventListener('keypress', this.keyboard_handler);
				window.document.body.addEventListener('keydown', self.keyboard_keydown_handler);
			});        
			// window.document.body.addEventListener('keypress',this.keyboard_handler);
		},
		change_config:function(){
			var config;
			if($('#Receipt').prop('checked') == true){
				config =  true;
			}
			else if(!$('#Receipt').prop('checked') == true){
				config =  false;
			}   
			return config
		},
	 	// and complete the currency details
		change_currency: function() {

			var self = this;
			var currencies = this.pos.poscurrency;
			var cur = this.$('.drop-currency').val();
			var curr_sym;
			var order= this.pos.get_order();
			var pos_currency = this.pos.currency;
			for(var i=0;i<currencies.length;i++)
			{
				if(cur != pos_currency.id && cur==currencies[i].id)
				{
					var currency_in_pos = (currencies[i].rate/self.pos.currency.rate).toFixed(6);
					this.$('.currency_symbol').text(currencies[i].symbol);
					this.$('.currency_rate').text(currency_in_pos);
					this.$('.currency_name').text(currencies[i].name);
					curr_sym = currencies[i].symbol;

					var curr_tot =order.get_total_with_tax()*currency_in_pos;
					this.$('.currency_cal').text(parseFloat(curr_tot.toFixed(6)));
					order.set_curamount(parseFloat(curr_tot.toFixed(6)));
					order.set_symbol(curr_sym);
					order.set_curname(currencies[i].name);
					order.set_inrecipt(this.change_config());
					return curr_tot;
				}
				if(cur == pos_currency.id && cur==currencies[i].id){
					this.$('.currency_symbol').text(pos_currency.symbol);
					this.$('.currency_rate').text(1);
					this.$('.currency_name').text(pos_currency.name);
					curr_sym = pos_currency.symbol;

					var curr_tot =order.get_total_with_tax();
					this.$('.currency_cal').text(parseFloat(curr_tot.toFixed(2)));
					order.set_curamount(parseFloat(curr_tot.toFixed(2)));
					order.set_symbol(curr_sym);
					order.set_curname(pos_currency.name);
					order.set_inrecipt(this.change_config());
					return curr_tot;
				}
			}
		},

		update_amount: function() {
			var self = this;
			var order = this.pos.get_order();
			var paymentlines = this.pos.get_order().get_paymentlines();
			var open_paymentline = false;
			var tot = self.change_currency();
			var tot_amount = 0;
			var currency = this.pos.poscurrency;
			var user_amt = this.$('.edit-amount').val();
			var cur = this.$('.drop-currency').val();
			for(var j=0;j<paymentlines.length;j++){
				order.remove_paymentline(paymentlines[j])
			}

			order.add_paymentline(this.pos.payment_methods[0]);
			for(var i=0;i<currency.length;i++)
			{
				if(cur==currency[i].id)
				{
					for(var j=0;j<paymentlines.length;j++){
						tot_amount = user_amt*self.pos.company_currency.rate/currency[i].rate;
						paymentlines[j].amount =parseFloat(tot_amount.toFixed(2));
						paymentlines[j].amount_currency =parseFloat(tot.toFixed(2)) ;
						this.$('.show-payment').text(this.format_currency_no_symbol(paymentlines[j].amount));
					}
				}
			}
			this.render_paymentlines();
			if (!order) {
				return;
			} else if (order.is_paid()) {
				self.$('.next').addClass('highlight');
			}else{
				self.$('.next').removeClass('highlight');
			}
			window.document.body.removeEventListener('keypress', self.keyboard_handler);
			window.document.body.removeEventListener('keydown', self.keyboard_keydown_handler);
		},

});
		

});
