function createChooserWidget(id, opts) {
    /*
    id = the ID of the HTML element where chooser behaviour should be attached
    opts = dictionary of configuration options, which may include:
        modalWorkflowResponseName = the response identifier returned by the modal workflow to
            indicate that an item has been chosen. Defaults to 'chosen'.
    */

    opts = opts || {};

    var chooserElement = $('#' + id + '-chooser');
    var docTitle = chooserElement.find('.title');
    var input = $('#' + id);
    var editLink = chooserElement.find('.edit-link');
    var editLinkWrapper = chooserElement.find('.edit-link-wrapper');
    if (!editLink.attr('href')) {
        editLinkWrapper.hide();
    }
    var chooseButton = $('.action-choose', chooserElement);

    var widget = {
        idForLabel: null,
        getState: function() {
            return {
                'value': input.val(),
                'title': docTitle.text(),
                'edit_item_url': editLink.attr('href')
            };
        },
        getValue: function() {
            return input.val();
        },
        setState: function(newState) {
            if (newState) {
                input.val(newState.value);
                docTitle.text(newState.title);
                chooserElement.removeClass('blank');
                if (newState.edit_item_url) {
                    editLink.attr('href', newState.edit_item_url);
                    editLinkWrapper.show();
                } else {
                    editLinkWrapper.hide();
                }
            } else {
                input.val('');
                chooserElement.addClass('blank');
            }
        },
        focus: function() {
            chooseButton.focus();
        }
    };

    chooseButton.on('click', function() {
        var responses = {};
        responses[opts.modalWorkflowResponseName || 'chosen'] = function(snippetData) {
            widget.setState({
                'value': snippetData.id,
                'title': snippetData.string,
                'edit_item_url': snippetData.edit_link
            });
        };

        ModalWorkflow({
            url: chooserElement.data('choose-modal-url'),
            onload: GENERIC_CHOOSER_MODAL_ONLOAD_HANDLERS,
            responses: responses
        });
    });

    $('.action-clear', chooserElement).on('click', function() {
        widget.setState(null);
    });

    return widget;
}
