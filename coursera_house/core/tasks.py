from __future__ import absolute_import, unicode_literals
from celery import task

from .models import Setting
from django.conf import settings as conf_settings
from django.core.mail import send_mail

import requests
import json

def return_list(f):
    def wrapper(*args, **kwargs):
        ret = f(*args, **kwargs)
        return ret if ret is not None else []
    return wrapper

def get_sensors_dict(response):
    all_states = json.loads(response.text)
    all_states['data']
    #return {item["name"]: {'value': item["value"], \
    #                'created': item['created'], 'updated': item['updated']} for item in all_states['data']}
    return {item["name"]: {'value': item["value"]} for item in all_states['data']}
    

@return_list
def handle_leak_detector(response):
    '''
    Если есть протечка воды (leak_detector=true), 
    закрыть холодную (cold_water=false) и горячую (hot_water=false) воду 
    и отослать письмо в момент обнаружения
    '''
    
    leak_detector = get_sensors_dict(response)['leak_detector']
    
    if leak_detector['value']:
        send_mail('coursera smart house message', 'Attention: leak_detector = True ',
            'from@example.com',[conf_settings.EMAIL_RECEPIENT], fail_silently=True)
        return [set_cold_water(False), set_hot_water(False), 
                    set_boiler(False), set_washing_machine(False)]
        
@return_list
def handle_cold_water_detector(response):
    '''
    Если холодная вода (cold_water) закрыта, немедленно выключить бойлер (boiler) 
    и стиральную машину (washing_machine) и 
    ни при каких условиях не включать их, пока холодная вода не будет снова открыта.
    '''
    
    detector = get_sensors_dict(response)['cold_water']
    smoke_detector = get_sensors_dict(response)['smoke_detector']

    if not detector['value']:
        return [set_boiler(False), set_washing_machine(False)]

@return_list
def handle_boiler_temperature_detector(response):
    '''
    Если горячая вода имеет температуру (boiler_temperature) меньше чем hot_water_target_temperature - 10%,
    нужно включить бойлер (boiler), и ждать пока она не достигнет температуры hot_water_target_temperature + 10%,
    после чего в целях экономии энергии бойлер нужно отключить
    '''
    
    detector = get_sensors_dict(response)['boiler_temperature']
    hot_water_target_temperature = get_hot_water_target_temperature()
    smoke_detector = get_sensors_dict(response)['smoke_detector']

    if detector['value'] < 0.9*hot_water_target_temperature and \
        get_sensors_dict(response)['cold_water']['value'] and not smoke_detector['value']:
        return [set_boiler(True)]
                    
    if detector['value'] >= 1.1*hot_water_target_temperature:
        return [set_boiler(False)]
        
@return_list
def handle_curtains_detector(response):
    '''
    Если шторы частично открыты (curtains == “slightly_open”), то они находятся на ручном управлении -
    это значит их состояние нельзя изменять автоматически ни при каких условиях.
    
    Если на улице (outdoor_light) темнее 50, открыть шторы (curtains), но только если не горит лампа
    в спальне (bedroom_light). Если на улице (outdoor_light) светлее 50, или горит свет в спальне 
    (bedroom_light), закрыть шторы. Кроме случаев когда они на ручном управлении
    '''
    
    curtains = get_sensors_dict(response)['curtains']
    outdoor_light = get_sensors_dict(response)['outdoor_light']
    bedroom_light = get_sensors_dict(response)['bedroom_light']

    if curtains['value']=='slightly_open' :
        return
                    
    if outdoor_light['value'] < 50 and not bedroom_light['value']:
        return [set_curtains('open')]

    if outdoor_light['value'] > 50 or bedroom_light['value']:
        return [set_curtains('close')]

@return_list
def handle_smoke_detector(response):
    '''
    Если обнаружен дым (smoke_detector), немедленно выключить следующие приборы 
    [air_conditioner, bedroom_light, bathroom_light, boiler, washing_machine], и
    ни при каких условиях не включать их, пока дым не исчезнет.
    '''
    smoke_detector = get_sensors_dict(response)['smoke_detector']

    if smoke_detector['value']:
        return [set_air_conditioner(False),
                set_bedroom_light(False),
                set_bathroom_light(False),
                set_boiler(False),
                set_washing_machine(False)]
       
@return_list
def handle_bedroom_temperature_detector(response):
    '''
    Если температура в спальне (bedroom_temperature) поднялась выше bedroom_target_temperature + 10% -
    включить кондиционер (air_conditioner), 
    и ждать пока температура не опустится ниже bedroom_target_temperature - 10%, 
    после чего кондиционер отключить.
    '''
    
    bedroom_target_temperature = get_bedroom_target_temperature()
    smoke_detector = get_sensors_dict(response)['smoke_detector']
    bedroom_temperature = get_sensors_dict(response)['bedroom_temperature']
    
    if bedroom_temperature['value'] > bedroom_target_temperature*1.1 and not smoke_detector['value']:
        return [set_air_conditioner(True)]

    if bedroom_temperature['value'] < bedroom_target_temperature*0.9:
        return [set_air_conditioner(False)]

@return_list
def handle_bathroom_light(response):

    setting = get_setting('bathroom_light')
    current_state = get_sensors_dict(response)['bathroom_light']['value']

    if setting is not None and not get_sensors_dict(response)['smoke_detector']['value'] and \
        setting != current_state:
        return [set_bathroom_light(bool(setting))]

@return_list
def handle_bedroom_light(response):
    setting = get_setting('bedroom_light')
    current_state = get_sensors_dict(response)['bedroom_light']['value']

    if setting is not None and not get_sensors_dict(response)['smoke_detector']['value'] and \
        setting != current_state:
        return [set_bedroom_light(bool(setting))]

###################################################
def post_sensor(name, value):
    return {'name': name, 'value': value}

def send_post(list_of_dicts):
    if list_of_dicts is None or len(list_of_dicts)==0:
        return

    headers = {'Authorization': 'Bearer {}'.format(conf_settings.SMART_HOME_ACCESS_TOKEN)}
    contrs = {"controllers": list_of_dicts}
    text = json.dumps(contrs)
    r = requests.post(conf_settings.SMART_HOME_API_URL, headers=headers, data=text)

def set_boiler(state):
    return post_sensor("boiler",state)

def set_washing_machine(state):
    return post_sensor("washing_machine",'on' if state else 'off')


def get_setting(setting_name):
    if Setting.objects.filter(controller_name=setting_name).exists():
        return int(Setting.objects.get(controller_name=setting_name).value)
    else:
        return None

def get_hot_water_target_temperature():
    return get_setting("hot_water_target_temperature")

def get_bedroom_target_temperature():
    return get_setting("bedroom_target_temperature")

def set_air_conditioner(state):
    return post_sensor("air_conditioner",state)
    
def set_bathroom_light(state):
    return post_sensor("bathroom_light",state)
    
def set_bedroom_light(state):
    return post_sensor("bedroom_light",state)
        
def set_cold_water(state):
    return post_sensor("cold_water",state)

def set_hot_water(state):
    return post_sensor("hot_water",state)

def set_curtains(state):
    return post_sensor("curtains",state)

@task()
def smart_home_manager():
    # Здесь ваш код для проверки условий

    headers = {'Authorization': 'Bearer {}'.format(conf_settings.SMART_HOME_ACCESS_TOKEN)}  
    r = requests.get(conf_settings.SMART_HOME_API_URL, headers=headers)

    send_post(handle_leak_detector(r) + handle_cold_water_detector(r) + 
                handle_boiler_temperature_detector(r) + 
                handle_curtains_detector(r) + 
                handle_smoke_detector(r) + 
                handle_bedroom_temperature_detector(r) +
                handle_bedroom_light(r) + handle_bathroom_light(r)
                )
