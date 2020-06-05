sudo systemctl stop lights
sudo cp lights.service /etc/systemd/system/lights.service
sudo cp gh-webhook.service /etc/systemd/system/gh-webhook.service
sudo systemctl daemon-reload
sudo systemctl start lights
