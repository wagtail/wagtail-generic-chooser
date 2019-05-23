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
from django.views.generic.edit import FormMixin, ModelFormMixin

from wagtail.admin.forms.search import SearchForm
from wagtail.admin.modal_workflow import render_modal_workflow
from wagtail.admin.viewsets.base import ViewSet
from wagtail.core.permission_policies import ModelPermissionPolicy
from wagtail.search.backends import get_search_backend
from wagtail.search.index import class_is_indexed


class ChooseView(FormMixin, View):
    icon = 'snippet'

    page_title = _("Choose")
    search_placeholder = _("Search")
    search_tab_label = _("Search")
    create_tab_label = _("Create")
    create_form_submit_label = _("Create")
    create_form_is_long_running = False
    create_form_submitted_label = _("Uploading…")

    template = 'generic_chooser/choose.html'
    results_template = 'generic_chooser/_results.html'
    per_page = None
    is_searchable = False

    # URL route name for this chooser view - should return the URL of the chooser view when
    # reversed with no arguments. If no suitable URL route exists, subclasses can override
    # get_choose_url instead.
    # This will be used as the action URL of the search form.
    choose_url_name = None

    # URL route name for the 'item chosen' view - should return the URL of that view when
    # reversed with one argument, the instance ID. If no suitable URL route exists,
    # subclasses can override get_chosen_url instead.
    chosen_url_name = None

    # A permission policy object that can be queried to check if the user is able to create
    # objects of the type being chosen here
    permission_policy = None

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

    def get_object_string(self, instance):
        return str(instance)

    def get_choose_url(self):
        return reverse(self.choose_url_name)

    def get_chosen_url(self, instance):
        object_id = self.get_object_id(instance)
        return reverse(self.chosen_url_name, args=(quote(object_id),))

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
            'search_tab_label': self.search_tab_label,
            'create_tab_label': self.create_tab_label,
            'create_form_submit_label': self.create_form_submit_label,
            'create_form_is_long_running': self.create_form_is_long_running,
            'create_form_submitted_label': self.create_form_submitted_label,

            'rows': self.get_rows(),
            'results_template': self.get_results_template(),
            'is_searchable': self.is_searchable,
            'choose_url': self.get_choose_url(),
            'is_paginated': self.is_paginated,
            'prefix': self.get_prefix(),
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

        create_form = None
        if self.user_can_create(self.request.user):
            create_form = self.get_form()

        context.update({
            'create_form': create_form,
            'tabbed': create_form is not None,
        })

        return context

    def get_results_template(self):
        return self.results_template

    def get_template(self):
        return self.template

    def get_object_list(self):
        raise NotImplementedError

    def get_paginated_object_list(self):
        paginator = Paginator(self.get_object_list(), per_page=self.per_page)
        object_list = paginator.get_page(self.page_number)
        return (object_list, paginator)

    def get_object_id(self, instance):
        raise NotImplementedError

    def user_can_create(self, user):
        if self.permission_policy:
            return self.permission_policy.user_has_permission(user, 'add')
        else:
            return False

    def get_form(self):
        # accommodate get_form_class returning None to indicate that no
        # creation form should be rendered
        if self.get_form_class() is None:
            return None

        return super().get_form()

    def get_form_kwargs(self):
        # FormMixin will use self.prefix as the form ID prefix, but we also use self.prefix elsewhere
        # in the modal (e.g. tab anchor IDs) to avoid clashes with the calling page; we therefore need
        # to scope the form prefix more tightly
        kwargs = super().get_form_kwargs()
        if kwargs['prefix']:
            kwargs['prefix'] += '-create-form'

        return kwargs


class ModelChooseView(ModelFormMixin, ChooseView):
    model = None
    order_by = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.permission_policy:
            self.permission_policy = ModelPermissionPolicy(self.model)

        if (not self.prefix) and self.model:
            self.prefix = slugify(camel_case_to_spaces(self.model.__name__)) + '-chooser'

        if (self.create_form_submit_label == ChooseView.create_form_submit_label) and self.model:
            self.create_form_submit_label = _("Add %s") % self.model._meta.verbose_name

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

    def get_object_id(self, instance):
        return instance.pk

    def get_form_class(self):
        if self.fields is None and self.form_class is None:
            # ModelFormMixin will throw an ImproperlyConfigured if neither fields nor form_class
            # is supplied; we'll pre-empt this and skip the creation form instead
            return None

        return super().get_form_class()


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


class DRFChooseView(ChooseView):
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


class ChosenView(View):

    # URL route name for editing an existing item - should return the URL of the item's edit view
    # when reversed with the item's quoted ID as its only argument. If no suitable URL route exists
    # (e.g. it requires additional arguments), subclasses can override get_edit_item_url instead.
    edit_item_url_name = None

    def get_object(self, pk):
        raise NotImplementedError

    def get_object_id(self, instance):
        raise NotImplementedError

    def get_edit_item_url(self, instance):
        if self.edit_item_url_name is None:
            return None
        else:
            object_id = self.get_object_id(instance)
            return reverse(self.edit_item_url_name, args=(quote(object_id),))

    def get_object_string(self, instance):
        return str(instance)

    def get_response_data(self, item):
        return {
            'id': str(self.get_object_id(item)),
            'string': self.get_object_string(item),
            'edit_link': self.get_edit_item_url(item)
        }

    def get(self, request, pk):
        try:
            item = self.get_object(unquote(pk))
        except ObjectDoesNotExist:
            raise Http404

        response_data = self.get_response_data(item)

        return render_modal_workflow(
            request,
            None, None,
            None, json_data={'step': 'chosen', 'result': response_data}
        )


class ModelChosenView(ChosenView):
    model = None

    def get_object(self, pk):
        return self.model.objects.get(pk=pk)

    def get_object_id(self, instance):
        return instance.pk


class DRFChosenView(ChosenView):
    api_base_url = None
    title_field_name = None

    def get_object(self, id):
        url = '%s%s/?format=json' % (self.api_base_url, quote(id))
        result = requests.get(url).json()

        if 'id' not in result:
            # assume this is a 'not found' report
            raise ObjectDoesNotExist(result['message'])

        return result

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


class ChooserViewSet(ViewSet):
    choose_view_class = ChooseView
    chosen_view_class = ChosenView

    def get_choose_view_attrs(self):
        attrs = {
            'choose_url_name': self.get_url_name('choose'),
            'chosen_url_name': self.get_url_name('chosen'),
        }

        for attr_name in (
            'icon', 'page_title', 'per_page', 'is_searchable', 'form_class', 'permission_policy', 'prefix'
        ):
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
    choose_view_class = ModelChooseView
    chosen_view_class = ModelChosenView

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


class DRFChooserViewSet(ChooserViewSet):
    choose_view_class = DRFChooseView
    chosen_view_class = DRFChosenView

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
