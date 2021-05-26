odoo.define('l10n_ve_fiscal_printer.buttons', function (require) {
    "use strict";

var core = require('web.core');
var FormController = require('web.FormController');

var _t = core._t;
var QWeb = core.qweb;

FormController.include({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        _onButtonZClicked: '_onButtonZClicked',
    }),

    _onExpectedDateChanged: function (event) {
        console.log('jeison')
        console.log('jeison')
        console.log('jeison')
        console.log('jeison')
        console.log('jeison')
        console.log('jeison')
        console.log('jeison')
        console.log('jeison')
//        event.stopPropagation();
//        var self = this;
//        this.model.changeExpectedDate(this.handle, event.data.moveLineID, event.data.newDate).then(function () {
//            self.reload();
//        });
    },


    renderButtons: function ($node) {
        this._super.apply(this, arguments);

        if (this.$buttons) {
            this.$buttons.on('click', '.o_printer_reports_z',
                this._onPrintZ.bind(this));
            this.$buttons.on('click', '.o_printer_reports_x',
                this._onPrintX.bind(this));
        }
    },

    _update: function () {
        this._updateButtons();
        return this._super.apply(this, arguments);
    },

    _updateButtons: function () {
        if (!this.$buttons) {
            return;
        }
        this._super.apply(this, arguments);
    },

    _onPrintZ: function () {
        var url = 'http://127.0.0.1:8081/hka/reportz'
        var http = new XMLHttpRequest()
        http.open("POST", url)

        http.onreadystatechange = function(){

            if(this.readyState == 4 && this.status == 200){
                var resultado = JSON.parse(this.responseText)
                console.log(resultado)
            }
        }
        http.send()
    },

    _onPrintX: function () {
        var url = 'http://127.0.0.1:8081/hka/reportx'
        var http = new XMLHttpRequest()
        http.open("POST", url)

        http.onreadystatechange = function(){

            if(this.readyState == 4 && this.status == 200){
                var resultado = JSON.parse(this.responseText)
                console.log(resultado)
            }
        }
        http.send()
    },


});
//End Odoo Define
});