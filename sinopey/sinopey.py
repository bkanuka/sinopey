# -*- coding: utf-8 -*-

import requests
import logging

class Thermostat(object):
    MODE_MANUAL = 2
    MODE_AUTOMATIC = 3

    def __init__(self, json, timeout=30, headers=None):
        self._headers = headers
        self.timeout = timeout
        self.json = json

        logging.debug("Initializing Thermostat with json: {}".format(json))

        # Initialize the settings.
        self._active = json['active']
        self._name = json['name']
        self._gatewayId = json['gatewayId']
        self._model = json['model']
        self._type = json['type']
        self._id = json['id']
        self._tempMax = json['tempMax']
        self._tempMin = json['tempMin']

        # Initialize the parameters.
        self._init = False
        self._alarm = None
        self._errorCode = None
        self._heatLevel = None
        self._mode = None
        self._rssi = None
        self._setpoint = None
        self._temperature = None

    @property
    def temperature(self):
        if not self._init:
            raise RuntimeError("Must run Thermostat.update() first")
        return self._temperature

    @property
    def setpoint(self):
        if not self._init:
            raise RuntimeError("Must run Thermostat.update() first")
        return self._setpoint

    @setpoint.setter
    def setpoint(self, value):
        if not self._init:
            raise RuntimeError("Must run Thermostat.update() first")
        if (value > self._tempMax) or (value < self._tempMin):
            raise ValueError('Setpoint must be between {} and {}'.format(self._tempMin, self._tempMax))

        # Set the mode to manual before setting temp
        self.mode = 2  # MODE_MANUAL

        params = {"temperature": value}
        self._set_thermostat_value("setpoint", params)

    @property
    def mode(self):
        if not self._init:
            raise RuntimeError("Must run Thermostat.update() first")
        return self._mode

    @mode.setter
    def mode(self, value):
        if not self._init:
            raise RuntimeError("Must run Thermostat.update() first")
        if value not in [2, 3]:
            raise AssertionError("Mode must be one of 2 (manual) or 3 (automatic)")
        params = {"mode": value}
        self._set_thermostat_value("mode", params)

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._id

    def load_parameters_from_json(self, json_thermostat):
        self._alarm = json_thermostat.get('alarm', self._alarm)
        self._errorCode = json_thermostat.get('errorCode', self._errorCode)
        self._heatLevel = json_thermostat.get('heatLevel', self._heatLevel)
        self._mode = json_thermostat.get('mode', self._mode)
        self._setpoint = json_thermostat.get('setpoint', self._setpoint)
        self._temperature = json_thermostat.get('temperature', self._temperature)
        if json_thermostat.get('errorCode', None):
            logging.warning("Thermostat error code: {}". format(json_thermostat['errorCode']))

    def update(self):
        r = requests.get(
            "https://neviweb.com/api/device/{}/data?force=1".format(self._id),
            headers=self._headers,
            timeout=self.timeout)
        response = r.json()
        logging.debug("Thermostat update json: {}".format(response))
        if "code" in response:
            raise requests.ConnectionError(str(response))
        if "error" in response:
            raise requests.ConnectionError(str(response))
        self.load_parameters_from_json(response)
        self._init = True

    def _set_thermostat_value(self, name, params):
        logging.debug("PUT: {}".format(params))
        r = requests.put("https://neviweb.com/api/device/{}/{}".format(self._id, name),
                         params,
                         headers=self._headers,
                         timeout=self.timeout)

        response = r.json()
        logging.debug("PUT response: {}".format(response))
        if "code" in response:
            raise requests.ConnectionError(response["code"] + ": " + response.get("message", "None"))
        if name not in response:
            raise KeyError("{} not found in PUT response. PUT unsuccessful.".format(name))
        self.load_parameters_from_json(response)


class Gateway(object):

    def __init__(self, json, timeout=30, headers=None):
        self._headers = headers
        self.timeout = timeout

        logging.debug("Initializing Gateway with json: {}".format(json))

        self._id = json['id']
        self._mac = json['macID']
        self._name = json['name']
        self._is_active = True if json['active'] else False
        self._city = json['city']
        self._postalCode = json['postalCode']

        self._thermostats = []

    def update(self):
        self._thermostats = []
        logging.info("Getting list of thermostats for gateway {}({})".format(self.name, self.id))
        r = requests.get(
            "https://neviweb.com/api/device?gatewayId={}".format(self.id),
            headers=self._headers,
            timeout=self.timeout)

        response = r.json()

        if "code" in response:
            raise requests.ConnectionError(response["code"] + ": " + response.get("message", "None"))

        for json_thermostat in response:
            therm = Thermostat(json_thermostat, timeout=self.timeout, headers=self._headers)
            try:
                therm.update()
            except requests.exceptions.Timeout:
                logging.warning("Thermostat {}({}) is unresponsive. Skipping.".format(therm.name, therm.id))
            else:
                self._thermostats.append(therm)

        if not self._thermostats:
            logging.warning("No thermostats found in gateway")

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def thermostats(self):
        return self._thermostats

    def get_thermostat(self, name):
        for thermostat in self._thermostats:
            if thermostat.name == name:
                return thermostat
        raise KeyError('Thermostat {} not found.'.format(name))


class Sinope(object):

    def __init__(self, email, password, timeout=30):
        self._email = email
        self._password = password
        self.timeout = timeout
        self._headers = {'Content-type': r'application/x-www-form-urlencoded'}
        self._session_id = None
        self._gateways = []

    def connect(self):
        logging.info("Connecting to neviweb")
        login_parameters = {'email': self._email,
                            'password': self._password,
                            'stayConnected': "0"}

        r = requests.post("https://neviweb.com/api/login",
                          data=login_parameters,
                          headers=self._headers,
                          timeout=self.timeout)

        response = r.json()
        logging.debug(response)
        if "code" in response:
            raise requests.ConnectionError(response["code"] + ": " + response.get("message", "None"))

        self._session_id = response.get('session', None)
        if self._session_id:
            self._headers['Session-Id'] = self._session_id
        else:
            raise requests.ConnectionError("Invalid response")

    def disconnect(self):
        logging.info("Disconnecting")
        requests.get("https://neviweb.com/api/logout",
                     headers=self._headers,
                     timeout=self.timeout)
        self._session_id = None
        self._headers.pop('Session-Id', None)

    def reconnect(self):
        self.disconnect()
        self.connect()

    def read_gateway(self):
        logging.info("Getting list of gateways")
        r = requests.get("https://neviweb.com/api/gateway",
                         headers=self._headers,
                         timeout=self.timeout)
        response = r.json()
        if "code" in response:
            raise requests.ConnectionError(response["code"] + ": " + response.get("message", "None"))
        assert len(response) > 0

        self._gateways = []
        for json_gateway in response:
            self._gateways.append(
                Gateway(json_gateway, timeout=self.timeout, headers=self._headers)
            )

        for gateway in self._gateways:
            gateway.update()

    @property
    def gateways(self):
        return self._gateways

    def get_gateway(self, name):
        for gateway in self._gateways:
            if gateway.name == name:
                return gateway
        raise Exception('Gateway {} not found.'.format(name))

    def get_thermostat(self, name):
        for gateway in self._gateways:
            for thermostat in gateway.thermostats:
                if thermostat.name == name:
                    return thermostat
        raise KeyError('Thermostat {} not found.'.format(name))
