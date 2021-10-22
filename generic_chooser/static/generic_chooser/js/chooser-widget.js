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
    this.titleElement = this.chooserElement.find('.title');
    this.inputElement = $('#' + id);
    this.editLinkElement = this.chooserElement.find('.edit-link');
    this.editLinkWrapper = this.chooserElement.find('.edit-link-wrapper');
    if (!this.editLinkElement.attr('href')) {
        this.editLinkWrapper.hide();
    }
    this.chooseButton = $('.action-choose', this.chooserElement);
    this.idForLabel = null;

    this.modalResponses = {};
    this.modalResponses[opts.modalWorkflowResponseName || 'chosen'] = function(data) {
        self.setState({
            'value': data.id,
            'title': data.string,
            'edit_item_url': data.edit_link
        });
        self.inputElement.trigger('change');
    };

    this.chooseButton.on('click', function() {
        self.openModal();
    });

    $('.action-clear', this.chooserElement).on('click', function() {
        self.setState(null);
    });
}

ChooserWidget.prototype.getModalURL = function() {
    return this.chooserElement.data('choose-modal-url');
};

ChooserWidget.prototype.openModal = function() {
    ModalWorkflow({
        url: this.getModalURL(),
        onload: GENERIC_CHOOSER_MODAL_ONLOAD_HANDLERS,
        responses: this.modalResponses
    });
};

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
