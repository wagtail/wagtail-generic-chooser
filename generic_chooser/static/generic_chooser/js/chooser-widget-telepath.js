(function() {
    function Chooser(html) {
        this.html = html;
    }
    Chooser.prototype.render = function(placeholder, name, id, initialState) {
        var html = this.html.replace(/__NAME__/g, name).replace(/__ID__/g, id);
        placeholder.outerHTML = html;

        var chooser = new ChooserWidget(id);
        chooser.setState(initialState);
        return chooser;
    };

    window.telepath.register('wagtail_generic_chooser.widgets.Chooser', Chooser);
})();
