#!/bin/bash

export LIGHTSIDENTITY=him
autossh -R lights-$LIGHTSIDENTITY.serveo.net:80:localhost:3254 serveo.net &
ruby /home/pi/lights/webhook.rb &
