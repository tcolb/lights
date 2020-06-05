sudo systemctl stop lights
sudo cp services/lights.service /etc/systemd/system/lights.service
sudo cp services/gh-webhook.service /etc/systemd/system/gh-webhook.service
sudo systemctl daemon-reload
sudo systemctl start lights
