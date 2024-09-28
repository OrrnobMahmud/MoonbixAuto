FROM ubuntu:24.04

# install python, git, bash
RUN apt update && apt upgrade -y  \
    && apt install -y python3 python3-pip git bash

# break system packages
RUN mkdir -p /root/.config/pip  \
    && echo "[global]\nbreak-system-packages = true" > /root/.config/pip/pip.conf

WORKDIR /app

# clone repo
RUN git clone https://github.com/orrnobmahmud/moonbixauto.git

WORKDIR /app/moonbixauto

# install dependencies
RUN python3 -m pip install -r requirements.txt

# run
CMD ["python3", "bot.py"]
