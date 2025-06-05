class ChooserWidgetController extends window.StimulusModule.Controller {
  static values = { opts: Array };

  connect() {
    console.log("ChooserWidgetController connected", this.element.id, this.optsValue);
    new window.ChooserWidget(this.element.id, this.optsValue);
  }
}

window.wagtail.app.register("ChooserWidget", ChooserWidgetController);
