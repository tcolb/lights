sudo cp lights.service /etc/systemd/system/lights.service
sudo chmod 644 /etc/systemd/system/lights.service
sudo systemctl start lights
sudo systemctl enable lights
