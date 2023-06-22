FROM ubuntu:18.04

##################################
#  Basic tools for Ubuntu image  #
##################################
RUN apt-get update && apt-get install -y curl \
    ca-certificates \ 
    software-properties-common \
    lsb-release

RUN apt-get update && apt-get install -y build-essential    
RUN apt-get update && apt-get install -y cmake
RUN apt-get update && apt-get install -y \
    sudo \
    wget \
    git \
    git-lfs \
    gnupg \
    gcc \
    g++ \
    make \
    openssh-server \
    google-mock \
    libssl1.0-dev \
    libgtest-dev \
    libssh2-1-dev

RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -
RUN apt-add-repository "deb http://apt.llvm.org/bionic/ llvm-toolchain-bionic-13 main"
RUN apt-get update && apt-get install -y clang-format-13 libclang-cpp13 libllvm13 clang-tidy-13

RUN wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | gpg --dearmor - | tee /etc/apt/trusted.gpg.d/kitware.gpg >/dev/null
RUN apt-add-repository "deb https://apt.kitware.com/ubuntu/ $(lsb_release -cs) main"
RUN apt-get update && apt-get install -y cmake

##################################
#  Python 3.7  for Ubuntu image  #
##################################
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-setuptools \
    python3-venv \
    libzmq3-dev \
    git \
    cmake \
    libzmq3-dev \
    && apt-get clean

RUN apt-get update && apt-get install -y python3.7 python3.7-dev python3-pip
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install \ 
                setuptools \
                pyinstaller \
                aiohttp \ 
                aiohttp_cors \
                pymongo \
                pandas \
                tabulate \
                schedule \
                pyyaml \
                pyftpdlib \
                websockets
                
##################################
#  Build using CMAKE  #
##################################
COPY ./ /tmp/
RUN dpkg -i ./tmp/app/third_party/tjess_python/tjess-transport_2.2.0--unstable-9-g3ae5165_amd64.deb
RUN cd ./tmp/app/third_party/tjess_python/ && python3 -m pip install .
RUN mkdir ./tmp/build && cd ./tmp/build && cmake ../ && make -j 8 && cpack

ENTRYPOINT ["/bin/bash"]