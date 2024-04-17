#No GPU support needed for now
#from nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

from ubuntu:22.04

ENV BINPATH=/opt/bin
ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C 

RUN mkdir -p /work/
RUN mkdir -p /work/venvs/
RUN mkdir -p /work/opuscleaner/
RUN mkdir -p /work/frontend/
RUN mkdir -p /work/deployment/

COPY deployment/requirements-ws.txt /work/deployment/requirements-ws.txt	
COPY deployment/requirements-oc.txt /work/deployment/requirements-oc.txt	
COPY opuscleaner/ /work/opuscleaner/
COPY frontend/ /work/frontend/

RUN apt-get update
RUN apt-get install -y joe curl python3.10 python3-dev python3.10-dev  python3-pip  python3.10-venv software-properties-common


#The webserver runs in no env
RUN python3.10 -m pip install -U pip && \
	python3.10 -m pip install -U wheel  && \
	python3.10 -m pip install -U setuptools

#RUN apt-get update && apt-get install -y \
#    software-properties-common \
#    npm

RUN python3.10 -m pip install -r /work/deployment/requirements-ws.txt
SHELL ["/bin/bash", "--login", "-i", "-c"]
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
RUN source /root/.bashrc && nvm install 16.0.0
#SHELL ["/bin/bash", "--login", "-c"]


#RUN nvm install 16.0.0 
#    npm install n -g && \
#    n latest

    
RUN cd /work/frontend/ && source /root/.bashrc && npm clean-install && npm run build
    
#RUN cd /work/frontend && \
#	 npm clean-install && \
#	 npm run build


#OpusFilters et al. runs in this env. 
RUN python3.10 -m venv /work/venvs/venv-oc

RUN . /work/venvs/venv-oc/bin/activate && \
	python3.10 -m pip install -U pip && \
	python3.10 -m pip install -U wheel && \
	python3.10 -m pip install -U setuptools 
#RUN . /work/venvs/venv-oc/bin/activate && \
#	python3.10 -m pip install -r /work/deployment/requirements-oc.txt
#I don't want to install the above while testing ws


COPY deployment/docker-entrypoint.sh /work/deployment/docker-entrypoint.sh

EXPOSE 8000
RUN chmod +x /work/deployment/*.sh

WORKDIR /work

CMD /work/deployment/docker-entrypoint.sh
