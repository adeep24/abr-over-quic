### ABR-over-QUIC

*This is still in a work in progress state and the concepts and results related to this would be shared publicly.*

This repository is used to store information repository to the project where we try to measure and analyse the effects of video streaming, 
specifically DASH (ABR) streaming over the new generation protocol - QUIC and HTTP/3.

`protocol`: This directory contain an asyncio based implementation of quic protocol using aioquic library.
Most of the code is inspired by the library itself and being directly modified from it.

`client`: This directory contain all the client implementation classes which are referenced and used at the main entry point of the code.

`adaptive`: This directory contain the adaptive bitrate algorithm implementation for the project.

`script`: This directory contain the script related to the creation of frames and segments from video file 
and further helper scripts to produce a custom manifest file.

`tests`: This directory contain the ssl keys for the protocol.

`htdocs`: This directory contain files to test and debug the protocol.


Below, you can find the necessary steps inorder to configure this project.

### Installing aioquic submodule to directly use it.

Try executing the below command inside the submodule:

```
$ pip install .
```

or, again within the submodule:

```
$ python3 setup.py install --user
```
or, do it manually if using conda environment

Httpbin
```
conda install -c dmnapolitano httpbin
```

Asgiref
```
conda install -c conda-forge asgiref
```

Starlette
```
conda install -c conda-forge starlette
```

Aiofiles
```
conda install -c anaconda aiofiles
```

Requires python 3.6+

Change different settings such as video URL and server IP address in config.py file


### Usage:

**Client**

```
python3 player.py --ca-certs tests/pycacert.pem --output-dir=. --include -v
```

**Server**

```
$ python3 server.py -c tests/ssl_cert.pem -k tests/ssl_key.pem -v
```
