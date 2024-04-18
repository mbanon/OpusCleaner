#No GPU support needed for now
#from nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

from ubuntu:22.04

ENV BINPATH=/opt/bin
ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C 

RUN mkdir -p /work/
RUN mkdir -p /work/venvs/
RUN mkdir -p /work/OpusCleaner/


#COPY deployment/requirements-ws.txt /work/deployment/requirements-ws.txt	
#COPY deployment/requirements-oc.txt /work/deployment/requirements-oc.txt	
#COPY pyproject.toml /work/OpusCleaner/
#COPY opuscleaner/ /work/
#COPY frontend/ /work/
#COPY utils/ /work/
COPY . /work/OpusCleaner/

RUN apt-get update
RUN apt-get install -y joe curl python3.10 python3-dev python3.10-dev  python3-pip  python3.10-venv software-properties-common git


#The webserver runs in no env (the cleaner either, for now)
RUN python3.10 -m pip install -U pip && \
	python3.10 -m pip install -U wheel  && \
	python3.10 -m pip install -U setuptools

RUN python3.10 -m pip install -r /work/OpusCleaner/deployment/requirements-ws.txt
SHELL ["/bin/bash", "--login", "-i", "-c"]
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
RUN source /root/.bashrc && nvm install 16.0.0
RUN cd /work/OpusCleaner/frontend/ && source /root/.bashrc && npm clean-install && npm run build 
    
SHELL ["/bin/bash", "--login", "-c"]

#OpusFilters et al. runs in this env. (not now)
#RUN python3.10 -m venv /work/venvs/venv-oc
#RUN . /work/venvs/venv-oc/bin/activate && \
#	python3.10 -m pip install -U pip && \
#	python3.10 -m pip install -U wheel && \
#	python3.10 -m pip install -U setuptools 
#RUN . /work/venvs/venv-oc/bin/activate && \
#	python3.10 -m pip install -r /work/deployment/requirements-oc.txt
#I don't want to install the above while testing ws

RUN python3.10 -m pip install /work/OpusCleaner/
#COPY deployment/docker-entrypoint.sh /work/deployment/docker-entrypoint.sh

EXPOSE 8000
RUN chmod +x /work/OpusCleaner/deployment/*.sh

WORKDIR /work

CMD /work/OpusCleaner/deployment/docker-entrypoint.sh
