const GENERIC_CHOOSER_MODAL_ONLOAD_HANDLERS = {
    choose(modal, jsonData) {
        function serializeFormData(form) {
            // Return the non-empty form data as an object
            return Object.fromEntries(
                Array.from(new FormData(form))
                    .filter(pair => !!pair[1])
            );
        }

        function ajaxifyLinks(context) {
            $('a.item-choice', context).on('click', function() {
                modal.loadUrl(this.href);
                return false;
            });

            $('.pagination a', context).on('click', function() {
                fetchResults(this.href);
                return false;
            });
        }

        const searchForm = modal.body[0].querySelector('form.chooser-search');
        const searchResults = modal.body[0].querySelector('#search-results');
        let request;

        function fetchResults(url, requestData) {
            const opts = {
                url: url,
                success(data) {
                    request = null;
                    $(searchResults).html(data);
                    ajaxifyLinks(searchResults);
                },
                error() {
                    request = null;
                }
            };

            // FIXME: The result view should be a distinct one
            const params = new URLSearchParams(new URL(url).search);
            if (!params.has('results')) {
                requestData = $.extend(
                    { results: 'true' },
                    requestData
                );
            }

            if (requestData) {
                opts.data = requestData;
            }

            request = $.ajax(opts);
        }

        ajaxifyLinks(modal.body);

        if (searchForm) {
            const searchUrl = searchForm.action;

            function search() {
                fetchResults(searchUrl, serializeFormData(searchForm));
                return false;
            }

            $(searchForm).on('submit', search);

            $(searchForm.elements).on('input', function() {
                if(request) {
                    request.abort();
                }
                clearTimeout($.data(this, 'timer'));
                const wait = setTimeout(search, 50);
                $(this).data('timer', wait);
            });
        }

        $('form.create-form', modal.body).on('submit', function() {
            const formdata = new FormData(this);

            $.ajax({
                url: this.action,
                data: formdata,
                processData: false,
                contentType: false,
                type: 'POST',
                dataType: 'text',
                success: modal.loadResponseText,
                error(response, textStatus, errorThrown) {
                    const message = jsonData.error_message + '<br />' + errorThrown + ' - ' + response.status;
                    $('.create-section', modal.body).append(
                        '<div class="help-block help-critical">' +
                        '<strong>' + jsonData.error_label + ': </strong>' + message + '</div>');
                }
            });

            return false;
        });
    },
    chosen(modal, jsonData) {
        modal.respond('chosen', jsonData.result);
        modal.close();
    }
};
