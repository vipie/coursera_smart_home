from django.urls import reverse_lazy
from django.views.generic import FormView
from django.conf import settings as conf_settings

from .models import Setting
from .form import ControllerForm
import requests, json


class ControllerView(FormView):
    form_class = ControllerForm
    template_name = 'core/control.html'
    success_url = reverse_lazy('form')

    def get_context_data(self, **kwargs):
        context = super(ControllerView, self).get_context_data()
        headers = {'Authorization': 'Bearer {}'.format(conf_settings.SMART_HOME_ACCESS_TOKEN)}  
        r = requests.get(conf_settings.SMART_HOME_API_URL, headers=headers)
        all_states = json.loads(r.text)
        #context['data'] = {item["name"]: {'value': item["value"],'created': item['created'], \
        #'updated': item['updated']} for item in all_states['data']}
        context['data'] = {item["name"]: item["value"] for item in all_states['data']}

        return context

    def get_initial(self):
        return {}

    def form_valid(self, form):
        return super(ControllerView, self).form_valid(form)
