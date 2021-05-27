(function() {
    function LinkedFieldChooser(html, opts) {
        this.html = html;
        this.opts = opts;
    }
    LinkedFieldChooser.prototype.render = function(placeholder, name, id, initialState) {
        var html = this.html.replace(/__NAME__/g, name).replace(/__ID__/g, id);
        placeholder.outerHTML = html;

        var chooser = new LinkedFieldChooserWidget(id, this.opts);
        chooser.setState(initialState);
        return chooser;
    };

    window.telepath.register('wagtail_generic_chooser.widgets.LinkedFieldChooser', LinkedFieldChooser);
})();
