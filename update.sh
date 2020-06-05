sudo systemctl stop lights
sudo cp lights.service /etc/systemd/system/lights.service
sudo systemctl daemon-reload
sudo systemctl start lights
