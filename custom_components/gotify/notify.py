import logging
import requests
from typing import Any
import voluptuous as vol
from homeassistant.const import (
    CONF_URL,
    CONF_TOKEN,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.components.notify import (
    ATTR_TITLE_DEFAULT,
    ATTR_TITLE,
    ATTR_DATA,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({vol.Required(CONF_URL): cv.url, vol.Required(CONF_TOKEN): cv.string})
_LOGGER = logging.getLogger(__name__)

def get_service(hass, config, discovery_info=None):
    url = config.get(CONF_URL)
    token = config.get(CONF_TOKEN)

    _LOGGER.info('Service created')

    return HassAgentNotificationService(hass, url, token)


class HassAgentNotificationService(BaseNotificationService):
    def __init__(self, hass, url, token):
        self._url = url
        self._token = token
        self._hass = hass

        if not self._url.endswith('/'):
            self._url += '/'
        self._url += 'message'

    def send_request(self, url, token, data):
        return requests.post(url, headers={'X-Gotify-Key': token}, json=data, timeout=10);

    async def async_send_message(self, message: str, **kwargs: Any):
        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)
        data = kwargs.get(ATTR_DATA, None)
        if data is None:
            data = dict()

        payload = {
            'title': title,
            'message': message,
            'priority': data.get('priority', 5),
            'extras': {
                'client::display': {
                    'contentType': 'text/markdown'
                },
                'client::notification': {},
                'android::action': {}
            }
        }

        if 'content_type' in data:
            payload['extras']['client::display']['contentType'] = data.get('content_type')

        if 'image' in data:
            payload['extras']['client::notification']['bigImageUrl'] = data.get('image')
            if payload['extras']['client::display']['contentType'] == 'text/markdown':
                payload['message'] = message + ' ![](' + data.get('image') +')'

        if 'click_url' in data:
            payload['extras']['client::notification']['click'] = {
                'url': data.get('click_url')
            }

        if 'android_intentUrl' in data:
            payload['extras']['android::action']['onReceive'] = {
                'intentUrl': data.get('android_intentUrl')
            }

        if 'extras' in data:
            payload['extras'] = data.get('extras')

        _LOGGER.debug('Sending message to gotify: %s', payload)

        try:
            response = await self.hass.async_add_executor_job(self.send_request, self._url, self._token, payload)
            response.raise_for_status()
        except Exception as ex:
            _LOGGER.error('Error while sending gotify message: %s', ex)
