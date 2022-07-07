import json

from django.contrib.admin.utils import quote
from django.core.exceptions import ObjectDoesNotExist
from django.forms import widgets, Media
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

import requests

from wagtail import VERSION as WAGTAIL_VERSION
from wagtail.utils.widgets import WidgetWithScript

try:
    from wagtail.telepath import register
except ImportError:
    try:
        # Wagtail<3.0
        from wagtail.core.telepath import register
    except ImportError:  # do-nothing fallback for Wagtail <2.13
        def register(adapter, cls):
            pass

try:
    from wagtail.widget_adapters import WidgetAdapter
except ImportError:
    try:
        # Wagtail<3.0
        from wagtail.core.widget_adapters import WidgetAdapter
    except ImportError:  # do-nothing fallback for Wagtail <2.13
        class WidgetAdapter:
            pass

class AdminChooser(WidgetWithScript, widgets.Input):
    input_type = 'hidden'
    choose_one_text = _("Choose an item")
    choose_another_text = _("Choose another item")
    clear_choice_text = _("Clear choice")
    link_to_chosen_text = _("Edit this item")
    link_to_create_text = _("Create an item")
    show_edit_link = True
    show_create_link = True

    classname = None  # CSS class for the top-level element

    model = None

    # URL route name for creating a new item - should return the URL of the item's create view when
    # reversed with no arguments.  If no suitable URL route exists (e.g. it requires additional
    # arguments), subclasses can override get_create_item_url instead.
    create_item_url_name = None

    # URL route name for editing an existing item - should return the URL of the item's edit view
    # when reversed with the item's quoted PK as its only argument. If no suitable URL route exists
    # (e.g. it requires additional arguments), subclasses can override get_edit_item_url instead.
    edit_item_url_name = None

    # URL route name for the chooser modal view - should return the URL of the chooser view when
    # reversed with no arguments. If no suitable URL route exists, subclasses can override
    # get_choose_modal_url instead.
    # This will appear as the attribute data-choose-modal-url on the top-level element of the
    # chooser widget.
    choose_modal_url_name = None

    template = "generic_chooser/widgets/chooser.html"

    # when looping over form fields, this one should appear in visible_fields, not hidden_fields
    # despite the underlying input being type="hidden"
    is_hidden = False

    def get_instance(self, value):
        return self.model.objects.get(pk=value)

    def get_create_item_url(self):
        if self.create_item_url_name is None:
            return None
        else:
            return reverse(self.create_item_url_name)
    
    def get_edit_item_url(self, instance):
        if self.edit_item_url_name is None:
            return None
        else:
            return reverse(self.edit_item_url_name, args=(quote(instance.pk),))

    def get_choose_modal_url(self):
        if self.choose_modal_url_name is None:
            return None
        else:
            return reverse(self.choose_modal_url_name)

    def value_from_datadict(self, data, files, name):
        # treat the empty string as None
        result = super().value_from_datadict(data, files, name)
        if result == '':
            return None
        else:
            return result

    def get_title(self, instance):
        return str(instance)

    def get_value_data(self, value):
        # Given a data value (which may be None or an value such as a pk to pass to get_instance),
        # extract the necessary data for rendering the widget with that value.
        # In the case of StreamField (in Wagtail >=2.13), this data will be serialised via
        # telepath https://wagtail.github.io/telepath/ to be rendered client-side, which means it
        # cannot include model instances. Instead, we return the raw values used in rendering -
        # namely: value, title and edit_item_url
        if value is None:
            instance = None
        elif self.model and isinstance(value, self.model):
            instance = value
            value = value.pk
        else:
            try:
                instance = self.get_instance(value)
            except (ObjectDoesNotExist if self.model is None else self.model.DoesNotExist):
                instance = None

        if instance is None:
            return {
                'value': None,
                'title': '',
                'edit_item_url': None,
            }
        else:
            return {
                'value': value,
                'title': self.get_title(instance),
                'edit_item_url': self.get_edit_item_url(instance),
            }

    def render_input_html(self, name, value, attrs):
        # render the HTML for just the (hidden) input field
        return super().render_html(name, value, attrs)

    def render_html(self, name, value, attrs):
        if WAGTAIL_VERSION >= (2, 12):
            # From Wagtail 2.12, get_value_data is called as a preprocessing step in
            # WidgetWithScript before invoking render_html
            value_data = value
        else:
            value_data = self.get_value_data(value)

        original_field_html = self.render_input_html(name, value_data['value'], attrs)

        return render_to_string(self.template, {
            'widget': self,
            'original_field_html': original_field_html,
            'attrs': attrs,
            'is_empty': value_data['value'] is None,
            'title': value_data['title'],
            'edit_item_url': value_data['edit_item_url'],
            'create_item_url': self.get_create_item_url(),
            'choose_modal_url': self.get_choose_modal_url(),
        })

    def render_js_init(self, id_, name, value):
        return "new ChooserWidget({0});".format(json.dumps(id_))

    def __init__(self, **kwargs):
        # allow choose_one_text / choose_another_text to be overridden per-instance
        if 'choose_one_text' in kwargs:
            self.choose_one_text = kwargs.pop('choose_one_text')
        if 'choose_another_text' in kwargs:
            self.choose_another_text = kwargs.pop('choose_another_text')
        if 'clear_choice_text' in kwargs:
            self.clear_choice_text = kwargs.pop('clear_choice_text')
        if 'link_to_chosen_text' in kwargs:
            self.link_to_chosen_text = kwargs.pop('link_to_chosen_text')
        if 'show_edit_link' in kwargs:
            self.show_edit_link = kwargs.pop('show_edit_link')
        super().__init__(**kwargs)

    class Media:
        if WAGTAIL_VERSION >= (3, 0):
            js = [
                'generic_chooser/js/tabs.js',
                'generic_chooser/js/chooser-modal.js',
                'generic_chooser/js/chooser-widget.js',
            ]
        else:
            js = [
                'generic_chooser/js/chooser-modal.js',
                'generic_chooser/js/chooser-widget.js',
            ]


class AdminChooserAdapter(WidgetAdapter):
    js_constructor = 'wagtail_generic_chooser.widgets.Chooser'

    def js_args(self, widget):
        return [
            widget.render_html(
                "__NAME__", widget.get_value_data(None), attrs={"id": "__ID__"}
            ),
        ]

    class Media:
        js = [
            "generic_chooser/js/chooser-widget-telepath.js",
        ]


register(AdminChooserAdapter(), AdminChooser)


class DRFChooser(AdminChooser):
    """A chooser widget associated with a Django REST Framework API endpoint"""
    def get_instance(self, id):
        url = '%s%s/?format=json' % (self.api_base_url, quote(id))
        result = requests.get(url).json()

        if 'id' not in result:
            # assume this is a 'not found' report
            raise ObjectDoesNotExist(result['message'])

        return result

    def get_edit_item_url(self, instance):
        if self.edit_item_url_name is None:
            return None
        else:
            return reverse(self.edit_item_url_name, args=(instance['id'],))


class LinkedFieldMixin:
    """
    Allows a chooser widget to accept a `linked_fields` kwarg which defines a
    set of form inputs on the calling page that will have their values
    extracted and passed to the modal URL when opening the chooser URL.
    For example:
        PersonChooser(linked_fields={
            'country': '#id_country'
        })
    will retrieve the value of the form input matching the selector '#id_country'
    and pass that to the chooser modal as the URL parameter 'country'.
    """
    def __init__(self, *args, **kwargs):
        self.linked_fields = kwargs.pop('linked_fields', {})
        super().__init__(*args, **kwargs)

    def js_opts(self):
        return {'linkedFields': self.linked_fields}

    def render_js_init(self, id_, name, value):
        opts = self.js_opts()
        return "new LinkedFieldChooserWidget({0}, {1});".format(json.dumps(id_), json.dumps(opts))

    @property
    def media(self):
        if WAGTAIL_VERSION >= (3, 0):
            return super().media + Media(js=[
                'generic_chooser/js/tabs.js',
                'generic_chooser/js/chooser-widget.js',
                'generic_chooser/js/linked-field-chooser-widget.js',
            ])
        else:
            return super().media + Media(js=[
                'generic_chooser/js/chooser-widget.js',
                'generic_chooser/js/linked-field-chooser-widget.js',
            ])


class LinkedFieldChooserAdapter(WidgetAdapter):
    js_constructor = 'wagtail_generic_chooser.widgets.LinkedFieldChooser'

    def js_args(self, widget):
        return [
            widget.render_html(
                "__NAME__", widget.get_value_data(None), attrs={"id": "__ID__"}
            ),
            widget.js_opts(),
        ]

    class Media:
        js = [
            "generic_chooser/js/linked-field-chooser-widget-telepath.js",
        ]


register(LinkedFieldChooserAdapter(), LinkedFieldMixin)
