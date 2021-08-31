from django.urls import reverse_lazy
from django.views.generic import FormView
from django.conf import settings as conf_settings

from django.http import HttpResponse, JsonResponse

from .models import Setting
from .form import ControllerForm
import requests, json


from marshmallow import Schema, fields
from marshmallow.validate import Length, Range, OneOf

class PostSettingSchema(Schema):
    bedroom_target_temperature = fields.Int(validate=Range(16, 50), required=True)
    hot_water_target_temperature = fields.Int(validate=Range(24, 90), required=True)
    bedroom_light = fields.String(validate=OneOf("on", "off"))
    bathroom_light = fields.String(validate=OneOf("on", "off"))
    
def set_setting(new_val, setting_name):
    if Setting.objects.filter(controller_name=setting_name).exists():
        t = Setting.objects.get(controller_name=setting_name)
        t.value = int(new_val)
    else:
        t = Setting(controller_name=setting_name, value=int(new_val),label=setting_name)

    t.save()

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
            schema = PostSettingSchema(strict=True)
            loaded = schema.load(request.POST)

            print(loaded)
            
            bedroom_light = loaded.data.get("bedroom_light", "off")
            bathroom_light = loaded.data.get("bathroom_light", "off")
           
            bedroom_light = True if bedroom_light == 'on' else False
            bathroom_light = True if bathroom_light == 'on' else False
            
            print("bedroom_target_temperature - " + request.POST.get("bedroom_target_temperature"))
            print("hot_water_target_temperature - " + request.POST.get("hot_water_target_temperature"))
            print("bedroom_light - " + str(bedroom_light) )
            print("bedroom_light - " + str(bathroom_light))
            
            #UnmarshalResult(data={'bedroom_light': 'on', 
            #'hot_water_target_temperature': 55, 'bedroom_target_temperature': 44}, errors={})

            set_setting(loaded.data["bedroom_target_temperature"] ,
                "bedroom_target_temperature")
            set_setting(loaded.data["hot_water_target_temperature"] ,
                "hot_water_target_temperature")

            set_setting(bedroom_light, "bedroom_light")            
            set_setting(bathroom_light, "bathroom_light")

            #item = Setting.objects.get(id=item_id)
            #review = Review(text=document['text'],
            #                grade=document['grade'],
            #                item_id=item.pk)
            #review.save()
        except Exception as exc:
            print(exc)
            return HttpResponse(str(exc),status=404)
        #except (json.JSONDecodeError, ValidationError):
        #    return HttpResponse(status=400)

        return super().post(request)