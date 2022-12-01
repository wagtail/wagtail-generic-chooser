GENERIC_CHOOSER_MODAL_ONLOAD_HANDLERS = {
    'choose': function(modal, jsonData) {
        var paginationUrl = $('.pagination', modal.body).data('action-url');

        function ajaxifyLinks(context) {
            $('a.item-choice', context).on('click', function() {
                modal.loadUrl(this.href);
                return false;
            });

            $('.pagination a', context).on('click', function() {
                var page = this.getAttribute('data-page');
                setPage(page);
                return false;
            });
        }
        ajaxifyLinks(modal.body);
        if ($('[data-wgc-tabs]', modal.body).length) {
            initWagtailGenericChooserTabs();
        }

        var searchUrl = $('form.chooser-search', modal.body).attr('action');
        var searchRequest;

        function search() {
            searchRequest = $.ajax({
                url: searchUrl,
                data: {q: $('#id_q').val(), results: 'true'},
                success: function(data, status) {
                    searchRequest = null;
                    $('#search-results').html(data);
                    ajaxifyLinks($('#search-results'));
                },
                error: function() {
                    searchRequest = null;
                }
            });
            return false;
        }

        $('form.chooser-search', modal.body).on('submit', search);

        $('#id_q').on('input', function() {
            if(searchRequest) {
                searchRequest.abort();
            }
            clearTimeout($.data(this, 'timer'));
            var wait = setTimeout(search, 50);
            $(this).data('timer', wait);
        });

        function setPage(page) {
            var dataObj = {p: page, results: 'true'};

            if ($('#id_q').length && $('#id_q').val().length) {
                dataObj.q = $('#id_q').val();
            }

            $.ajax({
                url: paginationUrl,
                data: dataObj,
                success: function(data, status) {
                    $('#search-results').html(data);
                    ajaxifyLinks($('#search-results'));
                }
            });
            return false;
        }

        $('form.create-form', modal.body).on('submit', function() {
            const button = $(this).find('[type="submit"]');
            button.prop("disabled", true);

            var formdata = new FormData(this);

            $.ajax({
                url: this.action,
                data: formdata,
                processData: false,
                contentType: false,
                type: 'POST',
                dataType: 'text',
                success: modal.loadResponseText,
                error: function(response, textStatus, errorThrown) {
                    message = jsonData['error_message'] + '<br />' + errorThrown + ' - ' + response.status;
                    $('.create-section', modal.body).append(
                        '<div class="help-block help-critical">' +
                        '<strong>' + jsonData['error_label'] + ': </strong>' + message + '</div>');
                }
            });

            return false;
        });

        modal.ajaxifyForm('form[data-multiple-choice-form]');
    },
    'chosen': function(modal, jsonData) {
        modal.respond('chosen', jsonData['result']);
        modal.close();
    }
};
