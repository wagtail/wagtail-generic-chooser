import json

from django.contrib.admin.utils import quote
from django.core.exceptions import ObjectDoesNotExist
from django.forms import widgets
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

import requests

from wagtail.utils.widgets import WidgetWithScript


class AdminChooser(WidgetWithScript, widgets.Input):
    input_type = 'hidden'
    choose_one_text = _("Choose an item")
    choose_another_text = _("Choose another item")
    clear_choice_text = _("Clear choice")
    link_to_chosen_text = _("Edit this item")
    show_edit_link = True
    classname = None  # CSS class for the top-level element

    model = None

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

    def render_html(self, name, value, attrs):
        if value is None:
            instance = None
        else:
            try:
                instance = self.get_instance(value)
            except (ObjectDoesNotExist if self.model is None else self.model.DoesNotExist):
                value = None
                instance = None

        original_field_html = super().render_html(name, value, attrs)

        if instance is None:
            edit_item_url = None
        else:
            edit_item_url = self.get_edit_item_url(instance)

        return render_to_string(self.template, {
            'widget': self,
            'original_field_html': original_field_html,
            'attrs': attrs,
            'value': value,
            'item': instance,
            'title': '' if instance is None else self.get_title(instance),
            'edit_item_url': edit_item_url,
            'choose_modal_url': self.get_choose_modal_url(),
        })

    def render_js_init(self, id_, name, value):
        return "createChooserWidget({0});".format(json.dumps(id_))

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
        js = [
            'generic_chooser/js/chooser-modal.js',
            'generic_chooser/js/chooser-widget.js',
        ]


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
