# scoreboard

A server to control a scoreboard ([Video on YouTube](https://youtu.be/3grEa7r0euY))

there is also a [scoreboard-gui](https://github.com/DresdenDukes/scoreboard-gui) for a more user friendly interface.

## hardware

- Raspberry Pi 3 Model B Plus Rev 1.3 (might switch to Pi Zero 2W later)
- 3x PCA9685
- SG90 Servo Motors
- Jumper wires ([Shop](https://www.amazon.de/dp/B01EV70C78))


## pi setup

```bash
apt install git python3-pip python3-full
python3 -m venv /opt/pythonenv
/opt/pythonenv/bin/pip install pip --upgrade
/opt/pythonenv/bin/pip install poetry
```

add `/opt/pythonenv/bin:` to PATH in /etc/profile

give pi user access to I2C (Pin3 and 5, SDA and SCL): `usermod -a -G i2c pi`

due to no real time clock we have to be able to set the time. add this line to `/etc/sudoers` to give the pi user the permission to change the time:
```
pi   ALL=(root) NOPASSWD: /usr/bin/date
```


crontab pi user:
```
@reboot cd /home/pi/scoreboard && /opt/pythonenv/bin/poetry run python scoreboard.py
@reboot sleep 40 && wget -q localhost:7000/clock -O /dev/null
```

## links

here are some helpful links which provided useful information for us:
- https://tutorials-raspberrypi.de/mehrere-servo-motoren-steuern-raspberry-pi-pca9685/
- https://tutorials-raspberrypi.de/raspberry-pi-gpios-erweitern-mittels-i2c-port-expander/
- https://youtu.be/Z7xdRMfPbP8
- https://gist.github.com/ysr23/c4a9d7185ed5c6d7ccfa31deead44070
