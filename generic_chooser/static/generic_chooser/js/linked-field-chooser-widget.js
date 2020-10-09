function LinkedFieldChooserWidget(id, opts) {
    /* A ChooserWidget which can pull values from other form elements to pass
    to the chooser modal as extra URL parameters. Define these by passing
    a 'linkedFields' dictionary in opts, of the form:
        {'urlParamName': '#some-css-selector'}
    which means: when generating the modal URL, look up the element matching
    some-css-selector, get its value, and add that to the URL as the
    parameter urlParamName.
    */
    opts = opts || {};
    ChooserWidget.call(this, id, opts);

    this.linkedFields = opts.linkedFields || {};
}

LinkedFieldChooserWidget.prototype = Object.create(ChooserWidget.prototype);

LinkedFieldChooserWidget.prototype.getModalURL = function() {
    var url = ChooserWidget.prototype.getModalURL.call(this);

    queryParams = [];
    for (var param in this.linkedFields) {
        var selector = this.linkedFields[param];
        var val = $(document).find(selector).val();
        queryParams.push({'name': param, 'value': val});
    }
    if (url.indexOf('?') == -1) {
        url += '?' + $.param(queryParams);
    } else {
        url += '&' + $.param(queryParams);
    }
    return url;
}
