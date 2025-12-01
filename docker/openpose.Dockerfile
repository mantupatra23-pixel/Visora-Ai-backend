FROM nvidia/cuda:11.7.0-cudnn8-devel-ubuntu20.04

# install deps
RUN apt-get update && apt-get install -y \
    build-essential cmake git libopencv-dev libboost-all-dev libprotobuf-dev protobuf-compiler \
    libgflags-dev libgoogle-glog-dev libhdf5-serial-dev libleveldb-dev libsnappy-dev liblmdb-dev \
    python3 python3-pip python3-dev python3-opencv python3-yaml wget unzip

WORKDIR /opt
# install caffe (light instructions — prefer using official OpenPose build scripts)
# clone openpose
RUN git clone --depth 1 https://github.com/CMU-Perceptual-Computing-Lab/openpose.git
WORKDIR /opt/openpose
# install python deps
RUN pip3 install numpy opencv-python
# build (use default build flags; may adjust CUDA arch)
RUN apt-get install -y libatlas-base-dev
RUN mkdir build && cd build && cmake .. && make -j`nproc`

ENV OPENPOSE_BIN=/opt/openpose/build/examples/openpose/openpose
ENV LD_LIBRARY_PATH=/opt/openpose/build/x64/Release/:$LD_LIBRARY_PATH
