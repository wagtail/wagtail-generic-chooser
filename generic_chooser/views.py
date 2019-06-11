import requests

from django.conf.urls import url
from django.contrib.admin.utils import quote, unquote
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Page, Paginator
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.text import camel_case_to_spaces, slugify
from django.utils.translation import ugettext_lazy as _
from django.views import View

from wagtail.admin.forms.search import SearchForm
from wagtail.admin.modal_workflow import render_modal_workflow
from wagtail.admin.viewsets.base import ViewSet
from wagtail.search.backends import get_search_backend
from wagtail.search.index import class_is_indexed


class ChooserMixin:
    """
    Helper methods common to all sub-views of the chooser modal. Will be subclassed to implement
    different data sources (e.g. database versus REST API).
    """

    def get_object(self, pk):
        """
        Return the object corresponding to the given ID. Both 'object' and 'ID' are loosely defined
        here; for example, this may be a JSON API lookup returning a dict, rather than a database
        lookup returning a model instance. Any object type is fine as long as the other methods
        here (get_object_string etc) provide consistent behaviour on it, and the ID is a simple
        value that can be embedded into a URL.
        """
        raise NotImplementedError

    def get_object_string(self, instance):
        """
        Return a string representation of the given object instance
        """
        return str(instance)

    def get_object_id(self, instance):
        """
        Return the ID for the given object instance
        """
        raise NotImplementedError

    # URL route name for the chooser view (required) - should return the URL of the chooser view
    # when reversed with no arguments. If no suitable URL route exists, subclasses can override
    # get_choose_url instead.
    # This will be used as the action URL of the search form.
    choose_url_name = None

    def get_choose_url(self):
        return reverse(self.choose_url_name)

    # URL route name for the 'item chosen' view (required) - should return the URL of that view
    # when reversed with one argument, the instance ID. If no suitable URL route exists, subclasses
    # can override get_chosen_url instead.
    chosen_url_name = None

    def get_chosen_url(self, instance):
        object_id = self.get_object_id(instance)
        return reverse(self.chosen_url_name, args=(quote(object_id),))

    # URL route name for editing an existing item (optional) - should return the URL of the item's
    # edit view when reversed with the item's quoted ID as its only argument. If no suitable URL
    # route exists (e.g. it requires additional arguments), subclasses can override
    # get_edit_item_url instead.
    edit_item_url_name = None

    def get_edit_item_url(self, instance):
        if self.edit_item_url_name is None:
            return None
        else:
            object_id = self.get_object_id(instance)
            return reverse(self.edit_item_url_name, args=(quote(object_id),))

    # A permission policy object that can be queried to check if the user is able to create
    # objects of the type being chosen here
    permission_policy = None

    def user_can_create(self, user):
        """
        Return True iff the given user has permission to create objects of the type being
        chosen here
        """
        if self.permission_policy:
            return self.permission_policy.user_has_permission(user, 'add')
        else:
            return False

    def get_object_list(self):
        """
        Return an iterable consisting of all the choosable object instances
        """
        # FIXME: formalise when filtering (e.g. searching) happens in this workflow
        raise NotImplementedError

    # Number of results per page, or None for an unpaginated listing
    per_page = None

    def get_paginated_object_list(self):
        """
        Return a page of results according to the `page_number` attribute, as a tuple of
        an iterable sequence of instances and a Paginator object
        """
        # FIXME: should page_number be a parameter here instead?
        paginator = Paginator(self.get_object_list(), per_page=self.per_page)
        object_list = paginator.get_page(self.page_number)
        return (object_list, paginator)

    # whether this chooser provides a search field
    is_searchable = False

    # A prefix to use on HTML IDs and form field names within this modal, to prevent
    # name collisions with other elements on the page
    prefix = None

    def get_prefix(self):
        return self.prefix

    def get_chosen_response_data(self, item):
        """
        Generate the result value to be returned when an object has been chosen
        """
        return {
            'id': str(self.get_object_id(item)),
            'string': self.get_object_string(item),
            'edit_link': self.get_edit_item_url(item)
        }

    def get_chosen_response(self, item):
        """
        Return the HTTP response to indicate that an object has been chosen
        """
        response_data = self.get_chosen_response_data(item)

        return render_modal_workflow(
            self.request,
            None, None,
            None, json_data={'step': 'chosen', 'result': response_data}
        )


class ModelChooserMixin(ChooserMixin):
    """Mixin for chooser modals backed by the database / ORM"""

    model = None
    order_by = None

    @property
    def is_searchable(self):
        return class_is_indexed(self.model)

    def get_unfiltered_object_list(self):
        objects = self.model.objects.all()
        if self.order_by:
            objects = objects.order_by(self.order_by)
        return objects

    def get_object_list(self):
        object_list = self.get_unfiltered_object_list()

        if self.is_searching:
            search_backend = get_search_backend()
            object_list = search_backend.search(self.search_query, object_list)

        return object_list

    def get_object(self, pk):
        return self.model.objects.get(pk=pk)

    def get_object_id(self, instance):
        return instance.pk

    def get_prefix(self):
        # autogenerate a prefix from the model name if one is not supplied manually
        if not self.prefix:
            self.prefix = slugify(camel_case_to_spaces(self.model.__name__)) + '-chooser'

        return self.prefix


class DRFChooserMixin(ChooserMixin):
    """Mixin for chooser modals backed by a Django REST Framework API"""
    api_base_url = None
    title_field_name = None

    def get_api_parameters(self):
        params = {'format': 'json'}

        if self.is_searching:
            params['search'] = self.search_query

        return params

    def get_object_list(self):
        params = self.get_api_parameters()

        result = requests.get(self.api_base_url, params=params).json()
        return result['items']

    def get_paginated_object_list(self):
        params = self.get_api_parameters()
        params['limit'] = self.per_page
        params['offset'] = (self.page_number - 1) * self.per_page

        result = requests.get(self.api_base_url, params=params).json()
        paginator = APIPaginator(result['meta']['total_count'], self.per_page)
        page = Page(result['items'], self.page_number, paginator)
        return (page, paginator)

    def get_object_id(self, item):
        return item['id']

    def get_object_string(self, item):
        # Given an object dictionary from the API response, return the text to use as the label
        if self.title_field_name:
            # use the field specified by title_field_name, if supplied
            return item[self.title_field_name]
        else:
            # fall back on default behaviour (calling str() on the object)
            super().get_object_string(item)

    def get_object(self, id):
        url = '%s%s/?format=json' % (self.api_base_url, quote(id))
        result = requests.get(url).json()

        if 'id' not in result:
            # assume this is a 'not found' report
            raise ObjectDoesNotExist(result['message'])

        return result


class ChooseView(ChooserMixin, View):
    icon = 'snippet'
    page_title = _("Choose")
    search_placeholder = _("Search")
    template = 'generic_chooser/choose.html'
    results_template = 'generic_chooser/_results.html'

    def get(self, request):

        self.is_searching = False
        self.search_query = None

        if self.is_searchable:
            if 'q' in request.GET:
                self.search_form = SearchForm(request.GET, placeholder=self.search_placeholder)

                if self.search_form.is_valid():
                    self.search_query = self.search_form.cleaned_data['q']
                    self.is_searching = True
            else:
                self.search_form = SearchForm(placeholder=self.search_placeholder)

        self.is_paginated = self.per_page is not None
        if self.is_paginated:
            try:
                self.page_number = int(request.GET.get('p', 1))
            except ValueError:
                self.page_number = 1

            if self.page_number < 1:
                self.page_number = 1

        if self.is_paginated:
            self.object_list, self.paginator = self.get_paginated_object_list()
        else:
            self.object_list = self.get_object_list()

        # 'results=true' URL param indicates we should only render the results partial
        # rather than serving a full ModalWorkflow response
        if request.GET.get('results') == 'true':
            return render(request, self.get_results_template(), self.get_context_data())
        else:
            return render_modal_workflow(
                request,
                self.get_template(), None,
                self.get_context_data(), json_data={'step': 'choose'}
            )

    def get_rows(self):
        for item in self.object_list:
            yield self.get_row_data(item)

    def get_row_data(self, item):
        return {
            'choose_url': self.get_chosen_url(item),
            'title': self.get_object_string(item),
        }

    def get_context_data(self):
        context = {
            'icon': self.icon,
            'page_title': self.page_title,
            'rows': self.get_rows(),
            'results_template': self.get_results_template(),
            'is_searchable': self.is_searchable,
            'choose_url': self.get_choose_url(),
            'is_paginated': self.is_paginated,
        }

        if self.is_searchable:
            context.update({
                'search_form': self.search_form,
            })

        if self.is_paginated:
            context.update({
                'page': self.object_list,
                'paginator': self.paginator,
            })

        return context

    def get_results_template(self):
        return self.results_template

    def get_template(self):
        return self.template


class ModelChooseView(ModelChooserMixin, ChooseView):
    pass


class APIPaginator(Paginator):
    """
    Customisation of Django's Paginator to give us access to the page_range / num_pages
    functionality needed by pagination UI, without having to use Paginator's
    list-slicing logic - which isn't a good fit for API use, as it relies on knowing
    the total count of results before deciding which slice to request.

    Rather than instantiating it with a list/queryset and page number, we pass it the
    full item count, which is sufficient for page_range / num_pages to work.
    """
    def __init__(self, count, per_page, **kwargs):
        self._count = int(count)
        super().__init__([], per_page, **kwargs)

    @property
    def count(self):
        return self._count


class DRFChooseView(DRFChooserMixin, ChooseView):
    pass


class ChosenView(ChooserMixin, View):
    def get(self, request, pk):
        try:
            item = self.get_object(unquote(pk))
        except ObjectDoesNotExist:
            raise Http404

        return self.get_chosen_response(item)


class ModelChosenView(ModelChooserMixin, ChosenView):
    pass


class DRFChosenView(DRFChooserMixin, ChosenView):
    pass


class ChooserViewSet(ViewSet):
    base_choose_view_class = ChooseView
    base_chosen_view_class = ChosenView
    chooser_mixin_class = ChooserMixin

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # compose a final ChooseView subclass from base_choose_view_class and chooser_mixin_class
        self.choose_view_class = type(
            'ChooserViewSetChooseView',
            (self.chooser_mixin_class, self.base_choose_view_class),
            {}
        )

        # compose a final ChosenView subclass from base_chosen_view_class and chooser_mixin_class
        self.chosen_view_class = type(
            'ChooserViewSetChosenView',
            (self.chooser_mixin_class, self.base_chosen_view_class),
            {}
        )

    def get_choose_view_attrs(self):
        attrs = {
            'choose_url_name': self.get_url_name('choose'),
            'chosen_url_name': self.get_url_name('chosen'),
        }

        for attr_name in ('icon', 'page_title', 'per_page', 'is_searchable'):
            if hasattr(self, attr_name):
                attrs[attr_name] = getattr(self, attr_name)

        return attrs

    @property
    def choose_view(self):
        return self.choose_view_class.as_view(**self.get_choose_view_attrs())

    def get_chosen_view_attrs(self):
        attrs = {}

        for attr_name in ('edit_item_url_name',):
            if hasattr(self, attr_name):
                attrs[attr_name] = getattr(self, attr_name)

        return attrs

    @property
    def chosen_view(self):
        return self.chosen_view_class.as_view(**self.get_chosen_view_attrs())

    def get_urlpatterns(self):
        return super().get_urlpatterns() + [
            url(r'^$', self.choose_view, name='choose'),
            url(r'^(\d+)/$', self.chosen_view, name='chosen'),
        ]


class ModelChooserViewSet(ChooserViewSet):
    chooser_mixin_class = ModelChooserMixin

    def get_choose_view_attrs(self):
        attrs = super().get_choose_view_attrs()
        if hasattr(self, 'model'):
            attrs['model'] = self.model
        if hasattr(self, 'order_by'):
            attrs['order_by'] = self.order_by

        return attrs

    def get_chosen_view_attrs(self):
        attrs = super().get_chosen_view_attrs()
        if hasattr(self, 'model'):
            attrs['model'] = self.model

        return attrs


class DRFChooserViewSet(ChooserViewSet):
    chooser_mixin_class = DRFChooserMixin

    def get_choose_view_attrs(self):
        attrs = super().get_choose_view_attrs()
        if hasattr(self, 'api_base_url'):
            attrs['api_base_url'] = self.api_base_url
        if hasattr(self, 'title_field_name'):
            attrs['title_field_name'] = self.title_field_name

        return attrs

    def get_chosen_view_attrs(self):
        attrs = super().get_chosen_view_attrs()
        if hasattr(self, 'api_base_url'):
            attrs['api_base_url'] = self.api_base_url
        if hasattr(self, 'title_field_name'):
            attrs['title_field_name'] = self.title_field_name

        return attrs
