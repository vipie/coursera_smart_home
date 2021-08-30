from django.urls import reverse_lazy
from django.views.generic import FormView
from django.conf import settings as conf_settings

from django.http import HttpResponse, JsonResponse

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


    def post(self, request):

        try:
            #document = json.loads(request.body)
            #validate(document, REVIEW_SCHEMA)
            #form = ControllerForm(request.POST)
            bl = request.POST.get("bedroom_light")
            bedroom_light = bl if bl is not None else "off"
            ba_l = request.POST.get("bathroom_light")
            bathroom_light = ba_l if ba_l is not None else "off"
            
            print("bedroom_target_temperature - " + request.POST.get("bedroom_target_temperature"))
            print("hot_water_target_temperature - " + request.POST.get("hot_water_target_temperature"))
            print("bedroom_light - " + bedroom_light )
            print("bedroom_light - " + bathroom_light)

            #item = Setting.objects.get(id=item_id)
            #review = Review(text=document['text'],
            #                grade=document['grade'],
            #                item_id=item.pk)
            #review.save()
        except Exception as exc:
            print(exc)
            return HttpResponse(status=404)
        #except (json.JSONDecodeError, ValidationError):
        #    return HttpResponse(status=400)

        return super().post(request)