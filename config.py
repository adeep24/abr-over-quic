# Can provide a list of manifest to download via HTTP/3
URLS = ['https://localhost:4433/']

NUM_SERVER_PUSHED_FRAMES = 10

MANIFEST_FILE = "./htdocs/video_properties.json"
CA_CERTS = "tests/pycacert.pem"

OUT_DIR = ".cache/"

MAX_STREAM_DATA = 65556

# QOE calculations
# MPC lambda and mu for balanced
LAMBDA = 1
MU = 3000