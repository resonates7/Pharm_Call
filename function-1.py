from importlib.metadata import files
import pandas as pd
from google.cloud import storage
from concurrent import futures
from google.cloud import pubsub_v1
from io import BytesIO

project_id = "gsk-grc"
topic_id = "test"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)
publish_futures = []


def list_files(file, src_bucket, dest_bucket):
    """Returns a list of file paths from GSK's metadata TSV file. Then moves the metadata file to the mdata_landing
    bucket.
    
    Args:
    file: file name on source bucket
    src_bucket: source bucket name
    dest_bucket: destination bucket name
    """

    #access file in storage
    storage_client = storage.Client()
    bucket = storage_client.bucket(src_bucket)
    blob = bucket.blob(file)
    contents = blob.download_as_bytes()
    bytes_io =  BytesIO() 
    bytes_io.write(contents)
    bytes_io.seek(0)


    #create a list for pub/sub iterations

    ######## NEEDS TO BE TSV file (TAB SEPERATED)

    raw = pd.read_csv(bytes_io, sep='\t')
    file_s = list(raw['FILEPATH'])

    #move file to landing bucket
    bucket = storage_client.bucket(dest_bucket)
    blob = bucket.blob(file)
    blob.upload_from_string(contents)

    #delete source file
    bucket = storage_client.bucket(src_bucket)
    blob = bucket.blob(file)
    blob.delete()

    return file_s




def hello_gcs(event, context):
    """Background Cloud Function to be triggered by Cloud Storage.
       This generic function logs relevant data when a file is changed,
       and works for all Cloud Storage CRUD operations.
    Args:
        event (dict):  The dictionary with data specific to this type of event.
                       The `data` field contains a description of the event in
                       the Cloud Storage `object` format described here:
                       https://cloud.google.com/storage/docs/json_api/v1/objects#resource
        context (google.cloud.functions.Context): Metadata of triggering event.
    Returns:
        None; the output is written to Cloud Logging
    """

    #print('Event ID: {}'.format(context['event_id']))
    #print('Event type: {}'.format(context['event_type']))
    print('Bucket: {}'.format(event['bucket']))
    print('File: {}'.format(event['name']))
    print('Metageneration: {}'.format(event['metageneration']))
    #print('Created: {}'.format(event['timeCreated']))
    #print('Updated: {}'.format(event['updated']))
    print('end of hello gcs')

    def get_callback(
        publish_future: pubsub_v1.publisher.futures.Future, data: str):
        def callback(publish_future: pubsub_v1.publisher.futures.Future) -> None:
            print('enter callback')
        
            try:
                # Wait 60 seconds for the publish call to succeed.
                print('print publish future',publish_future.result(timeout=60))
            except futures.TimeoutError:
                print(f"Publishing {data} timed out.")

        return callback

    list_s = list_files(event['name'], event['bucket'], 'mdata_landing')

    for path in list_s:
        data = str(path)
        print('data: ', data)
        print('type data: ', type(data))
        # When you publish a message, the client returns a future.
        publish_future = publisher.publish(topic_path, data.encode("utf-8"))
        # Non-blocking. Publish failures are handled in the callback function.
        publish_future.add_done_callback(get_callback(publish_future, data))
        publish_futures.append(publish_future)