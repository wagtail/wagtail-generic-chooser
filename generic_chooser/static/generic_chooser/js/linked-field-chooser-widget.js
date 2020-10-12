function LinkedFieldChooserWidget(id, opts) {
    /* A ChooserWidget which can pull values from other form elements to pass
    to the chooser modal as extra URL parameters. Define these by passing
    a 'linkedFields' dictionary in opts, of the form:
        {'urlParamName': {'id': 'some-element-id'}}
    which means: when generating the modal URL, look up the element with
    id="some-element-id", get its value, and add that to the URL as the
    parameter urlParamName.

    Alternative lookup types:
        {'urlParamName': {'selector': '.some-selector'}}
        - look up the element matching the given CSS selector
        {'urlParamName': {'match': r'^body-\d+-value-', 'append': 'country'}}
        - look up the ID formed by matching the CURRENT widget's ID against
          the given regexp, then appending the given string
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
        var lookup = this.linkedFields[param];
        var val;
        if (typeof(lookup) == 'string') {
            val = $(document).find(lookup).val();
        } else if (lookup.id) {
            val = $(document).find('#' + lookup.id).val();
        } else if (lookup.selector) {
            val = $(document).find(lookup.selector).val();
        } else if (lookup.match) {
            var match = this.id.match(new RegExp(lookup.match));
            if (match) {
                var id = match[0];
                if (lookup.append) {
                    id += lookup.append;
                }
                val = $(document).find('#' + id).val();
            }
        }
        if (val) {
            queryParams.push({'name': param, 'value': val});
        }
    }
    if (url.indexOf('?') == -1) {
        url += '?' + $.param(queryParams);
    } else {
        url += '&' + $.param(queryParams);
    }
    return url;
}
