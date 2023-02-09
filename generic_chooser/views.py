import urllib

import requests
from django.contrib.admin.utils import quote, unquote
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import Page, Paginator
from django.forms import models as model_forms
from django.http import Http404
from django.shortcuts import render
from django.urls import re_path, reverse
from django.utils.text import camel_case_to_spaces, slugify
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.base import ContextMixin
from wagtail.admin.forms.search import SearchForm
from wagtail.admin.modal_workflow import render_modal_workflow
from wagtail.admin.viewsets.base import ViewSet
from wagtail.permission_policies import ModelPermissionPolicy
from wagtail.search.backends import get_search_backend
from wagtail.search.index import class_is_indexed


class ModalPageFurnitureMixin(ContextMixin):
    """
    Add icon and page title to the template context
    """
    icon = None
    page_title = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'header_icon': self.icon,
            'page_title': self.page_title,
        })
        return context


class ChooserMixin:
    """
    Helper methods common to all sub-views of the chooser modal. Will be subclassed to implement
    different data sources (e.g. database versus REST API).
    """
    # URL parameters to be passed on from the initial URL in the result of get_choose_url
    preserve_url_parameters = []

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

    def get_choose_url_parameters(self):
        params = {}
        for param in (self.preserve_url_parameters + ['multiple']):
            try:
                params[param] = self.request.GET[param]
            except KeyError:
                pass
        return params

    def get_choose_url(self):
        url = reverse(self.choose_url_name)
        params = self.get_choose_url_parameters()

        if params:
            param_string = urllib.parse.urlencode(params)
            if '?' in url:
                url += '&' + param_string
            else:
                url += '?' + param_string

        return url

    # URL route name for the 'item chosen' view (required) - should return the URL of that view
    # when reversed with one argument, the instance ID. If no suitable URL route exists, subclasses
    # can override get_chosen_url instead.
    chosen_url_name = None

    def get_chosen_url_parameters(self):
        params = {}
        try:
            params['multiple'] = self.request.GET['multiple']
        except KeyError:
            pass

        return params

    def get_chosen_url(self, instance):
        object_id = self.get_object_id(instance)
        url = reverse(self.chosen_url_name, args=(quote(object_id),))
        params = self.get_chosen_url_parameters()

        if params:
            param_string = urllib.parse.urlencode(params)
            if '?' in url:
                url += '&' + param_string
            else:
                url += '?' + param_string

        return url

    # URL route name for the 'multiple items chosen' view
    chosen_multiple_url_name = None

    def get_chosen_multiple_url(self):
        if self.chosen_multiple_url_name:
            return reverse(self.chosen_multiple_url_name)

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

    def get_permission_policy(self):
        return self.permission_policy

    def user_can_create(self, user):
        """
        Return True iff the given user has permission to create objects of the type being
        chosen here
        """
        permission_policy = self.get_permission_policy()
        if permission_policy:
            return permission_policy.user_has_permission(user, 'add')
        else:
            # If no permission policy set, treat that as granting access to all authenticated
            # users; this is the 'least surprise' approach, as the implementer would expect the
            # form to appear once a form_class (or fields) property is set up
            return True

    def get_object_list(self, **kwargs):
        """
        Return an iterable consisting of all the choosable object instances.
        kwargs contains parameters that may be used to modify the result set; currently the only
        one available is 'search_term', passed when is_searchable is True.
        """
        raise NotImplementedError

    # Number of results per page, or None for an unpaginated listing
    per_page = None

    def get_paginated_object_list(self, page_number, **kwargs):
        """
        Return a page of results according to the `page_number` attribute, as a tuple of
        an iterable sequence of instances and a Paginator object
        """
        paginator = Paginator(self.get_object_list(**kwargs), per_page=self.per_page)
        object_list = paginator.get_page(page_number)
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

    def _wrap_chosen_response_data(self, response_data):
        """
        Wrap a response_data JSON payload in a modal workflow response
        """
        return render_modal_workflow(
            self.request,
            None, None,
            None, json_data={'step': 'chosen', 'result': response_data}
        )

    def get_multiple_chosen_response(self, items):
        response_data = [
            self.get_chosen_response_data(item) for item in items
        ]
        return self._wrap_chosen_response_data(response_data)

    def get_chosen_response(self, item):
        """
        Return the HTTP response to indicate that an object has been chosen
        """
        response_data = self.get_chosen_response_data(item)
        if self.request.GET.get('multiple'):
            # a multiple result was requested but we're only returning one,
            # so wrap as a list
            response_data = [response_data]

        return self._wrap_chosen_response_data(response_data)


class ModelChooserMixin(ChooserMixin):
    """Mixin for chooser modals backed by the database / ORM"""

    model = None
    order_by = None

    def get_permission_policy(self):
        # if no permission policy is specified, use ModelPermissionPolicy
        # (which enforces standard Django model permissions)
        if not self.permission_policy:
            self.permission_policy = ModelPermissionPolicy(self.model)

        return self.permission_policy

    @property
    def is_searchable(self):
        return class_is_indexed(self.model)

    def get_unfiltered_object_list(self):
        objects = self.model.objects.all()
        if self.order_by:
            if isinstance(self.order_by, str):
                objects = objects.order_by(self.order_by)
            else:
                objects = objects.order_by(*self.order_by)
        return objects

    def get_object_list(self, search_term=None, **kwargs):
        object_list = self.get_unfiltered_object_list()

        if search_term:
            search_backend = get_search_backend()
            object_list = search_backend.search(search_term, object_list)

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

    def get_api_parameters(self, search_term=None, **kwargs):
        params = {'format': 'json'}

        if search_term:
            params['search'] = search_term

        return params

    def get_object_list(self, **kwargs):
        params = self.get_api_parameters(**kwargs)

        result = requests.get(self.api_base_url, params=params).json()
        return result['items']

    def get_paginated_object_list(self, page_number, **kwargs):
        params = self.get_api_parameters(**kwargs)
        params['limit'] = self.per_page
        params['offset'] = (page_number - 1) * self.per_page

        result = requests.get(self.api_base_url, params=params).json()
        paginator = APIPaginator(result['meta']['total_count'], self.per_page)
        page = Page(result['items'], page_number, paginator)
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


class ChooserListingTabMixin:
    search_placeholder = _("Search")
    listing_tab_label = _("Search")

    listing_tab_template = 'generic_chooser/_listing_tab.html'
    results_template = 'generic_chooser/_results.html'

    def get_page_number_from_url(self):
        try:
            page_number = int(self.request.GET.get('p', 1))
        except ValueError:
            page_number = 1

        if page_number < 1:
            page_number = 1

        return page_number

    def get_search_form(self):
        if 'q' in self.request.GET:
            return SearchForm(self.request.GET, placeholder=self.search_placeholder)
        else:
            return SearchForm(placeholder=self.search_placeholder)

    def get_rows(self):
        for item in self.object_list:
            yield self.get_row_data(item)

    def get_row_data(self, item):
        return {
            'object_id': self.get_object_id(item),
            'choose_url': self.get_chosen_url(item),
            'title': self.get_object_string(item),
        }

    def get_results_template(self):
        return self.results_template

    def get_listing_tab_template(self):
        return self.listing_tab_template

    def get_listing_tab_context_data(self):
        # parameters passed to get_object_list / get_paginated_object_list to modify results
        filters = {}

        if self.is_searchable:
            self.search_form = self.get_search_form()
            if self.search_form.is_valid():
                filters['search_term'] = self.search_form.cleaned_data['q']

        self.is_paginated = self.per_page is not None
        if self.is_paginated:
            page_number = self.get_page_number_from_url()
            self.object_list, self.paginator = self.get_paginated_object_list(page_number, **filters)
        else:
            self.object_list = self.get_object_list(**filters)

        context = {
            'rows': self.get_rows(),
            'results_template': self.get_results_template(),
            'is_searchable': self.is_searchable,
            'choose_url': self.get_choose_url(),
            'chosen_multiple_url': self.get_chosen_multiple_url(),
            'is_paginated': self.is_paginated,
            'is_multiple_choice': bool(self.request.GET.get('multiple')),
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


class ChooserCreateTabMixin:
    create_tab_label = _("Create")
    create_tab_template = 'generic_chooser/_create_tab.html'
    create_form_submit_label = _("Create")
    create_form_is_long_running = False
    create_form_submitted_label = _("Uploading…")

    initial = {}
    form_class = None

    def get_initial(self):
        """Return the initial data to use for forms on this view."""
        return self.initial.copy()

    def get_form_class(self):
        return self.form_class

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix() + '-create-form',
        }

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def create_form_is_available(self):
        if self.get_form_class() is None:
            return False

        if not self.user_can_create(self.request.user):
            return False

        return True

    def form_valid(self, form):
        """
        Called when a valid form submission is received; returns the created object
        """
        raise NotImplementedError

    def get_create_tab_context_data(self):
        context = {
            'create_form_submit_label': self.create_form_submit_label,
            'create_form_is_long_running': self.create_form_is_long_running,
            'create_form_submitted_label': self.create_form_submitted_label,
            'create_form': self.form,
        }

        return context


class ModelChooserCreateTabMixin(ChooserCreateTabMixin):
    fields = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set a nicer default submit button label, based on the model name
        if (self.create_form_submit_label == ChooserCreateTabMixin.create_form_submit_label) and self.model:
            self.create_form_submit_label = _("Add %s") % self.model._meta.verbose_name

    def get_form_class(self):
        if (self.fields is not None) and not self.form_class:
            self.form_class = model_forms.modelform_factory(self.model, fields=self.fields)

        return self.form_class

    def form_valid(self, form):
        """
        Called when a valid form submission is received; returns the created object
        """
        instance = form.save()
        return instance


class DRFChooserCreateTabMixin(ChooserCreateTabMixin):
    def form_valid(self, form):
        result = requests.post(self.api_base_url, json=form.cleaned_data)
        return result.json()


class BaseChooseView(ModalPageFurnitureMixin, ContextMixin, View):
    icon = 'snippet'
    page_title = _("Choose")

    template = 'generic_chooser/tabbed_modal_v3.html'

    def get_template(self):
        return self.template

    def get(self, request):
        # 'results=true' URL param indicates we should only render the results partial
        # rather than serving a full ModalWorkflow response
        if request.GET.get('results') == 'true':
            return render(
                request,
                self.get_results_template(),
                self.get_context_data(results_only=True)
            )
        else:
            if self.create_form_is_available():
                self.form = self.get_form()

            return render_modal_workflow(
                request,
                self.get_template(), None,
                self.get_context_data(), json_data={'step': 'choose'}
            )

    def post(self, request):
        if not self.create_form_is_available():
            raise PermissionDenied

        self.form = self.get_form()
        if self.form.is_valid():
            instance = self.form_valid(self.form)
            return self.get_chosen_response(instance)
        else:
            return render_modal_workflow(
                request,
                self.get_template(), None,
                self.get_context_data(), json_data={'step': 'choose'}
            )

    def get_context_data(self, results_only=False, **kwargs):
        context = super().get_context_data(**kwargs)

        # skip setting the full tabbed-interface context if we're only returning the results
        # partial
        if results_only:
            context.update(self.get_listing_tab_context_data())
            return context
        else:
            prefix = self.get_prefix()
            listing_tab_id = '%s-search' % prefix
            context.update({
                'tabs': [
                    {
                        'label': self.listing_tab_label,
                        'id': listing_tab_id,
                        'template': self.listing_tab_template,
                    },
                ],
                'active_tab': listing_tab_id,
            })

            context.update(self.get_listing_tab_context_data())

            if self.create_form_is_available():
                create_tab_id = '%s-create' % prefix
                context['tabs'].append({
                    'label': self.create_tab_label,
                    'id': create_tab_id,
                    'template': self.create_tab_template,
                    'classname': 'create-section',
                })
                context.update(self.get_create_tab_context_data())
                if self.request.method == 'POST' and not self.form.is_valid():
                    # focus the create tab on validation errors
                    context['active_tab'] = create_tab_id

            return context


class ModelChooseView(ChooserMixin, ChooserListingTabMixin, ModelChooserCreateTabMixin, BaseChooseView):
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


class DRFChooseView(DRFChooserMixin, ChooserListingTabMixin, DRFChooserCreateTabMixin, BaseChooseView):
    pass


class BaseChosenView(View):
    def get(self, request, pk):
        try:
            item = self.get_object(unquote(pk))
        except ObjectDoesNotExist:
            raise Http404

        return self.get_chosen_response(item)


class BaseChosenMultipleView(View):
    def get(self, request):
        items = []
        for pk in request.GET.getlist('id'):
            try:
                items.append(self.get_object(pk))
            except ObjectDoesNotExist:
                pass

        return self.get_multiple_chosen_response(items)


class ModelChosenView(ModelChooserMixin, BaseChosenView):
    pass


class DRFChosenView(DRFChooserMixin, BaseChosenView):
    pass


class ChooserViewSet(ViewSet):
    base_choose_view_class = BaseChooseView
    base_chosen_view_class = BaseChosenView
    base_chosen_multiple_view_class = BaseChosenMultipleView
    chooser_mixin_class = ChooserMixin
    listing_tab_mixin_class = ChooserListingTabMixin
    create_tab_mixin_class = ChooserCreateTabMixin

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # compose a final ChooseView subclass from base_choose_view_class and chooser_mixin_class
        self.choose_view_class = type(
            'ChooserViewSetChooseView',
            (
                self.chooser_mixin_class, self.listing_tab_mixin_class,
                self.create_tab_mixin_class, self.base_choose_view_class
            ),
            {}
        )

        # compose a final ChosenView subclass from base_chosen_view_class and chooser_mixin_class
        self.chosen_view_class = type(
            'ChooserViewSetChosenView',
            (self.chooser_mixin_class, self.base_chosen_view_class),
            {}
        )

        # compose a final ChosenMultipleView subclass from base_chosen_multiple_view_class and chooser_mixin_class
        self.chosen_multiple_view_class = type(
            'ChooserViewSetChosenMultipleView',
            (self.chooser_mixin_class, self.base_chosen_multiple_view_class),
            {}
        )

    def get_choose_view_attrs(self):
        attrs = {
            'choose_url_name': self.get_url_name('choose'),
            'chosen_url_name': self.get_url_name('chosen'),
            'chosen_multiple_url_name': self.get_url_name('chosen_multiple'),
        }

        for attr_name in (
            'icon', 'page_title', 'per_page', 'is_searchable', 'form_class', 'edit_item_url_name',
            'permission_policy', 'prefix',
        ):
            if hasattr(self, attr_name):
                attrs[attr_name] = getattr(self, attr_name)

        return attrs

    @property
    def choose_view(self):
        return self.choose_view_class.as_view(**self.get_choose_view_attrs())

    def get_chosen_view_attrs(self):
        attrs = {}

        for attr_name in ('edit_item_url_name', 'prefix',):
            if hasattr(self, attr_name):
                attrs[attr_name] = getattr(self, attr_name)

        return attrs

    @property
    def chosen_view(self):
        return self.chosen_view_class.as_view(**self.get_chosen_view_attrs())

    def get_chosen_multiple_view_attrs(self):
        attrs = {}

        for attr_name in ('edit_item_url_name', 'prefix',):
            if hasattr(self, attr_name):
                attrs[attr_name] = getattr(self, attr_name)

        return attrs

    @property
    def chosen_multiple_view(self):
        return self.chosen_multiple_view_class.as_view(**self.get_chosen_multiple_view_attrs())

    def get_urlpatterns(self):
        return super().get_urlpatterns() + [
            re_path(r'^$', self.choose_view, name='choose'),
            re_path(r'^(\d+)/$', self.chosen_view, name='chosen'),
            re_path(r'^chosen-multiple/$', self.chosen_multiple_view, name='chosen_multiple'),
        ]


class ModelChooserViewSet(ChooserViewSet):
    chooser_mixin_class = ModelChooserMixin
    create_tab_mixin_class = ModelChooserCreateTabMixin

    def get_choose_view_attrs(self):
        attrs = super().get_choose_view_attrs()
        for attr_name in ('model', 'order_by', 'fields'):
            if hasattr(self, attr_name):
                attrs[attr_name] = getattr(self, attr_name)

        return attrs

    def get_chosen_view_attrs(self):
        attrs = super().get_chosen_view_attrs()
        if hasattr(self, 'model'):
            attrs['model'] = self.model

        return attrs

    def get_chosen_multiple_view_attrs(self):
        attrs = super().get_chosen_view_attrs()
        if hasattr(self, 'model'):
            attrs['model'] = self.model

        return attrs


class DRFChooserViewSet(ChooserViewSet):
    chooser_mixin_class = DRFChooserMixin
    create_tab_mixin_class = DRFChooserCreateTabMixin

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

    def get_chosen_multiple_view_attrs(self):
        attrs = super().get_chosen_view_attrs()
        if hasattr(self, 'api_base_url'):
            attrs['api_base_url'] = self.api_base_url
        if hasattr(self, 'title_field_name'):
            attrs['title_field_name'] = self.title_field_name

        return attrs
