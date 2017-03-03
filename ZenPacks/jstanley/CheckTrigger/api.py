'''
API interfaces and default implementations.
'''
import json
import logging

from zenoss.protocols.protobufs.model_pb2 import _MODELELEMENTTYPE
from zope.interface import implements

from Products import Zuul
from Products.ZenUI3.browser.streaming import StreamingView
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IFacade


log = logging.getLogger('zen.checkTrigger.api')


class imitationDevice(object):
    def __init__(self, event):
        details = {}
        occurrence = event.get('occurrence', [False])[0]
        if occurrence:
            eventDetails = occurrence.get('details', [])
            details = { x['name']:x['value'] for x in eventDetails }
        self.ip_address = details.get('zenoss.device.ip_address', [''])[0]
        self.device_class = details.get('', [''])
        self.production_state = int(details.get('zenoss.device.production_state', [-10])[0])
        self.priority = int(details.get('zenoss.device.priority', [-10])[0])
        self.location = details.get('zenoss.device.location', [''])[0]
        self.systems = details.get('zenoss.device.systems', [''])
        self.groups = details.get('zenoss.device.groups', [''])


class imitationEvent(object):
    def __init__(self, event):
        eventDetails = {}
        occurrence = event.get('occurrence', [{}])[0]
        self.severity = int(occurrence.get('severity', -10))
        self.event_key = occurrence.get('event_key', '')
        self.event_class = occurrence.get('event_class', '')
        self.event_class_key = occurrence.get('event_class_key', '')
        self.summary = occurrence.get('summary', '')
        self.message = occurrence.get('message', '')
        self.fingerprint = occurrence.get('fingerprint', '')
        self.agent = occurrence.get('agent', '')
        self.monitor = occurrence.get('monitor', '')
        self.count = int(event.get('count', 1))
        self.status = int(event.get('status', -10))
        self.syslog_priority = int(occurrence.get('syslog_priority', -10))
        self.syslog_facility = int(occurrence.get('syslog_facility', -10))
        self.nt_event_code = int(occurrence.get('nt_event_code', -10))
        self.current_user_name = event.get('current_user_name', '')


class imitationElement(object):
    def __init__(self, event):
        actor = {}
        occurrence = event.get('occurrence', [False])[0]
        if occurrence:
            actor = occurrence.get('actor', {})
        elementType = actor.get('element_type_id', -10)
        elementLookup = _MODELELEMENTTYPE.values_by_number.get(elementType)
        self.name = actor.get('element_title', '')
        self.type = getattr(elementLookup, 'name', '')


class imitationSubElement(object):
    def __init__(self, event):
        actor = {}
        occurrence = event.get('occurrence', [False])[0]
        if occurrence:
            actor = occurrence.get('actor', {})
        elementType = actor.get('element_sub_type_id', -10)
        elementLookup = _MODELELEMENTTYPE.values_by_number.get(elementType)
        self.name = actor.get('element_sub_title', '')
        self.type = getattr(elementLookup, 'name', '')


class imitationEventDetails(object):
    def __init__(self, event):
        occurrence = event.get('occurrence', [{}])[0]
        eventDetails = occurrence.get('details', [])
        for field in eventDetails:
            setattr(self, field['name'], field['value'][0])


class ICheckTriggerFacade(IFacade):
    def checkTriggers(self, events, triggers):
        """Check if event would return true for a trigger"""


class CheckTriggerFacade(ZuulFacade):
    implements(ICheckTriggerFacade)

    def getTriggers(self):
        triggerFacade = Zuul.getFacade('triggers', self.context)
        data = triggerFacade.getTriggers()
        return data

    def getEventData(self, evids):
        zep = Zuul.getFacade('zep', self.context)
        eventFilter = zep.createEventFilter(uuid=evids)
        response = zep.getEventSummaries(0, filter=eventFilter)
        for event in response.get('events', []):
            yield event

    def buildTriggerObjects(self, event):
        dev = imitationDevice(event)
        evt = imitationEvent(event)
        elem = imitationElement(event)
        sub_elem = imitationSubElement(event)
        zp_det = imitationEventDetails(event)
        return (dev, evt, elem, sub_elem, zp_det)

    def checkTrigger(self, dev, evt, elem, sub_elem, zp_det, trigger):
        testFunction = eval('lambda dev, evt, elem, sub_elem, zp_det: ' + trigger)
        result = testFunction(dev, evt, elem, sub_elem, zp_det)
        return str(result)

    def checkTriggers(self, evids, trigger):
        if trigger == 'all':
            triggers = self.getTriggers()
        else:
            triggers = [t for t in self.getTriggers() if t['name'] == trigger]

        for event in self.getEventData(evids):
            header = "-" * 10
            dev, evt, elem, sub_elem, zp_det = self.buildTriggerObjects(event)
            yield "{} {} {}".format(header, event.get('uuid'), evt.summary)
            for trig in triggers:
                code = trig['rule']['source']
                yield "Trigger: {} for Event ({}): {} returned: {}".format(
                    trig['name'],
                    event.get('uuid'),
                    evt.summary,
                    self.checkTrigger(dev, evt, elem, sub_elem, zp_det, code),
                )


class CheckTriggerRouter(DirectRouter):
    def _getFacade(self):
        return Zuul.getFacade('checktrigger', self.context)

    def getTriggers(self):
        facade = self._getFacade()
        data = facade.getTriggers()
        return DirectResponse.succeed(data=json.dumps(data))

    def checkTriggers(self, evids, trigger=None):
        facade = self._getFacade()
        data = facade.checkTriggers(evids, trigger)
        return DirectResponse.succeed(data=data)


class checkTriggerCommandView(StreamingView):
    def stream(self):
        facade = Zuul.getFacade('checktrigger', self.context)
        data = json.loads(self.request.get('data'))
        uids = data.get('uids', {})
        evids = uids.get('evids', [])
        trigger = uids.get('trigger')
        for result in facade.checkTriggers(evids, trigger):
            self.write(result)

        self.write('Done')

