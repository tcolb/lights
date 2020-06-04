export LIGHTSIDENTITY=him
/home/pi/lights/venv/bin/python /home/pi/lights/Client.py $LIGHTSIDENTITY &
autossh -R lights-$LIGHTSIDENTITY.serveo.net:80:localhost:3254 serveo.net &
ruby /home/pi/lights/webhook.rb &
