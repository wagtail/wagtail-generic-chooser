function ChooserWidget(id, opts) {
    /*
    id = the ID of the HTML element where chooser behaviour should be attached
    opts = dictionary of configuration options, which may include:
        modalWorkflowResponseName = the response identifier returned by the modal workflow to
            indicate that an item has been chosen. Defaults to 'chosen'.
    */

    opts = opts || {};
    var self = this;

    this.id = id;
    this.chooserElement = $('#' + id + '-chooser');
    this.titleElement = this.chooserElement.find('[data-chooser-title]');
    this.inputElement = $('#' + id);
    this.editLinkElement = this.chooserElement.find('.edit-link');
    this.editLinkWrapper = this.chooserElement.find('.edit-link-wrapper');
    if (!this.editLinkElement.attr('href')) {
        this.editLinkWrapper.hide();
    }
    this.chooseButton = $('.action-choose', this.chooserElement);
    this.idForLabel = null;
    this.baseModalURL = opts.modalURL || this.chooserElement.data('choose-modal-url');

    this.modalResponses = {};
    this.modalResponses[opts.modalWorkflowResponseName || 'chosen'] = function(data) {
        self.setStateFromModalData(data);
    };

    this.chooseButton.on('click', function() {
        self.openModal();
    });

    $('.action-clear', this.chooserElement).on('click', function() {
        self.setState(null);
    });

    // attach a reference to this widget object onto the root element of the chooser
    this.chooserElement.get(0).widget = this;
}

ChooserWidget.prototype.getModalURL = function() {
    return this.baseModalURL;
};

ChooserWidget.prototype.getModalURLParams = function() {
    return {};
};

ChooserWidget.prototype.openModal = function() {
    ModalWorkflow({
        url: this.getModalURL(),
        urlParams: this.getModalURLParams(),
        onload: GENERIC_CHOOSER_MODAL_ONLOAD_HANDLERS,
        responses: this.modalResponses
    });
};

ChooserWidget.prototype.setStateFromModalData = function(data) {
    this.setState({
        'value': data.id,
        'title': data.string,
        'edit_item_url': data.edit_link
    });
}

ChooserWidget.prototype.setState = function(newState) {
    if (newState && newState.value !== null && newState.value !== '') {
        this.inputElement.val(newState.value);
        this.titleElement.text(newState.title);
        this.chooserElement.removeClass('blank');
        if (newState.edit_item_url) {
            this.editLinkElement.attr('href', newState.edit_item_url);
            this.editLinkWrapper.show();
        } else {
            this.editLinkWrapper.hide();
        }
    } else {
        this.inputElement.val('');
        this.chooserElement.addClass('blank');
    }
    this.inputElement.trigger('change');
};

ChooserWidget.prototype.getState = function() {
    return {
        'value': this.inputElement.val(),
        'title': this.titleElement.text(),
        'edit_item_url': this.editLinkElement.attr('href')
    };
};

ChooserWidget.prototype.getValue = function() {
    return this.inputElement.val();
};

ChooserWidget.prototype.focus = function() {
    this.chooseButton.focus();
}


function ChooserWidgetFactory(html, opts) {
    this.html = html;
    this.opts = opts;
    this.widgetClass = ChooserWidget;
}
ChooserWidgetFactory.prototype.render = function(placeholder, name, id, initialState) {
    var html = this.html.replace(/__NAME__/g, name).replace(/__ID__/g, id);
    placeholder.outerHTML = html;

    var chooser = new this.widgetClass(id, this.opts);
    chooser.setState(initialState);
    return chooser;
};
ChooserWidgetFactory.prototype.getModalURLParams = function() {
    return {};
};
ChooserWidgetFactory.prototype.openModal = function(callback, urlParams) {
    var responses = [];
    responses[this.opts.modalWorkflowResponseName || 'chosen'] = callback;

    var fullURLParams = this.getModalURLParams();
    if (urlParams) {
        for (key in urlParams) {
            fullURLParams[key] = urlParams[key];
        }
    }

    ModalWorkflow({
        url: this.opts.modalURL,
        urlParams: fullURLParams,
        onload: GENERIC_CHOOSER_MODAL_ONLOAD_HANDLERS,
        responses: responses
    });
};
ChooserWidgetFactory.prototype.getById = function(id) {
    /* retrieve the widget object corresponding to the given HTML ID */
    return document.getElementById(id + '-chooser').widget;
}

window.WagtailGenericChooserWidgetFactory = ChooserWidgetFactory;
