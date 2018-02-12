# Sinopey

This is a Python module to control [Sinope](https://www.sinopetech.com/) thermostats.
It communicates through their web interface [Neviweb](https://neviweb.com/). All the commands
were reverse engineered from Neviweb.

## Install
`python setup.py install`

## Usage
```python
import sinopey

py_sinope = sinopey.Sinope(username, password)
py_sinope.connect()
py_sinope.read_gateway()

thermostat = py_sinope.get_thermostat("Bedroom")

print(thermostat.temperature)

thermostat.setpoint = 20
print(thermostat.setpoint)

py_sinope.disconnect()
```

## Special Thanks
Thank you to Alex Reid who first wrote a module to do this.
A lot of this is based off of his [original module](https://github.com/reid418/pysinope).