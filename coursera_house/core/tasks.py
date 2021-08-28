from __future__ import absolute_import, unicode_literals
from celery import task

from .models import Setting

import requests
import json



def get_sensors_dict(response):
    all_states = json.loads(response.text)
    all_states['data']
    return {item["name"]: {'value': item["value"], \
                    'created': item['created'], 'updated': item['updated']} for item in all_states['data']}
    
def handle_leak_detector(response):
    '''
    Если есть протечка воды (leak_detector=true), 
    закрыть холодную (cold_water=false) и горячую (hot_water=false) воду 
    и отослать письмо в момент обнаружения
    '''
    
    leak_detector = get_sensors_dict(response)['leak_detector']
    
    if leak_detector['value']:
        send_mail('leak_detector = True')
        set_close_water(False)
        set_hot_water(False)
        
def handle_cold_water_detector(response):
    '''
    Если холодная вода (cold_water) закрыта, немедленно выключить бойлер (boiler) 
    и стиральную машину (washing_machine) и 
    ни при каких условиях не включать их, пока холодная вода не будет снова открыта.
    '''
    
    detector = get_sensors_dict(response)['cold_water']
    smoke_detector = get_sensors_dict(response)['smoke_detector']

    
    if not detector['value']:
        set_boiler(False)
        set_washing_machine(False)
        
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
        set_boiler(True)
                    
    if detector['value'] >= 1.1*hot_water_target_temperature:
        set_boiler(False)

        
        
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
        set_curtains('open')

    if outdoor_light['value'] > 50 or bedroom_light['value']:
        set_curtains('close')
        
def handle_smoke_detector(response):
    '''
    Если обнаружен дым (smoke_detector), немедленно выключить следующие приборы 
    [air_conditioner, bedroom_light, bathroom_light, boiler, washing_machine], и
    ни при каких условиях не включать их, пока дым не исчезнет.
    '''
    smoke_detector = get_sensors_dict(response)['smoke_detector']

    if smoke_detector['value']:
        set_air_conditioner(False)
        set_bedroom_light(False)
        set_bathroom_light(False)
        set_boiler(False)
        set_washing_machine(False)
       
    
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
        set_air_conditioner(True)

    if bedroom_temperature['value'] < bedroom_target_temperature*0.9:
        set_air_conditioner(False)

###################################################
def post_sensor(name, value):
    headers = {'Authorization': 'Bearer {}'.format(SMART_HOME_ACCESS_TOKEN)}
    data = {'name': name, 'value': value}
    text = '{"controllers": ['+json.dumps(data)+']}'
    r = requests.post(SMART_HOME_API_URL, headers=headers, data=text)

def set_boiler(state):
    post_sensor("boiler",state)

def set_washing_machine(state):
    post_sensor("washing_machine",state)


def get_hot_water_target_temperature():
    #TODO get from sqlile
    return 0

def get_bedroom_target_temperature():
    #TODO get from sqlile
    return 0

def set_air_conditioner(state):
    post_sensor("air_conditioner",state)
    

@task()
def smart_home_manager():
    # Здесь ваш код для проверки условий


    headers = {'Authorization': 'Bearer {}'.format(SMART_HOME_ACCESS_TOKEN)}  
    r = requests.get(SMART_HOME_API_URL, headers=headers)

    handle_leak_detector(r)
    handle_cold_water_detector(r)
    handle_boiler_temperature_detector(r)
    handle_curtains_detector(r)
    handle_smoke_detector(r)
    handle_bedroom_temperature_detector(r)

    pass
