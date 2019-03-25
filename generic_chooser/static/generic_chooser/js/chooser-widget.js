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

    $('.action-choose', chooserElement).on('click', function() {
        var responses = {};
        responses[opts.modalWorkflowResponseName || 'chosen'] = function(snippetData) {
            input.val(snippetData.id);
            docTitle.text(snippetData.string);
            chooserElement.removeClass('blank');
            editLink.attr('href', snippetData.edit_link);
        };

        ModalWorkflow({
            url: chooserElement.data('choose-modal-url'),
            onload: GENERIC_CHOOSER_MODAL_ONLOAD_HANDLERS,
            responses: responses
        });
    });

    $('.action-clear', chooserElement).on('click', function() {
        input.val('');
        chooserElement.addClass('blank');
    });
}
