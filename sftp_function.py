from io import BytesIO
import paramiko
from google.cloud import storage, secretmanager
import base64

# connect to GCP secrets manager for log in info
project_id = 'gsk-grc'
client = secretmanager.SecretManagerServiceClient()

# fetch user name
name = f"projects/{project_id}/secrets/GSK_User/versions/latest"
response = client.access_secret_version(name=name)
my_secret_user = response.payload.data.decode("UTF-8")

# fetch pw
name = f"projects/{project_id}/secrets/GskPw/versions/latest"
response = client.access_secret_version(name=name)
my_secret_pw = response.payload.data.decode("UTF-8")

# set up secret manager here: https://codelabs.developers.google.com/codelabs/secret-manager-python#8
host = 'ftp2.inucn.com'
port = 22
username = my_secret_user
password = my_secret_pw

bucket_name = "audio_landing"
storage_client = storage.Client()
bucket = storage_client.bucket(bucket_name)


def download2(path: str):
    ssh_client = paramiko.SSHClient()
    #Google cloud doesn't handle ssh certificates, so set this to a warning to prevent stopping the process
    ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy())
    ssh_client.connect(host, port, username, password)
    sftp_client = ssh_client.open_sftp()
    #creates a buffer variable to store file in memory
    bytes_io = BytesIO()  

    print("opening file to retreive")
    try:
        sftp_client.getfo(path, bytes_io)
    except:
        print("Failed to retrieve file. Possible file does not exist. Closing client and returning.")
        sftp_client.close()
        ssh_client.close()
        return
    #this bytes object is lower level, so need to return to the begining using seek(0)
    bytes_io.seek(0)
    print("file retrieved")

    dest_blob = path.replace('/', '_')
    blob = bucket.blob(dest_blob)

    print("uploading file to blob")
    blob.upload_from_file(bytes_io)
    print("file uploaded to blob")

    ## Must ALWAYS close these clients
    sftp_client.close()
    ssh_client.close()


def hello_pubsub(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    print('pubsub message: ', pubsub_message)
    print('pubsub message type: ', type(pubsub_message))
    download2(pubsub_message)


# test_message = "/BUS4594041-DL/198253050000/198253051659.wav"
# download2(test_message)